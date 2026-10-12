"""Path-labelled envelope from the controlled campaign (Section VIII-D of the manuscript).

B_cal+ : largest calibration signing time with K = 1.
C_cal+ : largest calibration signing time with K = 2 minus the smallest K = 1 time.
D_ctl(n) = B_cal+ + (n-1) C_cal+, tested on the 26,000 holdout calls per configuration.
Also: labelled single-rejection costs (R_z, R_late, R_hint) from calibration calls.
"""
import sys, glob
import numpy as np, pandas as pd

ROOT = sys.argv[1]; OUT = sys.argv[2]


def part(k, b):
    if k < 8 and b < 3: return "cal"
    if k >= 8 and b < 3: return "keys"
    if k < 8 and b >= 3: return "boots"
    return "both"


def load():
    cfgs = []
    esp = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
    cfgs.append(("ESP32", 44, pd.DataFrame(dict(t=esp.elapsed_us / 1000, K=esp.K, nz=esp.reject_z, nw=esp.reject_w0, nc=esp.reject_ct0, nh=esp.reject_hint,
                                             part=[part(k, b) for k, b in zip(esp.key_id, esp.block)]))))
    for st in (44, 65, 87):
        for u in (1, 2):
            d = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
            cfgs.append((f"RP2040 unit {u}", st, pd.DataFrame(dict(t=d.sign_us / 1000, K=d.K, nz=d.n_z, nw=d.n_w0, nc=d.n_ct0, nh=d.n_hint,
                                                                 part=[part(k, b) for k, b in zip(d.key, d.boot_block)]))))
    return cfgs


rows = []; byk_rows = []; cost_rows = []
for name, st, d in load():
    cal = d[d.part == "cal"]; hold = d[d.part != "cal"]
    k1 = cal[cal.K == 1].t; k2 = cal[cal.K == 2]
    Bp, Bmin = k1.max(), k1.min()
    Cp = k2.t.max() - Bmin
    gov = k2.loc[k2.t.idxmax()]
    gov_exit = "hint" if gov.nh == 1 else ("w0" if gov.nw == 1 else ("z" if gov.nz == 1 else "ct0"))
    # non-hint variant
    k2nh = k2[k2.nh == 0]; Cp_nh = k2nh.t.max() - Bmin
    D = lambda n: Bp + (n - 1) * Cp
    env = Bp + (hold.K - 1) * Cp
    exc = hold[hold.t > env]
    margin = env - hold.t
    # labelled costs from calibration single-rejection calls
    B = k1.mean()
    Rz = k2[(k2.nz == 1)].t.mean() - B; Rw = k2[(k2.nw == 1)].t.mean() - B
    Rh = k2[(k2.nh == 1)].t.mean() - B if (k2.nh == 1).any() else np.nan
    nz1, nw1, nh1 = int((k2.nz == 1).sum()), int((k2.nw == 1).sum()), int((k2.nh == 1).sum())
    rows.append(dict(config=name, set=st, n_cal=len(cal), n_hold=len(hold), B_plus_ms=Bp, B_min_ms=Bmin, C_plus_ms=Cp, governing_exit=gov_exit,
                     C_plus_nohint_ms=Cp_nh, D96_s=D(96) / 1000, D64_s=D(64) / 1000, D32_s=D(32) / 1000,
                     exceed_hold=len(exc), exceed_max_K=int(exc.K.max()) if len(exc) else 0, min_margin_ms=margin.min(), hold_maxK=int(hold.K.max()),
                     mean_B_ms=B, Rz_ms=Rz, Rlate_w0_ms=Rw, Rhint_ms=Rh, ratio_w0_z=Rw / Rz, n_z1=nz1, n_w1=nw1, n_h1=nh1,
                     hold_max_t_s=hold.t.max() / 1000, env_at_hold_maxK_s=D(hold.K.max()) / 1000))
    # margin by K on holdouts
    for k, g in hold.groupby("K"):
        e = Bp + (k - 1) * Cp
        byk_rows.append(dict(config=name, set=st, K=int(k), n=len(g), max_t_ms=g.t.max(), envelope_ms=e, min_margin_ms=e - g.t.max(),
                             exceed=int((g.t > e).sum()), mean_inc_ms=((g.t - B) / (k - 1)).mean() if k > 1 else np.nan,
                             max_inc_ms=((g.t - Bmin) / (k - 1)).max() if k > 1 else np.nan))
