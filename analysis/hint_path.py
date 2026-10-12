"""The hint path: its cost from accepted candidates, the ct0 bound, and its coverage in the
archived traces (Sections VI-C, VIII-B/C/D of the manuscript; supplementary Section S-XIII).

Usage:  python3 -I hint_path.py <data> <out>

A. Stage diagnostics. In PQClean an accepted candidate does the same work as a hint-rejected one up
   to the hint-count check, and a ct0-rejected candidate stops earlier on the same path. For every
   configuration: accepted candidates' entry->hint-check time against hint-rejected candidates'
   entry->hint-check time (same runs, same build), the entry->ct0-check time of accepted candidates
   (the cost a ct0 rejection would have), and the ratios to the z- and w0-rejection costs. The
   hint-rejected times are also ranked among the accepted times of their configuration (mid-ranks,
   so that ties at the 1 us resolution count one half) and the pooled ranks are compared with a
   uniform distribution (Kolmogorov-Smirnov).
B. Envelope with the hint-path cost taken from accepted candidates: C+_stage = largest accepted
   entry->hint-check time + largest hint-rejection exit delay of the stage run of the same board and
   set; B+ from the calibration subset. Exceedances on the 26,000 original held-out calls and on the
   10,000 validation calls per configuration (RP2040), and on the 26,000 held-out ESP32 calls, whose
   stage events end at the hint-check or acceptance label (no separate exit delay).
C. Archived traces: the separated upper group U of the late band, read as the hint path: its
   increment relative to the late cluster against the hint/w0 ratio of the stage diagnostics;
   D(96) without U for traces that contain it, and D(96) with the late-cluster C+ scaled by the
   stage hint/w0 ratio of the same platform and parameter set (ESP32 run for the ESP32 trace, mean of
   the two RP2040 units otherwise), the estimate with the hint path for traces without U.
D. Per-unit hint counts in the controlled campaign and single-hint calls against expectation, over the
   full campaign and over boot blocks 0-3 (the third subset of the frozen rule); per-set hint shares
   over all boards.
"""
import sys, os, glob
import numpy as np, pandas as pd
from scipy import stats

ROOT = sys.argv[1]; OUT = sys.argv[2]
pd.set_option("display.width", 250)

# ------------------------------------------------------------------ A. stage diagnostics
rows = []; ratio_hw = {}; ranks = []
for f in sorted(glob.glob(f"{ROOT}/measurements/stages/rp2040/rp2040_*_set*_stages.csv")):
    d = pd.read_csv(f); u = int(d.board.iloc[0][-1]); st = int(d.set.iloc[0])
    acc = d[d.reason == 0]; h = d[d.reason == 4]; w = d[d.reason == 2]; z = d[d.reason == 1]
    a_h = (acc.hint_check_us - acc.entry_us) / 1000; a_c = (acc.ct0_check_us - acc.entry_us) / 1000
    h_h = (h.hint_check_us - h.entry_us) / 1000
    exit_delay = max((h.exit_us - h.hint_check_us).max() if len(h) else 0, (acc.exit_us - acc.hint_check_us).max()) / 1000
    rows.append(dict(device=f"RP2040 unit {u}", set=st, accepted=len(acc), hint_rejected=len(h),
                     acc_to_hint_med=a_h.median(), acc_to_hint_max=a_h.max(), hint_to_hint_med=h_h.median() if len(h) else np.nan,
                     hint_to_hint_max=h_h.max() if len(h) else np.nan, acc_to_ct0_med=a_c.median(), acc_to_ct0_max=a_c.max(),
                     w0_med=w.attempt_us.median() / 1000, z_med=z.attempt_us.median() / 1000, exit_delay_max_ms=exit_delay))
    ratio_hw.setdefault(st, []).append(a_h.median() / (w.attempt_us.median() / 1000))
    av = a_h.values; ranks += [((av < x).mean() + (av <= x).mean()) / 2 for x in h_h.values]
e = pd.read_csv(f"{ROOT}/measurements/stages/esp32/stage_events.csv")
p = e.pivot_table(index=["invocation", "candidate"], columns="label", values="t_us", aggfunc="first")
acc = p[p[8].notna()]; hint = p[p[7].notna()]; w0 = p[p[5].notna()]; zz = p[p[4].notna()]
a = (acc[8] - acc[0]) / 1000; hh = (hint[7] - hint[0]) / 1000
ranks += [((a.values < x).mean() + (a.values <= x).mean()) / 2 for x in hh.values]
rows.append(dict(device="ESP32", set=44, accepted=len(acc), hint_rejected=len(hint), acc_to_hint_med=a.median(), acc_to_hint_max=a.max(),
                 hint_to_hint_med=hh.median(), hint_to_hint_max=hh.max(), acc_to_ct0_med=np.nan, acc_to_ct0_max=np.nan,
                 w0_med=((w0[5] - w0[0]) / 1000).median(), z_med=((zz[4] - zz[0]) / 1000).median(), exit_delay_max_ms=0.0))
