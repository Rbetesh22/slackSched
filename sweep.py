"""Run grids of slacksim experiments in parallel; append JSON lines to a results file.
usage: python sweep.py <grid_name> <out.jsonl> [workers]
grids: sanity, main, sigma, stress, long, extra, inflate, slo, kv2k, lowload, sarathi
"""
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
VIDUR_DIR = os.environ.get("VIDUR_DIR", os.path.join(HERE, "vidur"))

STRATS = ["fcfs", "class", "sjf", "edf", "edf_triage", "tiers", "llf"]


def grid(name):
    G = []
    if name == "sanity":
        for s in STRATS:
            G.append(dict(strategy=s, qps=9, n=3000, seed=1))
        for q in [6.5, 7, 8, 12, 20]:
            G.append(dict(strategy="fcfs", qps=q, n=3000, seed=1))
    elif name == "main":
        for s, q, sd in itertools.product(STRATS, [5, 6, 7, 8, 9], range(1, 6)):
            G.append(dict(strategy=s, qps=q, n=3000, seed=sd))
    elif name == "sigma":
        for q, sd, sig in itertools.product([7, 9], range(1, 6), [0, 0.5, 1, 1.5, 2]):
            for m in ["rank", "point", "upper"]:
                G.append(dict(strategy="llf", qps=q, n=3000, seed=sd, sigma=sig, mode=m))
            G.append(dict(strategy="sjf", qps=q, n=3000, seed=sd, sigma=sig))
    elif name == "stress":
        base = ["fcfs", "class", "sjf", "edf", "edf_triage", "llf"]
        variants = {
            "mix80": dict(chat_frac=0.8),
            "ddl300": dict(batch_ddl=300.0),
            "truepoisson": dict(arrivals="poisson"),
            "bursty": dict(arrivals="gamma_cv2"),
            "kv8k": dict(num_blocks=8192),       # 131k tokens of KV (~16 GB) -> forces preemption
        }
        for (vn, v), s, q, sd in itertools.product(variants.items(), base, [7, 9], range(1, 4)):
            d = dict(strategy=s, qps=q, n=3000, seed=sd, variant=vn)
            d.update(v)
            G.append(d)
    elif name == "long":
        for s, q, sd in itertools.product(["fcfs", "class", "edf", "edf_triage", "llf"], [6, 7, 9], range(1, 3)):
            G.append(dict(strategy=s, qps=q, n=10000, seed=sd, variant="n10k"))
    elif name == "extra":
        for s, q, sd in itertools.product(["class_triage", "sjf_prefill"], [5, 6, 7, 8, 9], range(1, 6)):
            G.append(dict(strategy=s, qps=q, n=3000, seed=sd))
        for vn, v in {"mix80": dict(chat_frac=0.8), "kv8k": dict(num_blocks=8192), "bursty": dict(arrivals="gamma_cv2")}.items():
            for q, sd in itertools.product([7, 9], range(1, 4)):
                d = dict(strategy="class_triage", qps=q, n=3000, seed=sd, variant=vn)
                d.update(v)
                G.append(d)
        for q, sd in itertools.product([6, 7, 9], range(1, 3)):
            G.append(dict(strategy="class_triage", qps=q, n=10000, seed=sd, variant="n10k"))
    elif name == "inflate":
        # does the "upper bound" batch gain come from information or just pessimism? sigma=0, est = true*k
        for q, sd, k in itertools.product([7, 9], range(1, 6), [1, 2, 4, 8, 13]):
            G.append(dict(strategy="llf", qps=q, n=3000, seed=sd, sigma=0, mode=f"inflate{k}"))
    elif name == "slo":
        for s, q, sd in itertools.product(STRATS + ["class_triage", "sjf_prefill"], [7, 9], range(1, 4)):
            G.append(dict(strategy=s, qps=q, n=3000, seed=sd, variant="slo_metrics"))
    elif name == "kv2k":   # 2048 blocks = 32k tokens of KV: memory genuinely binds
        for s, q, sd in itertools.product(["fcfs", "class", "sjf", "edf", "edf_triage", "llf"], [5, 7, 9], range(1, 4)):
            G.append(dict(strategy=s, qps=q, n=3000, seed=sd, variant="kv2k", num_blocks=2048))
    elif name == "sarathi":  # chunked prefill (vLLM V1-like), FCFS only: the TPOT side-finding check
        for q, sd in itertools.product([5, 6, 7], range(1, 6)):
            G.append(dict(strategy="fcfs", qps=q, n=3000, seed=sd, variant="sarathi", sched="sarathi"))
    elif name == "lowload":
        for s, q, sd in itertools.product(STRATS, [4, 5.5], range(1, 6)):
            G.append(dict(strategy=s, qps=q, n=3000, seed=sd))
    return G


def work(p):
    # one fresh process per run (Vidur keeps global state; fork-pools hang)
    import subprocess
    vd = VIDUR_DIR
    try:
        out = subprocess.run([sys.executable, os.path.join(HERE, "slacksim.py"), json.dumps(p)],
                             cwd=vd, capture_output=True, text=True, timeout=1800)
        line = [l for l in out.stdout.splitlines() if l.startswith("{")][-1]
        r = json.loads(line)
    except Exception as e:
        r = dict(p, error=repr(e))
    r["key"] = json.dumps(p, sort_keys=True)
    return r


if __name__ == "__main__":
    name, out = sys.argv[1], sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    G = grid(name)
    done = set()
    if os.path.exists(out):
        for line in open(out):
            d = json.loads(line)
            if "error" not in d:
                done.add(d.get("key"))
    todo = [g for g in G if json.dumps(g, sort_keys=True) not in done]
    print(f"{name}: {len(G)} runs, {len(todo)} to do", flush=True)
    from multiprocessing.pool import ThreadPool as Pool
    with Pool(w) as pool, open(out, "a") as f:
        for i, r in enumerate(pool.imap_unordered(work, todo)):
            f.write(json.dumps(r, default=float) + "\n")
            f.flush()
            if i % 10 == 0:
                print(i, r.get("strategy"), r.get("qps"), r.get("wall"), r.get("error", ""), flush=True)
