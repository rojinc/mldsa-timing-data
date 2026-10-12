"""Figure: queue replay — predicted vs observed outcomes and response-time curves."""
import sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTD = sys.argv[1]; FIG = sys.argv[2]
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 7.5, "axes.labelsize": 7.5, "axes.titlesize": 8,
    "legend.fontsize": 6.8, "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "axes.linewidth": 0.6, "lines.linewidth": 1.1,
    "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK, "text.color": INK})
DBL = 7.1

l2 = pd.read_csv(OUTD + "/replay_level2a.csv"); rp = l2[l2.board != "esp32"].copy()
rp["label"] = rp.apply(lambda r: f"{'U1' if r.board=='rp2040_1' else 'U2'}-{'in' if r['mode']=='inline' else 'wk'}-{r.replicate}", axis=1)
curves = np.load(OUTD + "/response_curves.npz")

fig, axes = plt.subplots(1, 3, figsize=(DBL, 2.3), gridspec_kw=dict(width_ratios=[1.15, 1.15, 1]))
for ax, (per, key, ttl) in zip(axes[:2], [(100, "dropped", "(a) Dropped requests, RP2040, 100 ms"), (250, "late", "(b) Late reports, RP2040, 250 ms")]):
    sub = rp[rp.period_ms == per].sort_values(["board", "mode", "replicate"]).reset_index(drop=True)
    x = np.arange(len(sub))
    ax.vlines(x, sub[f"pred_{key}_lo"], sub[f"pred_{key}_hi"], color=C1, lw=2.2, alpha=0.35, label="replay, conditional 95% interval")
    ax.plot(x, sub[f"pred_{key}_med"], "_", color=C1, ms=9, mew=1.4, label="replay median")
    ax.plot(x, sub[f"obs_{key}"], "o", color=C2, ms=4, mec="white", mew=0.6, label="observed")
    ax.set_xticks(x); ax.set_xticklabels(sub.label, rotation=60, ha="right", fontsize=6)
    ax.set_title(ttl, loc="left"); ax.grid(axis="y", lw=0.3, color="0.88")
    ax.set_ylabel("count per 600 s run")
ax = axes[2]
for name, col, lab in (("rp2040_1_worker_250_1", C2, "RP2040 U1, worker, 250 ms"), ("esp32_inline_100_1", C3, "ESP32, inline, 100 ms")):
    obs = curves[name + "_obs"]; pred = curves[name + "_pred"]
    ax.step(obs, np.linspace(0, 1, len(obs)), where="post", color=col, lw=1.2, label=lab)
    ax.step(pred, np.linspace(0, 1, len(pred)), where="post", color=col, lw=1.0, ls="--")
ax.axvline(100, color=MUTED, lw=0.5, ls=":"); ax.axvline(250, color=MUTED, lw=0.5, ls=":")
ax.text(95, 1.04, "100 ms", fontsize=6, color=MUTED, ha="right"); ax.text(262, 1.04, "250 ms", fontsize=6, color=MUTED, ha="left")
ax.set_xscale("log"); ax.set_xlim(15, 1500); ax.set_ylim(0, 1.1)
ax.set_xlabel("report response, ready minus release (ms)"); ax.set_ylabel("fraction of completed reports")
ax.set_title("(c) Response time: observed (solid), replay (dashed)", loc="left", fontsize=7.2)
ax.text(300, 0.22, "RP2040 U1,\nworker, 250 ms", fontsize=6, color=C2, ha="left", va="center")
ax.text(16, 0.72, "ESP32,\ninline,\n100 ms", fontsize=6, color=C3, ha="left", va="center")
ax.grid(axis="y", lw=0.3, color="0.88")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, frameon=False, loc="lower center", ncol=3, bbox_to_anchor=(0.38, -0.08), fontsize=6.5)
fig.tight_layout(w_pad=1.2)
fig.savefig(FIG + "/fig_queue_replay.pdf")
print("ok")
