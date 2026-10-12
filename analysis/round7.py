"""Round-7 analyses (Sections IV-B, VIII-E and IX-D of the manuscript).

A. Instrumentation overhead from the paired pilots: counting mode minus plain mode on the same
   inputs (RP2040: 1,100 pairs per board and set; ESP32: 1,000 pairs), with t intervals.
B. Simple prediction baselines for the queue outcomes, using the same other-replicate pools as
   the level-2 replay: a mean-capacity baseline for drops (window / mean cycle) and a
   share-above-period baseline for late reports.
C. Held-out exceedance of the path-labelled envelope at attainable iteration-tail targets:
   n_eps from the calibration mean, D_ctl(n_eps) from the calibration maxima, exceedances
   counted on the 26,000 held-out calls per configuration and split by cause.
D. The ct0 bound tau * 2^(d-1) against gamma2 for the three parameter sets.
"""
import sys, os, glob, json
import numpy as np, pandas as pd
from scipy import stats

ROOT = sys.argv[1]; OUT = sys.argv[2]
sys.argv = ["x", ROOT, OUT]
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "queue_replay.py")).read().split("if __name__")[0])

# ---------------------------------------------------------------- A. overhead
def ols(y, X):
    """Least squares with 95% t intervals; returns (coef, lo, hi) including the intercept first."""
    X = np.column_stack([np.ones(len(y)), X]); b = np.linalg.lstsq(X, y, rcond=None)[0]
    r = y - X @ b; n, p = X.shape; s2 = (r @ r) / (n - p); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X))); t = stats.t.ppf(0.975, n - p)
    return b, b - t * se, b + t * se

def overhead_row(board, st, plain, counts, K, rej):
    """Paired difference counts - plain: mean with t interval; its regression on the number of rejections,
    Delta = a + b (K - 1), so that a is the shift at K = 1 and b the shift per additional candidate; and its
    regression on the exit counts z, w0, hint (per rejected candidate of each exit)."""
    diff = (counts - plain).astype(float); n = len(diff); se = diff.std(ddof=1) / np.sqrt(n); t = stats.t.ppf(0.975, n - 1)
    # regress on the number of rejections K-1, so that the intercept is the shift of a first-candidate call (K=1)
    b, lo, hi = ols(diff, K.astype(float) - 1); b2, lo2, hi2 = ols(diff, rej.astype(float))
    return dict(board=board, set=st, pairs=n, mean_plain_us=plain.mean(), mean_diff_us=diff.mean(), ci_lo_us=diff.mean() - t * se, ci_hi_us=diff.mean() + t * se,
                median_diff_us=np.median(diff), sd_diff_us=diff.std(ddof=1), rel_pct=100 * diff.mean() / plain.mean(),
                shift_K1_us=b[0], shift_K1_lo=lo[0], shift_K1_hi=hi[0], slope_us_per_candidate=b[1], slope_lo=lo[1], slope_hi=hi[1],
                z_us=b2[1], z_lo=lo2[1], z_hi=hi2[1], w0_us=b2[2], w0_lo=lo2[2], w0_hi=hi2[2], hint_us=b2[3], hint_lo=lo2[3], hint_hi=hi2[3], pairs_with_hint=int((rej[:, 2] > 0).sum()),
                diff_K1_us=diff[K == 1].mean(), diff_K2_us=diff[K == 2].mean(), diff_Kge5_us=diff[K >= 5].mean(), n_Kge5=int((K >= 5).sum()), max_K=int(K.max()))

rows = []
for u in (1, 2):
    for st in (44, 65, 87):
        d = pd.DataFrame([json.loads(l) for l in open(f"{ROOT}/measurements/pilots/rp2040/rp2040_{u}_set{st}.jsonl")])
        p = d[d.phase == "pilot"]; pl = p[p["mode"] == 0].set_index("index"); co = p[p["mode"] == 1].set_index("index").loc[pl.index]
        rej = np.vstack(co.reject.values)[:, [0, 1, 3]]          # z, w0, hint (ct0 never occurs)
        rows.append(overhead_row(f"rp2040_{u}", st, pl.sign_us.values.astype(float), co.sign_us.values.astype(float), co.K.values, rej))
pl = pd.read_csv(f"{ROOT}/measurements/pilots/esp32/plain.csv"); co = pd.read_csv(f"{ROOT}/measurements/pilots/esp32/counts.csv")
m = pl.merge(co, on=["block", "key_id", "message_id", "rand_index"], suffixes=("_p", "_c"))
rows.append(overhead_row("esp32", 44, m.elapsed_us_p.values.astype(float), m.elapsed_us_c.values.astype(float), m.K_c.values, m[["reject_z_c", "reject_w0_c", "reject_hint_c"]].values))
OV = pd.DataFrame(rows)
env = pd.read_csv(OUT + "/envelope_controlled.csv") if os.path.exists(OUT + "/envelope_controlled.csv") else None
if env is not None:
    key = {"rp2040_1": "RP2040 unit 1", "rp2040_2": "RP2040 unit 2", "esp32": "ESP32"}
    rz = {(r.config, int(r.set)): r.Rz_ms for _, r in env.iterrows()}
    OV["Rz_ms"] = [rz[(key[b], int(st))] for b, st in zip(OV.board, OV.set)]
    OV["slope_rel_Rz_pct"] = 100 * OV.slope_us_per_candidate / 1000 / OV.Rz_ms
OV.to_csv(OUT + "/overhead.csv", index=False)
pd.set_option("display.width", 260); print("A. counting-mode overhead (us): mean difference, and its dependence on K and on the exits"); print(OV.round(2).to_string())

