"""Checks that are not in analyze.py: run-length plot, TTFT-threshold plot,
Kendall tau of the fake predictor, and measured capacity.

usage: python extra_analysis.py            (needs results/*.jsonl and the vidur trace)
"""
import json
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import kendalltau

from analyze import NAMES, COLORS, load, FIG, HERE

VIDUR_DIR = os.environ.get("VIDUR_DIR", os.path.join(HERE, "vidur"))


def runlength_plot():
    """3,000 vs 10,000 requests per run at 7 and 9 req/s (results/main + extra vs long + extra n10k)."""
    short = pd.concat([load("main"), load("extra")], ignore_index=True)
    short = short[short.get("variant", pd.Series(index=short.index, dtype=object)).isna()]
    long_ = pd.concat([load("long"), load("extra")], ignore_index=True)
    long_ = long_[long_.get("variant") == "n10k"]
    strats = ["fcfs", "class", "edf", "edf_triage", "llf", "class_triage"]
    bars = [(7, short, "#a3bfee", "7 req/s, 3k requests"), (7, long_, "#2a6fdb", "7 req/s, 10k requests"),
            (9, short, "#f2b5a5", "9 req/s, 3k requests"), (9, long_, "#e8603c", "9 req/s, 10k requests")]
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.2))
    x = np.arange(len(strats))
    for ax, met in zip(axs, ["chat_ontime", "batch_ontime"]):
        for i, (q, d, c, lab) in enumerate(bars):
            m = d[d.qps == q].groupby("strategy")[met].mean()
            ax.bar(x + (i - 1.5) * 0.2, [100 * m.get(s, np.nan) for s in strats], 0.2, color=c, label=lab)
        ax.set_xticks(x, [NAMES[s] for s in strats], rotation=15, fontsize=8)
        ax.set_title(f"{met.replace('_', ' ')}: 3,000 vs 10,000 requests per run")
        ax.set_ylabel("%"); ax.grid(axis="y", alpha=0.3)
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "rep_runlength.png"), dpi=130)


def ttft_threshold_plot():
    """At 9 req/s, share of chats under each TTFT threshold (results/slo.jsonl)."""
    d = load("slo")
    d = d[d.qps == 9]
    cols = ["chat_ontime", "chat_ttft_le1", "chat_ttft_le2", "chat_ttft_le5", "chat_ttft_le30"]
    labels = ["deck SLO\n(0.5s / 5x prefill)", "<=1 s", "<=2 s", "<=5 s", "<=30 s"]
    m = d.groupby("strategy")[cols].mean()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for s in ["fcfs", "class", "edf", "edf_triage", "llf", "class_triage"]:
        if s in m.index:
            ax.plot(range(len(cols)), 100 * m.loc[s].values, "--" if s == "class_triage" else "-",
                    marker="o", color=COLORS[s], label=NAMES[s])
    ax.set_xticks(range(len(cols)), labels)
    ax.set_ylabel("% of chats with TTFT under threshold")
    ax.set_title("9 req/s: the winner depends on where you put the TTFT threshold")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "rep_ttft_threshold.png"), dpi=130)


def kendall_tau_table(n=3000, reps=5):
    """Kendall tau between true decode length and guess = true * exp(sigma * z), on the conv trace."""
    df = pd.read_csv(os.path.join(VIDUR_DIR, "data/processed_traces/splitwise_conv.csv"))
    d = df.num_decode_tokens.values
    rows = []
    for sig in [0, 0.5, 1, 1.5, 2]:
        taus = []
        for r in range(reps):
            rng = np.random.default_rng(r)
            true = d[rng.integers(0, len(d), n)]
            guess = true * np.exp(sig * rng.standard_normal(n))
            taus.append(kendalltau(true, guess).statistic)
        rows.append(f"| {sig} | {np.mean(taus):.3f} | {np.std(taus):.3f} |")
    return ["## Kendall tau of the fake predictor (conv trace)\n", "| sigma | tau (mean) | SD |", "|---|---|---|"] + rows + [""]


def capacity():
    """Measured service rate: completed requests per second under FCFS in the heaviest overload runs."""
    d = load("main")
    d = d[(d.strategy == "fcfs") & (d.qps >= 8)]
    rate = (d.n / d.makespan).mean()
    eff = (d.eff_qps / d.qps).mean()
    return ["## Capacity\n",
            f"Service rate under overload (FCFS, 8-9 req/s): {rate:.2f} req/s.",
            f"Actual / nominal arrival rate (Vidur clips Poisson gaps at 3/qps): {eff:.3f}x in these runs "
            f"(expected value 1/(1-e^-3) = {1 / (1 - np.exp(-3)):.3f}x).", ""]


if __name__ == "__main__":
    runlength_plot()
    ttft_threshold_plot()
    out = kendall_tau_table() + capacity()
    open(os.path.join(HERE, "results", "extra_summary.md"), "w").write("\n".join(out))
    print("\n".join(out))