A = pd.DataFrame(rows)
A["hint_over_z"] = A.acc_to_hint_med / A.z_med; A["hint_over_w0"] = A.acc_to_hint_med / A.w0_med
A["ct0_below_hint_ms"] = A.acc_to_hint_med - A.acc_to_ct0_med
A.to_csv(OUT + "/hint_path_stages.csv", index=False)
print("A. Hint path from accepted candidates (ms):"); print(A.round(4).to_string())
print(f"   hint/z ratio {A.hint_over_z.min():.3f}-{A.hint_over_z.max():.3f}; hint/w0 {A.hint_over_w0.min():.4f}-{A.hint_over_w0.max():.4f}")
ks = stats.kstest(ranks, "uniform")
print(f"   {len(ranks)} hint-rejected candidates: largest median difference {(A.hint_to_hint_med - A.acc_to_hint_med).abs().max():.3f} ms; "
      f"maxima above the accepted maximum: {int((A.hint_to_hint_max > A.acc_to_hint_max).sum())}; "
      f"mean mid-rank percentile {np.mean(ranks):.3f}, KS D={ks.statistic:.3f}, p={ks.pvalue:.3f}")

# ------------------------------------------------------------------ B. stage-derived envelope
brows = []
for _, r in A[A.device != "ESP32"].iterrows():
    u = int(r.device[-1]); st = int(r.set)
    d = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
    cal = d[(d.key < 8) & (d.boot_block < 3)]; hold = d[~((d.key < 8) & (d.boot_block < 3))]
    Bp = cal[cal.K == 1].sign_us.max() / 1000
    Cs = r.acc_to_hint_max + r.exit_delay_max_ms
    k2 = cal[cal.K == 2]; Bm = cal[cal.K == 1].sign_us.min() / 1000; Ccal = (k2.sign_us / 1000 - Bm).max()
    def exc(df, C):
        t = df.sign_us / 1000; return int(((df.K >= 2) & (t > Bp + (df.K - 1) * C)).sum())
    vf = f"{ROOT}/measurements/signing/rp2040/validation/rp2040_{u}_set{st}_validation.csv"
    v = pd.read_csv(vf) if os.path.exists(vf) else None
    brows.append(dict(device=r.device, set=st, B_plus=Bp, C_plus_stage=Cs, C_plus_calibration=Ccal,
                      hold_exceed_stage=exc(hold, Cs), hold_exceed_calibration=exc(hold, Ccal),
                      val_exceed_stage=exc(v, Cs) if v is not None else -1, D96_stage_s=(Bp + 95 * Cs) / 1000, D96_cal_s=(Bp + 95 * Ccal) / 1000))
r = A[A.device == "ESP32"].iloc[0]
d = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
d = d.rename(columns={"elapsed_us": "sign_us", "key_id": "key", "block": "boot_block"})
cal = d[(d.key < 8) & (d.boot_block < 3)]; hold = d[~((d.key < 8) & (d.boot_block < 3))]
Bp = cal[cal.K == 1].sign_us.max() / 1000; Bm = cal[cal.K == 1].sign_us.min() / 1000
Ccal = (cal[cal.K == 2].sign_us / 1000 - Bm).max(); Cs = r.acc_to_hint_max + r.exit_delay_max_ms
ex = lambda df, C: int(((df.K >= 2) & (df.sign_us / 1000 > Bp + (df.K - 1) * C)).sum())
brows.append(dict(device="ESP32", set=44, B_plus=Bp, C_plus_stage=Cs, C_plus_calibration=Ccal, hold_exceed_stage=ex(hold, Cs),
                  hold_exceed_calibration=ex(hold, Ccal), val_exceed_stage=-1, D96_stage_s=(Bp + 95 * Cs) / 1000, D96_cal_s=(Bp + 95 * Ccal) / 1000))
Bt = pd.DataFrame(brows); Bt.to_csv(OUT + "/hint_path_envelope.csv", index=False)
print("\nB. Envelope with C+ from accepted candidates (K>=2 exceedances; val -1: not run):"); print(Bt.round(3).to_string())
Bt["C_stage_over_cal_pct"] = 100 * (Bt.C_plus_stage / Bt.C_plus_calibration - 1)
print("   C+_stage relative to C+_cal (%):", Bt.C_stage_over_cal_pct.round(2).tolist())