# ---------------------------------------------------------------- B. baselines
runs = rp_runs() + esp_runs(); pool = pools(runs)
l2 = pd.read_csv(OUT + "/replay_level2a.csv")
brows = []
for r in runs:
    if r["period_ms"] == 1000:
        continue
    P = r["period_ms"] * 1000; n = r["n"]
    others = np.vstack([v for k, v in pool.items() if k[0] == r["board"] and k[1] == r["mode"] and k[2] != r["replicate"]])
    cycle = others.sum(axis=1).mean(); svc = others[:, 0]
    served = int(WINDOW // cycle)                      # mean-capacity baseline: requests the server can finish in the window
    base_drop = max(0, n - served)
    base_late = n * float((svc > P).mean())            # share-above-period baseline
    m = l2[(l2.board == r["board"]) & (l2["mode"] == r["mode"]) & (l2.period_ms == r["period_ms"]) & (l2.replicate == r["replicate"])].iloc[0]
    brows.append(dict(board=r["board"], mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"], n=n, pool_mean_cycle_ms=cycle / 1000,
                      obs_dropped=r["obs"]["dropped"], base_dropped=base_drop, replay_dropped=m.pred_dropped_med,
                      obs_late=r["obs"]["late"], base_late=base_late, replay_late=m.pred_late_med))
B = pd.DataFrame(brows)
for k in ("dropped", "late"):
    B[f"base_{k}_err_pct"] = 100 * (B[f"obs_{k}"] - B[f"base_{k}"]) / B[f"obs_{k}"].replace(0, np.nan)
    B[f"replay_{k}_err_pct"] = 100 * (B[f"obs_{k}"] - B[f"replay_{k}"]) / B[f"obs_{k}"].replace(0, np.nan)
B.to_csv(OUT + "/baselines.csv", index=False)
print("\nB. baselines (error = observed - prediction, relative to observed):")
print(B[["board", "mode", "period_ms", "replicate", "obs_dropped", "base_dropped", "replay_dropped", "base_dropped_err_pct", "replay_dropped_err_pct",
         "obs_late", "base_late", "replay_late", "base_late_err_pct", "replay_late_err_pct"]].round(1).to_string())
for (b, per), g in B.groupby([B.board.str.startswith("rp2040"), "period_ms"]):
    k = "dropped" if (b and per == 100) else "late"
    print(f"  {'RP2040' if b else 'ESP32'} {per} ms {k}: baseline error {g[f'base_{k}_err_pct'].min():.1f} to {g[f'base_{k}_err_pct'].max():.1f}% | replay error {g[f'replay_{k}_err_pct'].min():.1f} to {g[f'replay_{k}_err_pct'].max():.1f}%")

# ---------------------------------------------------------------- C. attainable-probability deadline validation
def part(k, b):
    return "cal" if (k < 8 and b < 3) else "hold"
cfgs = []
esp = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
cfgs.append(("ESP32", 44, pd.DataFrame(dict(t=esp.elapsed_us / 1000, K=esp.K, part=[part(k, b) for k, b in zip(esp.key_id, esp.block)]))))
for st in (44, 65, 87):
    for u in (1, 2):
        d = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
        cfgs.append((f"RP2040 unit {u}", st, pd.DataFrame(dict(t=d.sign_us / 1000, K=d.K, part=[part(k, b) for k, b in zip(d.key, d.boot_block)]))))
vrows = []
for name, st, d in cfgs:
    cal = d[d.part == "cal"]; hold = d[d.part == "hold"]
    q = 1 - 1 / cal.K.mean(); Bp = cal[cal.K == 1].t.max(); Bm = cal[cal.K == 1].t.min(); Cp = cal[cal.K == 2].t.max() - Bm
    for eps in (1e-2, 1e-3, 1e-4):
        n_eps = int(np.ceil(np.log(eps) / np.log(q))); D = Bp + (n_eps - 1) * Cp
        exc = hold[hold.t > D]; it = int((hold.K > n_eps).sum()); cost = int(((hold.K <= n_eps) & (hold.t > D)).sum())
        N = len(hold); x = len(exc); z = 1.959964
        ctr = (x / N + z * z / (2 * N)) / (1 + z * z / N); half = z * np.sqrt(x / N * (1 - x / N) / N + z * z / (4 * N * N)) / (1 + z * z / N)
        vrows.append(dict(config=name, set=st, eps=eps, q_cal=q, n_eps=n_eps, D_ms=D, pred_iter_tail=q ** n_eps, holdout=N, exceed=x, exceed_iter=it, exceed_cost=cost,
                          obs_rate=x / N, wilson_lo=max(0, ctr - half), wilson_hi=ctr + half, iter_only_rate=it / N, expected_iter_exceed=N * q ** n_eps))
V = pd.DataFrame(vrows); V.to_csv(OUT + "/deadline_validation.csv", index=False)
print("\nC. held-out exceedance at attainable targets:"); print(V.round(6).to_string())

# ---------------------------------------------------------------- D. ct0 bound
Q = 8380417
for st, tau, g2 in ((44, 39, (Q - 1) // 88), (65, 49, (Q - 1) // 32), (87, 60, (Q - 1) // 32)):
    print(f"D. ML-DSA-{st}: tau*2^(d-1) = {tau * 4096:,} vs gamma2 = {g2:,} -> ct0 rejection {'impossible for valid keys' if tau * 4096 < g2 else 'not excluded by the bound'}")
