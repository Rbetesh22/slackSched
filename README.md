# SlackSched

Deadline-aware scheduling for one LLM server shared by chat (interactive) and batch (background) requests. COMS E6998 project, Ralph Betesh and Dinesh SC.

This repo runs every experiment in the midterm deck on [Vidur](https://github.com/microsoft/vidur), Microsoft's LLM-serving simulator. It models Llama-3-8B on one A100 80 GB with Vidur's copy of the vLLM (v0) scheduler.

> **Note on provenance.** This is an independent reimplementation written during an audit of the midterm results, not the original `slacksim.py` / `analyze.py` / `sweep.sh` / `plots.py`. It reproduces the deck's scorecard within a few points (see `docs/review.md`, section 3.1). The deck's original charts came from the original scripts.

## Quick start

```bash
./setup.sh                 # clones Vidur at commit abae7f6 into ./vidur and pip-installs deps
python3 slacksim.py '{"strategy": "fcfs", "qps": 2, "n": 50, "seed": 1}'   # first run trains Vidur's timing models (~20-25 min, once)

# one experiment: EDF + triage at 9 req/s, 3,000 requests
python3 slacksim.py '{"strategy": "edf_triage", "qps": 9, "n": 3000, "seed": 1}'

# everything (~900 runs, a few hours with 2 workers; resumable)
WORKERS=4 ./run_all.sh
```

`results/` already holds every run from the audit (832 runs), so `python3 analyze.py` and `python3 extra_analysis.py` rebuild all tables and plots without rerunning anything. Point `VIDUR_DIR` at an existing Vidur clone to skip the clone.

## How it works

Vidur simulates arrivals, batching, KV-cache memory and preemption step by step, using timing models trained on real A100 measurements. `slacksim.py` changes one thing: before every scheduling step it **re-sorts the waiting queue** with a strategy's key (it wraps `VLLMReplicaScheduler._get_next_batch`). Batching and memory logic are Vidur's, untouched. Requests restarted after preemption still go first, as in vLLM.

**Workload.** Request sizes are sampled from Vidur's bundled Azure 2023 LLM inference trace (conversation, `splitwise_conv.csv`), capped at 4,096 tokens. Each request is chat or batch at random (50/50 by default). Arrivals are Poisson; Vidur's generator clips gaps at 3/qps, which makes the real rate about 5% above nominal.

**Targets (SLOs).**
- Chat: time to first token ≤ max(0.5 s, 5 × no-load prefill time).
- Batch: whole request done within 120 s (configurable with `batch_ddl`).
- Also recorded: time per output token ≤ 50 ms, and TTFT under 1 / 2 / 5 / 30 s.

**Slack** = deadline − now − time still needed. For chat, time still needed is the prefill time. For batch, it's prefill + predicted answer length × 15 ms.

**Fake length predictor.** guess = true length × e^(σ·z), with z ~ N(0,1) fixed per request. Modes: `rank` (time math uses the median, 129 tokens), `point` (the guess), `upper` (guess × e^(1.28σ)), `inflateK` (guess × K, the pessimism control).

### Strategies (`strategy` key)

| Key | Deck name | Rule (lower key is served first) |
|---|---|---|
| `fcfs` | FCFS (vLLM default) | arrival time |
| `class` | Class priority | chat before batch, then arrival |
| `sjf` | Shortest-first | predicted answer length |
| `edf` | Deadline-first (EDF) | deadline |
| `edf_triage` | EDF + triage | negative slack to the back, then deadline |
| `tiers` | SlackSched (tiers) | chat by slack, then batch with < 30 s slack, then shortest batch, hopeless last |
| `llf` | SlackSched (least slack) | negative slack to the back, then least slack |
| `class_triage` | (audit baseline) | negative slack to the back, then chat first |
| `sjf_prefill` | (audit baseline) | shortest prompt first |

### Run parameters

`strategy`, `qps`, `n` (requests), `seed`, `sigma`, `mode`, `chat_frac`, `batch_ddl`, `arrivals` (`vidur_poisson` | `poisson` | `gamma_cv2`), `num_blocks` (KV-cache size; smaller forces preemption), `sched` (`vllm` | `sarathi` for chunked prefill, FCFS only).

## Experiment grids (`python3 sweep.py <grid> results/<grid>.jsonl [workers]`)

| Grid | What it tests | Runs |
|---|---|---|
| `main` | 7 strategies × loads 5–9 × 5 seeds (RQ1) | 175 |
| `sigma` | prediction noise σ 0–2 × 3 modes + shortest-first, at 7 and 9 req/s (RQ2) | 200 |
| `inflate` | perfect predictions × 1–13: is the upper-bound gain just pessimism? | 50 |
| `stress` | 80/20 chat mix, 300 s batch deadline, true Poisson, bursty arrivals, small KV cache | 180 |
| `long` | 10,000 requests per run instead of 3,000 | 30 |
| `extra` | class + triage and shortest-prompt-first baselines | 74 |
| `slo` | TTFT threshold sensitivity | 54 |
| `kv2k` | very small KV cache, real preemption | 54 |
| `sarathi` | chunked prefill, FCFS: per-token speed check | 15 |
| `sanity`, `lowload` | quick checks, loads 4 and 5.5 | – |

## Outputs

- `results/<grid>.jsonl`: one JSON line per run, with every metric (chat/batch on time, goodput, p50/p99/p99.9 TTFT, slowest batch, TPOT, steady-state windows, preemptions, makespan).
- `results/summary.md`: scorecard, load tables, noise sweep and stress tables (from `analyze.py`).
- `results/extra_summary.md`: Kendall τ of the fake predictor and measured capacity (from `extra_analysis.py`).
- `figs/`: on time vs load with 95% CIs, noise sweep, run-length check, TTFT-threshold check.
- `docs/review.md`: the full audit of the midterm deck, with every claim checked.

## Headline numbers (9 req/s, 3,000 requests, 5 seeds)

| Strategy | Chat on time | Batch on time | Goodput (req/s) |
|---|---|---|---|
| FCFS | 1% | 67% | 3.3 |
| Class priority | 66% | 20% | 4.1 |
| EDF | 50% | 20% | 3.4 |
| EDF + triage | 93% | 47% | 6.8 |
| Least slack | 81% | 43% | 6.0 |

Measured capacity is about 6.3 req/s, so 9 req/s is about 150% of capacity. Above capacity the queue never settles and the batch and tail numbers depend on run length (see `docs/review.md`).

## Known limitations

- Vidur's accuracy was validated up to about 85% of capacity; most results here are above capacity.
- The vLLM v0 scheduler runs whole prefills at once; vLLM V1 uses chunked prefill. Strategies are only hooked into the v0 scheduler so far.
- The length predictor is synthetic (noise on the true length), not a trained model.
- With the default KV cache, memory never runs out, so there's no preemption unless `num_blocks` is set.