# ------------------------------------------------------------------ C. archived traces
sys.argv = ["x", ROOT]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "modes2.py")).read()
ns = {}
exec(src.split("\nout=[]")[0], ns)        # load(), clusters() and the trace list of modes2.py
crow = []
for name, f, lvl, bw in ns["rows"]:
    t = ns["load"](f, lvl); c = ns["clusters"](t, bw)
    Bp = c["C0"].max(); Bm = c["C0"].min(); Cl = max(c["C1"].max(), c["C2"].max()) - Bm
    Cu = (c["U"].max() - Bm) if len(c["U"]) else np.nan
    ratio = float(A[A.device == "ESP32"].hint_over_w0.iloc[0]) if name.startswith("ESP32") else np.mean(ratio_hw[lvl])   # same platform and set
    inc = ((c["U"] - c["B"]) / c["Rl"]) if len(c["U"]) else np.array([])
    crow.append(dict(trace=name, set=lvl, n_u=len(c["U"]), U_over_late=f"{inc.min():.3f}-{inc.max():.3f}" if len(inc) else "-",
                     stage_hint_over_w0=ratio, C_plus=max(Cl, Cu) if len(c["U"]) else Cl, C_late=Cl,
                     D96=(Bp + 95 * (max(Cl, Cu) if len(c["U"]) else Cl)) / 1000, D96_without_U=(Bp + 95 * Cl) / 1000 if len(c["U"]) else np.nan,
                     D96_hint_scaled=(Bp + 95 * Cl * ratio) / 1000, Cu_over_Cl=(Cu / Cl) if len(c["U"]) else np.nan,
                     D821=(Bp + 820 * (max(Cl, Cu) if len(c["U"]) else Cl)) / 1000, D821_without_U=(Bp + 820 * Cl) / 1000 if len(c["U"]) else np.nan,
                     D821_hint_scaled=(Bp + 820 * Cl * ratio) / 1000))
C = pd.DataFrame(crow); C.to_csv(OUT + "/hint_path_archived.csv", index=False)
print("\nC. Archived traces: U group as the hint path:"); print(C.round(4).to_string())
w = C[C.n_u > 0]
print(f"   D(96) without U: {100 * (w.D96_without_U / w.D96 - 1).min():.1f} to {100 * (w.D96_without_U / w.D96 - 1).max():.1f}%; "
      f"hint-scaled vs observed D(96) where U exists: {100 * (w.D96_hint_scaled / w.D96 - 1).min():+.2f} to {100 * (w.D96_hint_scaled / w.D96 - 1).max():+.2f}%")

# ------------------------------------------------------------------ D. per-unit hint counts
drow = []
for st in (44, 65, 87):
    tmp = []
    for u in (1, 2):
        d = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
        tmp.append((u, d))
    rej = sum(int((d.K - 1).sum()) for _, d in tmp); hsum = sum(int(d.n_hint.sum()) for _, d in tmp); share = hsum / rej
    for u, d in tmp:
        k2 = d[d.K == 2]; obs = int((k2.n_hint > 0).sum()); exp = len(k2) * share
        r = int((d.K - 1).sum()); h = int(d.n_hint.sum())
        drow.append(dict(unit=u, set=st, rejections=r, hint_rejections=h, hint_share_pct=100 * h / r, pooled_share_pct=100 * share,
                         hint_two_sided_p=2 * min(stats.poisson.cdf(h, r * share), stats.poisson.sf(h - 1, r * share)),
                         single_hint_calls=obs, single_hint_expected=exp, single_hint_p_low=stats.poisson.cdf(obs, exp)))
D = pd.DataFrame(drow)
# the window of the frozen rule's third subset (all keys, boot blocks 0-3) for unit 1 at ML-DSA-65
d = {(u, st): pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv") for u in (1, 2) for st in (44, 65, 87)}
win = []
for (u, st), dd in d.items():
    k2 = dd[(dd.K == 2) & (dd.boot_block < 4)]; share = float(D[D.set == st].pooled_share_pct.iloc[0]) / 100
    win.append((u, st, int((k2.n_hint > 0).sum()), len(k2) * share, stats.poisson.cdf(int((k2.n_hint > 0).sum()), len(k2) * share)))
D = D.merge(pd.DataFrame(win, columns=["unit", "set", "single_hint_blocks0_3", "expected_blocks0_3", "p_low_blocks0_3"]), on=["unit", "set"])
D.to_csv(OUT + "/hint_counts.csv", index=False)
print("\nD. Hint rejections per unit:"); print(D.round(4).to_string())
e = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
er, eh = int((e.K - 1).sum()), int(e.reject_hint.sum())
for st in (44, 65, 87):
    r = int(D[D.set == st].rejections.sum()) + (er if st == 44 else 0); h = int(D[D.set == st].hint_rejections.sum()) + (eh if st == 44 else 0)
    print(f"   ML-DSA-{st}, all boards: {h} hint rejections of {r:,} rejected candidates = {100 * h / r:.3f}%")
print(f"   all sets: {int(D.hint_rejections.sum()) + eh} of {int(D.rejections.sum()) + er:,}")
for st in (44, 65, 87):
    lam = D[D.set == st].single_hint_expected.sum() / 100000 * 1000     # expected single-hint calls per 1,000 signatures
    print(f"   ML-DSA-{st}: probability that a 1,000-signature trace contains a single-hint call = {1 - np.exp(-lam):.3f} (expected {lam:.3f})")
