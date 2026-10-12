"""Quiet-benchmark counterfactual (Section X of the manuscript).

Replays every RP2040 run at 100 and 250 ms with signing service times drawn from the controlled
campaign of the same unit (ML-DSA-44, 50,000 signatures, measured without the telemetry harness)
instead of from the telemetry runs, keeping the run's own dispatch and post-signing durations
(drawn with replacement from its executed requests).  Reports the predicted dropped and late
counts against the observed ones.  Seed 7.
"""
import sys, os
import numpy as np, pandas as pd

ROOT = sys.argv[1]; OUT = sys.argv[2]; NSIM = int(sys.argv[3]) if len(sys.argv) > 3 else 300
sys.argv = ["x", ROOT, OUT]
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "queue_replay.py")).read().split("if __name__")[0])

rng = np.random.default_rng(7)
ctl = {u: pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set44.csv").sign_us.values.astype(float) for u in (1, 2)}
rows = []
for r in rp_runs():
    if r["period_ms"] == 1000:
        continue
    u = 1 if r["board"] == "rp2040_1" else 2; pool = ctl[u]
    P = r["period_ms"] * 1000; n = r["n"]
    ok = ~np.isnan(r["svc"]); chk = r["chk"][ok]; disp = r["disp"][ok]
    preds = []
    for s in range(NSIM):
        sv = pool[rng.integers(0, len(pool), n)]
        idx = rng.integers(0, len(chk), n)
        sim = replay(P, n, sv, chk[idx], disp[idx]); preds.append(outcomes(sim, P))
    pr = pd.DataFrame(preds)
    row = dict(board=r["board"], run=r["run"], mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"],
               ctl_mean_ms=pool.mean() / 1000, run_mean_ms=np.nanmean(r["svc"]) / 1000)
    for k in ("dropped", "late"):
        lo, med, hi = np.percentile(pr[k], [2.5, 50, 97.5])
        row.update({f"obs_{k}": r["obs"][k], f"ctl_{k}_lo": lo, f"ctl_{k}_med": med, f"ctl_{k}_hi": hi,
                    f"ctl_{k}_err_pct": 100 * (med - r["obs"][k]) / r["obs"][k] if r["obs"][k] else np.nan})
    rows.append(row)
T = pd.DataFrame(rows); T.to_csv(OUT + "/quiet_benchmark.csv", index=False)
pd.set_option("display.width", 220)
print(T[["board", "mode", "period_ms", "replicate", "ctl_mean_ms", "run_mean_ms", "obs_dropped", "ctl_dropped_med", "ctl_dropped_err_pct", "obs_late", "ctl_late_med", "ctl_late_err_pct"]].round(1).to_string())
for per in (100, 250):
    s = T[T.period_ms == per]
    k = "dropped" if per == 100 else "late"
    print(f"{per} ms: {k} error of controlled-pool replay: {s[f'ctl_{k}_err_pct'].min():.1f} to {s[f'ctl_{k}_err_pct'].max():.1f}% (median {s[f'ctl_{k}_err_pct'].median():.1f}%)")
