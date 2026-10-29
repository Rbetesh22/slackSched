"""Aggregate results/*.jsonl into results/summary.md and make plots in figs/. usage: python analyze.py"""
import json
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figs")
os.makedirs(FIG, exist_ok=True)

NAMES = {"fcfs": "FCFS", "class": "Class priority", "sjf": "Shortest-first", "edf": "EDF",
         "edf_triage": "EDF + triage", "tiers": "SlackSched tiers", "llf": "Least slack",
         "class_triage": "Class + triage (ours)", "sjf_prefill": "Shortest-prompt-first (ours)"}
COLORS = {"fcfs": "#2a6fdb", "class": "#e8603c", "sjf": "#1aa37a", "edf": "#e6a100", "edf_triage": "#d6589f",
          "tiers": "#127a12", "llf": "#6b4fd8", "class_triage": "#555555", "sjf_prefill": "#999999"}


def load(name):
    p = os.path.join(R, name + ".jsonl")
    if not os.path.exists(p):
        return pd.DataFrame()
    d = pd.DataFrame([json.loads(l) for l in open(p)])
    if "error" in d:
        d = d[d["error"].isna()]
    return d


METRICS = ["chat_ontime", "batch_ontime", "goodput_span", "p99_chat_ttft", "max_batch_e2e",
           "chat_ontime_mid", "batch_ontime_mid", "chat_ontime_first1k", "chat_ontime_last1k", "chat_tpot_ok",
           "goodput_makespan", "restarts", "makespan"]


def agg(d, by):
    m = [c for c in METRICS if c in d]
    g = d.groupby(by)[m]
    mean, sd, n = g.mean(), g.std(), g.size()
    return mean, sd, n


def ci95(sd, n):
    from scipy.stats import t
    return t.ppf(0.975, np.maximum(n - 1, 1)) * sd / np.sqrt(n)


def fmt_pct(x):
    return f"{100 * x:.0f}%"


