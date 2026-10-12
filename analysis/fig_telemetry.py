"""Figure: telemetry outcomes per run (acquisition misses and report deadline failures), with the
fresh-input ESP32 runs beside the fixed-fixture ones when esp32_*_fresh.csv are present.

Usage:  python3 -I fig_telemetry.py <data> <fig_dir>
"""
import sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = sys.argv[1]; FIG = sys.argv[2]
D = ROOT + "/measurements/telemetry/"
C_IN, C_WK = "#eb6834", "#2a78d6"
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 7.5, "axes.labelsize": 7.5, "axes.titlesize": 8,
    "legend.fontsize": 6.8, "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "axes.linewidth": 0.6, "lines.linewidth": 1.1,
    "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK, "text.color": INK})
DBL = 7.1
PERIODS = [100, 250, 1000]; XPOS = {100: 0, 250: 1, 1000: 2}
MK = {1: "o", 2: "s", 3: "^"}

rows = []  # platform, policy, mode, period, replicate, acq_miss_pct, report_fail_pct
# ESP32, fixed fixtures
er = pd.read_csv(D + "esp32_runs.csv"); ep = pd.read_csv(D + "esp32_reports.csv")
for _, r in er[er["mode"] != "baseline"].iterrows():
    g = ep[(ep.replicate == r.replicate) & (ep["mode"] == r["mode"]) & (ep.period_ms == r.period_ms)]
    late = int((g.ready_off_us > r.period_ms * 1000).sum())
    rows.append(dict(platform="ESP32", policy="fixed", mode=r["mode"], period=int(r.period_ms), replicate=int(r.replicate),
                     acq=100 * r.acquisition_misses / r.acquisition_releases, rep=100 * (late + r.dropped + r.censored) / r.report_rows))
# ESP32, fresh inputs (optional)
have_fresh = os.path.isfile(D + "esp32_runs_fresh.csv") and os.path.isfile(D + "esp32_reports_fresh.csv")
if have_fresh:
    fr = pd.read_csv(D + "esp32_runs_fresh.csv"); fp = pd.read_csv(D + "esp32_reports_fresh.csv")
    for _, r in fr.iterrows():
        g = fp[(fp.replicate == r.replicate) & (fp["mode"] == r["mode"]) & (fp.period_ms == r.period_ms)]
        late = int((g.ready_off_us > r.period_ms * 1000).sum())
        rows.append(dict(platform="ESP32", policy="fresh", mode=r["mode"], period=int(r.period_ms), replicate=int(r.replicate),
                         acq=100 * r.acquisition_misses / r.acquisition_releases, rep=100 * (late + r.dropped + r.censored) / r.report_rows))
# RP2040 units
end = pd.read_csv(D + "rp2040_end.csv"); rr = pd.read_csv(D + "rp2040_report.csv")
for _, r in end[end["mode"] != "baseline"].iterrows():
    g = rr[(rr.board == r.board) & (rr.run == r.run)]
    exe = g[g["flags"] == 2]
    late = int(((exe.ready - exe.release) > r.period_ms * 1000).sum())
    fails = int((g["flags"] == 1).sum()) + late + int(g["flags"].isin([4, 6]).sum())
    rows.append(dict(platform="RP2040 unit 1" if r.board == "rp2040_1" else "RP2040 unit 2", policy="fresh", mode=r["mode"],
                     period=int(r.period_ms), replicate=int(r.replicate), acq=100 * (r.skipped + r.late) / r.acquisition_released, rep=100 * fails / len(g)))
T = pd.DataFrame(rows)
T.to_csv(FIG + "/telemetry_outcomes_points.csv", index=False)

fig, axes = plt.subplots(2, 3, figsize=(DBL, 3.5), sharex=True, sharey="row")
for j, plat in enumerate(["ESP32", "RP2040 unit 1", "RP2040 unit 2"]):
    sub = T[T.platform == plat]
    for i, (key, ylab) in enumerate([("acq", "Acquisition misses (%)"), ("rep", "Report failures (%)")]):
        ax = axes[i, j]
        for _, r in sub.iterrows():
            x = XPOS[r.period] + (-0.14 if r["mode"] == "inline" else 0.14) + (r.replicate - 2) * 0.045
            if plat == "ESP32":
                x += -0.07 if r.policy == "fixed" else 0.07
            col = C_IN if r["mode"] == "inline" else C_WK
            filled = (plat != "ESP32") or r.policy == "fixed"
            ax.plot(x, r[key], MK[r.replicate], ms=4.2, color=col, mfc=col if filled else "white", mew=1.0, alpha=0.95)
        ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["100", "250", "1,000"]); ax.set_ylim(-4, 104)
        ax.grid(axis="y", lw=0.3, color="0.88")
        if i == 0: ax.set_title(plat, loc="left")
        if j == 0: ax.set_ylabel(ylab)
        if i == 1: ax.set_xlabel("Report period (ms)")
        ax.axhline(0, color=MUTED, lw=0.4)
# legend
from matplotlib.lines import Line2D
h = [Line2D([], [], marker="o", color=C_IN, ls="", ms=4.2, label="Inline"),
     Line2D([], [], marker="o", color=C_WK, ls="", ms=4.2, label="Worker (second core)"),
     Line2D([], [], marker="o", color=MUTED, ls="", ms=4.2, label="Replicate 1"),
     Line2D([], [], marker="s", color=MUTED, ls="", ms=4.2, label="Replicate 2"),
     Line2D([], [], marker="^", color=MUTED, ls="", ms=4.2, label="Replicate 3")]
if have_fresh:
    h += [Line2D([], [], marker="o", color=MUTED, mfc=MUTED, ls="", ms=4.2, label="ESP32, 64 fixtures per replicate"),
          Line2D([], [], marker="o", color=MUTED, mfc="white", ls="", ms=4.2, mew=1.0, label="ESP32, fresh inputs per request")]
fig.legend(handles=h, frameon=False, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.09), fontsize=6.5, handletextpad=0.4, columnspacing=1.2)
fig.tight_layout(h_pad=1.0, w_pad=1.0)
fig.savefig(FIG + "/telemetry_results.pdf")
print("ok", len(T), "points", "(fresh runs included)" if have_fresh else "(no fresh runs)")
