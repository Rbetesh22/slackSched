"""
slacksim.py -- independent re-implementation of the SlackSched experiments
on top of microsoft/vidur (cloned at ./vidur by setup.sh, commit abae7f6).

Hook point: VLLMReplicaScheduler._get_next_batch. Before each call we re-sort the
waiting queue (self._request_queue) with a strategy-specific key. Batching, memory
accounting and preemption are Vidur's vLLM(v0) logic, untouched.

Workload: request sizes sampled from Vidur's bundled Azure 2023 conversation trace
(data/processed_traces/splitwise_conv.csv), clipped to 4096 total tokens exactly as
Vidur does; class chat/batch assigned i.i.d. with P(chat)=chat_frac; arrivals Poisson
(optionally Vidur-style truncated at 3/qps, or Gamma for burstiness).

Usage: run_one(dict(...)) -> dict of metrics. See sweep.py.
CLI:   python slacksim.py '{"strategy": "edf_triage", "qps": 9, "n": 3000, "seed": 1}'
"""
import math
import os
import sys
import time as _time

import numpy as np
import pandas as pd

VIDUR_DIR = os.environ.get("VIDUR_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "vidur"))
sys.path.insert(0, VIDUR_DIR)

TYPICAL_LEN = 129          # median decode length of splitwise_conv (verified)
DECODE_S_PER_TOK = 0.015   # deck's ~15 ms/token
MAX_TOKENS = 4096

_TRACE = None


def _trace():
    global _TRACE
    if _TRACE is None:
        df = pd.read_csv(os.path.join(VIDUR_DIR, "data/processed_traces/splitwise_conv.csv"))
        p = df.num_prefill_tokens.values.astype(int)
        d = df.num_decode_tokens.values.astype(int)
        tot = p + d
        diff = np.clip(tot - MAX_TOKENS, 0, None)
        p = p - np.ceil(diff * p / tot).astype(int)
        d = d - np.ceil(diff * d / tot).astype(int)
        _TRACE = (np.clip(p, 1, None), np.clip(d, 1, None))
    return _TRACE


def _build_config(num_blocks=None, out_dir="/tmp/vidur_out", sched="vllm"):
    from vidur.config import SimulationConfig
    argv = [
        "x",
        "--replica_config_device", "a100",
        "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
        "--cluster_config_num_replicas", "1",
        "--replica_scheduler_config_type", "vllm",
        "--request_generator_config_type", "synthetic",
        "--synthetic_request_generator_config_num_requests", "50",
        "--length_generator_config_type", "trace",
        "--trace_request_length_generator_config_trace_file", "./data/processed_traces/splitwise_conv.csv",
        "--interval_generator_config_type", "poisson",
        "--poisson_request_interval_generator_config_qps", "2",
        "--no-metrics_config_write_metrics",
        "--no-metrics_config_enable_chrome_trace",
        "--metrics_config_output_dir", out_dir,
        "--log_level", "warning",
    ]
    if num_blocks:
        argv += ["--vllm_scheduler_config_num_blocks", str(num_blocks)]
    if sched == "sarathi":  # chunked prefill (vLLM V1-like); strategies NOT hooked here, FCFS only
        argv[argv.index("vllm")] = "sarathi"
        argv += ["--sarathi_scheduler_config_chunk_size", "512",
                 "--sarathi_scheduler_config_batch_size_cap", "128"]
    old = sys.argv
    sys.argv = argv
    try:
        cfg = SimulationConfig.create_from_cli_args()
    finally:
        sys.argv = old
    return cfg


# ----------------------------------------------------------------------------
# strategies: key(request, now) -> sortable tuple. Lower = served first.
# Every request carries: cls ('chat'|'batch'), ddl (absolute deadline),
# prefill_s (no-load prefill time), pred (predicted decode len), est (decode len
# used for time math, depends on mode).
# Restarted (preempted) requests keep vLLM's behaviour of going first.
# ----------------------------------------------------------------------------
def _remaining(r):
    if r.cls == "chat":
        return r.prefill_s          # TTFT deadline only needs prefill
    return r.prefill_s + r.est * DECODE_S_PER_TOK


def _slack(r, now):
    return r.ddl - now - _remaining(r)


STARVE_S = 30.0  # SlackSched tiers: batch with < 30 s slack counts as "starving" (our interpretation)


def key_fn(strategy):
    if strategy == "fcfs":
        return lambda r, now: (r.arrived_at,)
    if strategy == "class":
        return lambda r, now: (r.cls != "chat", r.arrived_at)
    if strategy == "class_triage":   # extra baseline (ours): chat-first FCFS, hopeless to back
        return lambda r, now: (_slack(r, now) < 0, r.cls != "chat", r.arrived_at)
    if strategy == "sjf_prefill":    # extra baseline (ours): shortest *prompt* first (what TTFT depends on)
        return lambda r, now: (r.orig_p, r.arrived_at)
    if strategy == "sjf":
        return lambda r, now: (r.pred, r.arrived_at)
    if strategy == "edf":
        return lambda r, now: (r.ddl,)
    if strategy == "edf_triage":
        return lambda r, now: (_slack(r, now) < 0, r.ddl)
    if strategy == "llf":  # least slack, hopeless to back
        def k(r, now):
            s = _slack(r, now)
            return (s < 0, s)
        return k
    if strategy == "tiers":
        def k(r, now):
            s = _slack(r, now)
            if s < 0:
                return (3, r.ddl)
            if r.cls == "chat":
                return (0, s)
            if s < STARVE_S:
                return (1, s)
            return (2, r.pred)
        return k
    raise ValueError(strategy)


def _install_hook():
    from vidur.scheduler.replica_scheduler.vllm_replica_scheduler import VLLMReplicaScheduler
    if getattr(VLLMReplicaScheduler, "_slack_hooked", False):
        return
    orig = VLLMReplicaScheduler._get_next_batch

    def patched(self):
        kf = getattr(self, "_slack_key", None)
        if kf is not None and len(self._request_queue) > 1:
            now = self._slack_clock[0]
            self._request_queue.sort(key=lambda r: ((r.num_restarts == 0),) + kf(r, now))
        return orig(self)

    VLLMReplicaScheduler._get_next_batch = patched
    VLLMReplicaScheduler._slack_hooked = True

    # keep a clock the scheduler can read
    from vidur.events.replica_schedule_event import ReplicaScheduleEvent
    orig_h = ReplicaScheduleEvent.handle_event

    def h(self, scheduler, metrics_store):
        rs = scheduler.get_replica_scheduler(self._replica_id)
        if hasattr(rs, "_slack_clock"):
            rs._slack_clock[0] = self.time
        return orig_h(self, scheduler, metrics_store)

    ReplicaScheduleEvent.handle_event = h


def gen_workload(p, rng):
    P, D = _trace()
    n = p["n"]
    idx = rng.integers(0, len(P), n)
    qps = p["qps"]
    arr = p.get("arrivals", "vidur_poisson")
    if arr == "vidur_poisson":     # what Vidur's PoissonRequestIntervalGenerator does: clip at 3/qps
        gaps = np.minimum(rng.exponential(1 / qps, n), 3 / qps)
    elif arr == "poisson":
        gaps = rng.exponential(1 / qps, n)
    elif arr.startswith("gamma"):   # gamma_cv2 => CV=2 bursty arrivals
        cv = float(arr.split("cv")[1])
        k = 1 / cv ** 2
        gaps = rng.gamma(k, (1 / qps) / k, n)
    else:
        raise ValueError(arr)
    t = np.cumsum(gaps)
    t -= t[0]
    is_chat = rng.random(n) < p.get("chat_frac", 0.5)
    z = rng.standard_normal(n)
    return t, P[idx], D[idx], is_chat, z


def run_one(p):
    """p keys: strategy, qps, n, seed, sigma, mode(rank|point|upper), chat_frac,
    batch_ddl, arrivals, num_blocks."""
    t0 = _time.time()
    from vidur.config import SimulationConfig  # noqa
    from vidur.entities import Request, Batch
    from vidur.simulator import Simulator
    from vidur.utils.random import set_seeds
    _install_hook()

    # Vidur uses class-level id counters; reset so replica id == 0 in every run
    from vidur.entities import Replica, Cluster
    for C in (Request, Batch, Replica, Cluster):
        C._id = -1
    from vidur.entities.batch_stage import BatchStage
    BatchStage._id = -1

    seed = p.get("seed", 0)
    set_seeds(seed)
    rng = np.random.default_rng(seed)
    cfg = _build_config(p.get("num_blocks"), out_dir=p.get("out_dir", "/tmp/vidur_out"),
                        sched=p.get("sched", "vllm"))
    t, P, D, is_chat, z = gen_workload(p, rng)
    sigma = p.get("sigma", 0.0)
    mode = p.get("mode", "point")
    batch_ddl = p.get("batch_ddl", 120.0)

    holder = {}

    def init_q(self):
        pred_tp = self._scheduler._replica_schedulers[0]._replica_stage_schedulers[0]._execution_time_predictor
        cache = {}

        def prefill_s(n):
            b = (n + 15) // 16 * 16
            if b not in cache:
                rr = Request(0.0, int(b), 1)
                cache[b] = pred_tp.get_execution_time(Batch(0, [rr], [int(b)]), 0).total_time
            return cache[b]

        reqs = []
        import heapq
        from vidur.events import RequestArrivalEvent
        for i in range(len(t)):
            r = Request(float(t[i]), int(P[i]), int(D[i]))
            r.cls = "chat" if is_chat[i] else "batch"
            r.orig_p, r.orig_d = int(P[i]), int(D[i])
            r.prefill_s = prefill_s(int(P[i]))
            r.pred = D[i] * math.exp(sigma * z[i])
            if mode == "rank":
                r.est = TYPICAL_LEN
            elif mode == "point":
                r.est = r.pred
            elif mode == "upper":
                r.est = r.pred * math.exp(1.28 * sigma)
            elif mode.startswith("inflate"):   # pure pessimism control: guess x k, no extra information
                r.est = r.pred * float(mode[7:])
            if r.cls == "chat":
                r.slo = max(0.5, 5 * r.prefill_s)
                r.ddl = r.arrived_at + r.slo
            else:
                r.slo = batch_ddl
                r.ddl = r.arrived_at + batch_ddl
            reqs.append(r)
            self._add_event(RequestArrivalEvent(r.arrived_at, r))
        holder["reqs"] = reqs

    Simulator._init_event_queue = init_q
    sim = Simulator(cfg)
    rs = sim._scheduler._replica_schedulers[0]
    rs._slack_key = key_fn(p["strategy"])
    rs._slack_clock = [0.0]
    sim.run()
    reqs = holder["reqs"]
    return summarize(reqs, p, _time.time() - t0)


def summarize(reqs, p, wall):
    rows = []
    for r in reqs:
        ttft = r._prefill_completed_at - r.arrived_at
        e2e = r._completed_at - r.arrived_at
        dec = r.orig_d
        tpot = (r._completed_at - r._prefill_completed_at) / max(dec - 1, 1)
        rows.append((r.cls == "chat", ttft, e2e, tpot, r.slo, r.arrived_at, r._completed_at, r.num_restarts,
                     r.prefill_s))
    a = np.array(rows, dtype=float)
    chat = a[:, 0] == 1
    bat = ~chat
    ttft, e2e, tpot, slo, arr, done = a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5], a[:, 6]
    chat_ok = (ttft <= slo) & chat
    chat_ok_tpot = chat_ok & (tpot <= 0.050)
    bat_ok = (e2e <= slo) & bat
    span = arr.max()
    makespan = done.max()
    # steady-state window: drop first and last 20% of arrivals
    lo, hi = np.quantile(arr, [0.2, 0.8])
    mid = (arr >= lo) & (arr <= hi)
    out = dict(p)
    out.update(
        chat_ontime=chat_ok.sum() / chat.sum(),
        chat_ontime_tpot=chat_ok_tpot.sum() / chat.sum(),
        chat_tpot_ok=((tpot <= 0.05) & chat).sum() / chat.sum(),
        chat_ttft_le1=((ttft <= 1.0) & chat).sum() / chat.sum(),
        chat_ttft_le2=((ttft <= 2.0) & chat).sum() / chat.sum(),
        chat_ttft_le5=((ttft <= 5.0) & chat).sum() / chat.sum(),
        chat_ttft_le30=((ttft <= 30.0) & chat).sum() / chat.sum(),
        p999_chat_ttft=np.quantile(ttft[chat], 0.999),
        chat_short_ontime=(chat_ok & (slo <= 0.5)).sum() / (chat & (slo <= 0.5)).sum(),
        chat_long_ontime=(chat_ok & (slo > 0.5)).sum() / max((chat & (slo > 0.5)).sum(), 1),
        batch_ontime=bat_ok.sum() / bat.sum(),
        goodput_span=(chat_ok.sum() + bat_ok.sum()) / span,
        goodput_makespan=(chat_ok.sum() + bat_ok.sum()) / makespan,
        eff_qps=len(arr) / span,
        p99_chat_ttft=np.quantile(ttft[chat], 0.99),
        p50_chat_ttft=np.quantile(ttft[chat], 0.50),
        max_batch_e2e=e2e[bat].max(),
        chat_ontime_mid=(chat_ok & mid).sum() / (chat & mid).sum(),
        batch_ontime_mid=(bat_ok & mid).sum() / (bat & mid).sum(),
        chat_ontime_first1k=(chat_ok[:1000]).sum() / chat[:1000].sum(),
        chat_ontime_last1k=(chat_ok[-1000:]).sum() / chat[-1000:].sum(),
        restarts=a[:, 7].sum(),
        makespan=makespan,
        frac_chat_slo_gt_05=(slo[chat] > 0.5).mean(),
        median_prefill_s=np.median(a[:, 8]),
        wall=wall,
    )
    return out


if __name__ == "__main__":
    os.chdir(VIDUR_DIR)
    import json
    p = json.loads(sys.argv[1])
    print(json.dumps(run_one(p), default=float))