def main():
    out = []
    main = pd.concat([load("main"), load("extra")[lambda x: x.get("variant", pd.Series(dtype=object)).isna()] if len(load("extra")) else pd.DataFrame(), load("lowload")], ignore_index=True)
    if "variant" in main:
        main = main[main["variant"].isna()]
    mean, sd, n = agg(main, ["strategy", "qps"])
    ci = ci95(sd, n.values[:, None]) if len(n) else sd
    # scorecard at 9
    out.append("## Scorecard at 9 req/s (mean of seeds, +-95% CI half-width)\n")
    out.append("| Strategy | n | Chat on time | Batch on time | Goodput (req/s) | p99 chat TTFT (s) | Slowest batch (s) | Chat on time, steady-state middle 60% |")
    out.append("|---|---|---|---|---|---|---|---|")
    for s in NAMES:
        if (s, 9) not in mean.index:
            continue
        m, c = mean.loc[(s, 9)], ci.loc[(s, 9)]
        out.append(f"| {NAMES[s]} | {n.loc[(s, 9)]} | {100*m.chat_ontime:.0f} +-{100*c.chat_ontime:.0f}% | {100*m.batch_ontime:.0f} +-{100*c.batch_ontime:.0f}% | "
                   f"{m.goodput_span:.1f} +-{c.goodput_span:.1f} | {m.p99_chat_ttft:.0f} | {m.max_batch_e2e:.0f} | {100*m.chat_ontime_mid:.0f}% |")
    out.append("")
    # chat on time vs load table
    out.append("## Chat on time (TTFT SLO) vs load\n")
    loads = sorted(main.qps.unique())
    out.append("| Strategy | " + " | ".join(str(q) for q in loads) + " |")
    out.append("|---|" + "---|" * len(loads))
    for s in NAMES:
        row = []
        for q in loads:
            row.append(fmt_pct(mean.loc[(s, q)].chat_ontime) if (s, q) in mean.index else "-")
        if any(r != "-" for r in row):
            out.append(f"| {NAMES[s]} | " + " | ".join(row) + " |")
    out.append("")
    out.append("## Batch on time vs load\n")
    out.append("| Strategy | " + " | ".join(str(q) for q in loads) + " |")
    out.append("|---|" + "---|" * len(loads))
    for s in NAMES:
        row = [fmt_pct(mean.loc[(s, q)].batch_ontime) if (s, q) in mean.index else "-" for q in loads]
        if any(r != "-" for r in row):
            out.append(f"| {NAMES[s]} | " + " | ".join(row) + " |")
    out.append("")
    out.append("## Goodput (on-time requests / arrival span) vs load\n")
    out.append("| Strategy | " + " | ".join(str(q) for q in loads) + " |")
    out.append("|---|" + "---|" * len(loads))
    for s in NAMES:
        row = [f"{mean.loc[(s, q)].goodput_span:.2f}" if (s, q) in mean.index else "-" for q in loads]
        if any(r != "-" for r in row):
            out.append(f"| {NAMES[s]} | " + " | ".join(row) + " |")
    out.append("")
    # FCFS drift: first vs last 1000 requests
    out.append("## Non-stationarity check (FCFS & EDF+triage): chat on time in first 1000 vs last 1000 requests\n")
    out.append("| Strategy | load | first 1k | middle 60% | last 1k | makespan (s) |")
    out.append("|---|---|---|---|---|---|")
    for s in ["fcfs", "edf", "edf_triage", "llf"]:
        for q in loads:
            if (s, q) in mean.index:
                m = mean.loc[(s, q)]
                out.append(f"| {NAMES[s]} | {q} | {fmt_pct(m.chat_ontime_first1k)} | {fmt_pct(m.chat_ontime_mid)} | {fmt_pct(m.chat_ontime_last1k)} | {m.makespan:.0f} |")
    out.append("")

    # plot chat/batch on time vs load
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    for s in ["fcfs", "class", "sjf", "edf", "edf_triage", "tiers", "llf", "class_triage"]:
        qs = [q for q in loads if (s, q) in mean.index]
        if not qs:
            continue
        for ax, met in zip(axs, ["chat_ontime", "batch_ontime"]):
            y = np.array([mean.loc[(s, q)][met] for q in qs]) * 100
            e = np.array([ci.loc[(s, q)][met] for q in qs]) * 100
            ls = "--" if s == "class_triage" else "-"
            ax.plot(qs, y, ls, marker="o", ms=3, color=COLORS[s], label=NAMES[s], lw=1.6)
            ax.fill_between(qs, y - e, y + e, color=COLORS[s], alpha=0.12, lw=0)
    axs[0].set_title("Replication: chat meeting TTFT SLO (Vidur, 5 seeds, 95% CI)")
    axs[1].set_title("Replication: batch finishing within 120 s")
    for ax in axs:
        ax.set_xlabel("offered load (req/s)")
        ax.set_ylabel("% on time")
        ax.set_ylim(-2, 102)
        ax.grid(alpha=0.3)
        ax.axvline(6.4, color="k", lw=0.6, ls=":")
    axs[0].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "rep_ontime_vs_load.png"), dpi=130)

    # sigma
    sig = load("sigma")
    if len(sig):
        sig["mode"] = sig["mode"].fillna("point"); sig["sigma"] = sig["sigma"].astype(float); sig["qps"] = sig["qps"].astype(int)
        sm = sig.groupby(["strategy", "mode", "qps", "sigma"])[["chat_ontime", "batch_ontime", "max_batch_e2e"]].agg(["mean", "std", "count"])
        out.append("## Prediction-noise sweep (least slack; shortest-first), mean over seeds\n")
        out.append("| load | strategy/mode | metric | s=0 | 0.5 | 1 | 1.5 | 2 |")
        out.append("|---|---|---|---|---|---|---|---|")
        for q in [7, 9]:
            for (s, mo) in [("llf", "rank"), ("llf", "point"), ("llf", "upper"), ("sjf", "point")]:
                for met in ["chat_ontime", "batch_ontime", "max_batch_e2e"]:
                    vals = []
                    for sg in [0.0, 0.5, 1.0, 1.5, 2.0]:
                        try:
                            mu = sm.loc[(s, mo, q, sg)][(met, "mean")]
                            sdv = sm.loc[(s, mo, q, sg)][(met, "std")]
                            vals.append(f"{mu:.0f}s" if met == "max_batch_e2e" else f"{100*mu:.0f}+-{100*sdv:.0f}")
                        except KeyError:
                            vals.append("-")
                    out.append(f"| {q} | {s}/{mo} | {met} | " + " | ".join(vals) + " |")
        out.append("")
        fig, axs = plt.subplots(1, 3, figsize=(15, 4))
        for ax, (q, met) in zip(axs, [(9, "chat_ontime"), (9, "batch_ontime"), (7, "batch_ontime")]):
            for (s, mo), c in [(("llf", "rank"), "#2a6fdb"), (("llf", "point"), "#e8603c"), (("llf", "upper"), "#1aa37a"), (("sjf", "point"), "#e6a100")]:
                xs, ys, es = [], [], []
                for sg in [0.0, 0.5, 1.0, 1.5, 2.0]:
                    if (s, mo, q, sg) in sm.index:
                        r = sm.loc[(s, mo, q, sg)]
                        xs.append(sg); ys.append(100 * r[(met, "mean")]); es.append(100 * r[(met, "std")])
                xs, ys, es = map(np.array, (xs, ys, es))
                lab = "Shortest-first" if s == "sjf" else f"Least slack, {mo}"
                ax.errorbar(xs, ys, yerr=es, marker="o", ms=3, capsize=3, color=c, label=lab)
            ax.set_title(f"{met.replace('_', ' ')} at {q} req/s (error bars = 1 SD over 5 seeds)", fontsize=9)
            ax.set_xlabel("noise sigma"); ax.set_ylabel("%"); ax.grid(alpha=0.3)
        axs[0].legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "rep_sigma.png"), dpi=130)

    # stress
    st = pd.concat([load("stress"), load("extra"), load("long")], ignore_index=True)
    if len(st) and "variant" in st:
        st = st[st["variant"].notna()]
        sm = st.groupby(["variant", "strategy", "qps"])[["chat_ontime", "batch_ontime", "goodput_span", "p99_chat_ttft", "max_batch_e2e", "restarts", "chat_ontime_mid"]].mean()
        cnt = st.groupby(["variant", "strategy", "qps"]).size()
        out.append("## Stress variants (mean over seeds)\n")
        out.append("| variant | load | strategy | n | chat on time | batch on time | goodput | p99 chat TTFT (s) | slowest batch (s) | preemption restarts |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for idx, r in sm.iterrows():
            v, s, q = idx
            out.append(f"| {v} | {q} | {NAMES.get(s, s)} | {cnt.loc[idx]} | {fmt_pct(r.chat_ontime)} | {fmt_pct(r.batch_ontime)} | {r.goodput_span:.2f} | {r.p99_chat_ttft:.0f} | {r.max_batch_e2e:.0f} | {r.restarts:.0f} |")
        out.append("")
    open(os.path.join(R, "summary.md"), "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