res = pd.DataFrame(rows); byk = pd.DataFrame(byk_rows)
res.to_csv(OUT + "/envelope_controlled.csv", index=False); byk.to_csv(OUT + "/envelope_by_K.csv", index=False)
pd.set_option("display.width", 250)
print(res.round(3).to_string())
# where is the minimum margin reached (K)?
for name, g in byk.groupby(["config", "set"]):
    gg = g.sort_values("K")
    i = gg.min_margin_ms.idxmin()
    print(name, "min margin", round(gg.loc[i, "min_margin_ms"], 3), "at K=", gg.loc[i, "K"], "| exceedances:", int(gg.exceed.sum()),
          "| max per-rejection increment vs K (K=2..6):", [round(x, 3) for x in gg[gg.K.between(2, 6)].max_inc_ms.tolist()],
          "| K>=20 max inc:", round(gg[gg.K >= 20].max_inc_ms.max(), 3) if (gg.K >= 20).any() else None)

# ---- per-exit increment distributions (calibration, K = 2) and figure
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"; INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 7.5, "axes.labelsize": 7.5, "axes.titlesize": 8, "legend.fontsize": 6.5,
    "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "axes.linewidth": 0.6, "lines.linewidth": 1.1, "pdf.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK, "text.color": INK})
dist_rows = []
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.2), gridspec_kw=dict(width_ratios=[1.3, 1]))
ax = axes[0]
styles = {("ESP32", 44): (C3, "-"), ("RP2040 unit 1", 44): (C1, "-"), ("RP2040 unit 2", 44): (C1, "--"), ("RP2040 unit 1", 65): (C2, "-"),
          ("RP2040 unit 2", 65): (C2, "--"), ("RP2040 unit 1", 87): (INK, "-"), ("RP2040 unit 2", 87): (INK, "--")}
for name, st, d in load():
    cal = d[d.part == "cal"]; hold = d[d.part != "cal"]
    k1 = cal[cal.K == 1].t; k2 = cal[cal.K == 2]; Bmin = k1.min(); B = k1.mean()
    Cp = k2.t.max() - Bmin
    for ex, mask in (("z", k2.nz == 1), ("w0", k2.nw == 1), ("hint", k2.nh == 1)):
        inc = k2[mask].t - B
        if len(inc):
            dist_rows.append(dict(config=name, set=st, exit=ex, n=len(inc), median_ms=inc.median(), p95_ms=inc.quantile(0.95), max_ms=inc.max(), min_ms=inc.min()))
    g = hold[hold.K >= 2].groupby("K").t.max()
    ratio = ((g - Bmin) / (g.index - 1)) / Cp
    col, ls = styles[(name, st)]
    ax.plot(g.index, ratio, color=col, ls=ls, lw=1.0, label=f"{name.replace('RP2040 unit ', 'RP2040 U')}, set {st}")
ax.axhline(1, color=MUTED, lw=0.6, ls=":")
ax.set_xlabel("iteration count $K$ of the held-out call"); ax.set_ylabel("largest $(T-B^{-})/(K-1)$, relative to $C^+_{\\mathrm{cal}}$")
ax.set_title("(a) Held-out per-rejection increment versus $K$", loc="left"); ax.legend(frameon=False, ncol=2, fontsize=5.8, loc="upper right")
ax.set_ylim(0.6, 1.25); ax.grid(axis="y", lw=0.3, color="0.88")
ax = axes[1]
name, st, d = load()[1]
cal = d[d.part == "cal"]; k1 = cal[cal.K == 1].t; k2 = cal[cal.K == 2]; B = k1.mean()
for ex, mask, col in (("$z$ exit", k2.nz == 1, C1), ("$w_0$ exit", k2.nw == 1, C2), ("hint exit", k2.nh == 1, C3)):
    inc = np.sort(k2[mask].t - B)
    ax.step(inc, np.linspace(0, 1, len(inc)), where="post", color=col, lw=1.1, label=f"{ex} ($n$={len(inc)})")
ax.set_xlabel("single-rejection increment $T-\\widehat B$ (ms)"); ax.set_ylabel("fraction of calibration calls")
ax.set_title("(b) RP2040 unit 1, ML-DSA-44: cost by exit", loc="left"); ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", lw=0.3, color="0.88")
fig.tight_layout(w_pad=1.5); FIG = sys.argv[3] if len(sys.argv) > 3 else OUT
fig.savefig(FIG + "/fig_envelope_controlled.pdf")
pd.DataFrame(dist_rows).to_csv(OUT + "/exit_increments.csv", index=False)
print(pd.DataFrame(dist_rows).round(3).to_string())
