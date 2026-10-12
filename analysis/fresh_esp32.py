"""Fresh-input ESP32 telemetry runs: outcomes, replay levels and baselines (Sections IV-D, IX-C,
IX-D and supplementary S-III of the manuscript).

Usage:  python3 -I fresh_esp32.py <data> <out> [fresh_reports.csv]

Reads <data>/measurements/telemetry/esp32_reports_fresh.csv (or the file given as third argument),
whose columns are those of esp32_reports.csv.  With the fresh-input policy every request of a run
has its own message and signing randomness and fixture_id is the request id; the script checks that.

Per run it reports: late count and rate; share of signing times above the period; mean signing
time; the inferred dispatch and post-signing constants (as esp_runs() in queue_replay.py infers
them for the fixed-fixture runs); the level-1 same-run replay (must reproduce the late count
exactly); the level-2 replay from the other two fresh replicates of the same mode (300 sequences,
conditional simulation interval, same construction as Table S2); the controlled-pool replay from
the 50,000 controlled-campaign signatures (300 sequences; the scenario of Section IX-D); and the
two baselines of Table S9 computed from the controlled pool (mean capacity for drops, share above
the period for late reports).  Seeds: 13 (other-replicate pools), 17 (controlled pool) and 19 (independent forecast).

Outputs <out>/fresh_esp32.csv and <out>/fresh_esp32_summary.txt.
"""
import sys, os, glob
import numpy as np, pandas as pd

ROOT = sys.argv[1]; OUT = sys.argv[2]
FRESH = sys.argv[3] if len(sys.argv) > 3 else f"{ROOT}/measurements/telemetry/esp32_reports_fresh.csv"
sys.argv = ["x", ROOT, OUT]
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "queue_replay.py")).read().split("if __name__")[0])

NSIM = 300
e = pd.read_csv(FRESH)
ctl = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))]).elapsed_us.values.astype(float)

# ---- per-run records, as esp_runs() builds them for the fixed-fixture runs
runs = []
for (m, p, r), g in e.groupby(["mode", "period_ms", "replicate"]):
    g = g.sort_values("rep_id").reset_index(drop=True)
    P = int(p) * 1000; n = len(g)
    start = g.released_us + g.started_off_us; ready = g.released_us + g.ready_off_us
    prev_ready = ready.shift(1).fillna(0); busy = g.released_us < prev_ready
    d_idle = float((start - g.released_us)[~busy].median())
    d_busy = float((start - prev_ready)[busy].median()) if busy.any() else d_idle
    chk = max(d_busy - d_idle, 0.0)
    runs.append(dict(mode=m, period_ms=int(p), replicate=int(r), n=n, P=P, svc=(ready - start).values.astype(float), ready_obs=ready.values,
                     chk=chk, disp=d_idle, late=int((g.ready_off_us > P).sum()), distinct=int(g.fixture_id.nunique()),
                     digests_ok=int((g.status == 0).sum()), max_depth=int(g.queue_depth.max())))

# ---- pools from the other fresh replicates (same mode, all periods), triples (svc, chk, disp)
pool = {}
for r in runs:
    pool.setdefault((r["mode"], r["replicate"]), []).append(np.c_[r["svc"], np.full(r["n"], r["chk"]), np.full(r["n"], r["disp"])])
pool = {k: np.vstack(v) for k, v in pool.items()}

rng_o = np.random.default_rng(13); rng_c = np.random.default_rng(17); rng_i = np.random.default_rng(19)
rows = []
for r in runs:
    P, n = r["P"], r["n"]
    # level 1: same run, own service times in order
    l1 = outcomes(replay(P, n, r["svc"], np.full(n, r["chk"]), np.full(n, r["disp"])), P)["late"]
    # level 2: other fresh replicates of the same mode
    others = np.vstack([v for k, v in pool.items() if k[0] == r["mode"] and k[1] != r["replicate"]])
    po = []
    for s in range(NSIM):
        idx = rng_o.integers(0, len(others), n)
        po.append(outcomes(replay(P, n, others[idx, 0], others[idx, 1], others[idx, 2]), P)["late"])
    o_lo, o_med, o_hi = np.percentile(po, [2.5, 50, 97.5])
    # controlled pool: 50,000 controlled-campaign signatures with the run's own constants (conditional forecast)
    pc = []
    for s in range(NSIM):
        sv = ctl[rng_c.integers(0, len(ctl), n)]
        pc.append(outcomes(replay(P, n, sv, np.full(n, r["chk"]), np.full(n, r["disp"])), P)["late"])
    c_lo, c_med, c_hi = np.percentile(pc, [2.5, 50, 97.5])
    # controlled pool with dispatch and post-signing constants drawn from the other fresh replicates
    # (every forecast input measured outside the run: independent forecast)
    pi = []
    for s in range(NSIM):
        sv = ctl[rng_i.integers(0, len(ctl), n)]; idx = rng_i.integers(0, len(others), n)
        pi.append(outcomes(replay(P, n, sv, others[idx, 1], others[idx, 2]), P)["late"])
    i_lo, i_med, i_hi = np.percentile(pi, [2.5, 50, 97.5])
    # level-1 timestamp agreement (same construction as level1() in queue_replay.py)
    sim1 = replay(P, n, r["svc"], np.full(n, r["chk"]), np.full(n, r["disp"]))
    dready = np.abs(sim1["ready"].astype(np.int64) - r["ready_obs"].astype(np.int64))
    # baselines of Table S9 from the controlled pool and from the other-replicate pool
    cycle_c = ctl.mean() + r["chk"] + r["disp"]; cycle_o = (others[:, 0] + others[:, 1] + others[:, 2]).mean()
    rows.append(dict(mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"], n=n, distinct_fixtures=r["distinct"], digests_ok=r["digests_ok"],
                     max_queue_depth=r["max_depth"], mean_sign_ms=r["svc"].mean() / 1000, max_sign_ms=r["svc"].max() / 1000,
                     share_above_P=float((r["svc"] > P).mean()), dispatch_ms=r["disp"] / 1000, post_signing_ms=r["chk"] / 1000,
                     late_obs=r["late"], late_rate_pct=100 * r["late"] / n, level1_late=l1,
                     other_pool_n=len(others), other_pool_mean_ms=others[:, 0].mean() / 1000, other_late_med=o_med, other_late_lo=o_lo, other_late_hi=o_hi,
                     ctl_pool_mean_ms=ctl.mean() / 1000, ctl_late_med=c_med, ctl_late_lo=c_lo, ctl_late_hi=c_hi,
                     indep_late_med=i_med, indep_late_lo=i_lo, indep_late_hi=i_hi, level1_max_ready_diff_us=int(dready.max()), level1_median_ready_diff_us=float(np.median(dready)),
                     base_capacity_drop_ctl=max(0, n - int(WINDOW // cycle_c)), base_capacity_drop_other=max(0, n - int(WINDOW // cycle_o)),
                     base_share_late_ctl=n * float((ctl > P).mean()), base_share_late_other=n * float((others[:, 0] > P).mean())))
T = pd.DataFrame(rows).sort_values(["period_ms", "mode", "replicate"]).reset_index(drop=True)
for k in ("other", "ctl", "indep"):
    T[f"{k}_err_pct"] = 100 * (T.late_obs - T[f"{k}_late_med"]) / T.late_obs.replace(0, np.nan)
    T[f"{k}_covered"] = (T.late_obs >= T[f"{k}_late_lo"]) & (T.late_obs <= T[f"{k}_late_hi"])
T["base_share_err_pct"] = 100 * (T.late_obs - T.base_share_late_ctl) / T.late_obs.replace(0, np.nan)
T.to_csv(OUT + "/fresh_esp32.csv", index=False)

pd.set_option("display.width", 250)
lines = []
def say(s=""):
    print(s); lines.append(s)
say("Fresh-input ESP32 runs (error = observed minus replay median, relative to observed):")
say(T[["mode", "period_ms", "replicate", "n", "distinct_fixtures", "digests_ok", "max_queue_depth", "mean_sign_ms", "max_sign_ms", "share_above_P", "dispatch_ms", "post_signing_ms",
       "late_obs", "late_rate_pct", "level1_late", "other_late_med", "other_late_lo", "other_late_hi", "other_err_pct", "other_covered",
       "ctl_late_med", "ctl_late_lo", "ctl_late_hi", "ctl_err_pct", "ctl_covered", "base_share_late_ctl", "base_share_err_pct", "base_capacity_drop_ctl"]].round(3).to_string())
h = T[T.period_ms == 100]
say(f"\n100 ms: observed late {h.late_obs.min()}-{h.late_obs.max()} ({h.late_rate_pct.min():.1f}-{h.late_rate_pct.max():.1f}%), "
    f"share of signing times above 100 ms {100*h.share_above_P.min():.1f}-{100*h.share_above_P.max():.1f}%, mean signing {h.mean_sign_ms.min():.1f}-{h.mean_sign_ms.max():.1f} ms")
say(f"  controlled-pool replay: medians {h.ctl_late_med.min():.0f}-{h.ctl_late_med.max():.0f}, intervals {h.ctl_late_lo.min():.0f}-{h.ctl_late_hi.max():.0f}, "
    f"errors {h.ctl_err_pct.min():+.1f} to {h.ctl_err_pct.max():+.1f}%, covered {int(h.ctl_covered.sum())} of {len(h)}")
say(f"  independent forecast (controlled pool + other-replicate constants): medians {h.indep_late_med.min():.0f}-{h.indep_late_med.max():.0f}, errors {h.indep_err_pct.min():+.1f} to {h.indep_err_pct.max():+.1f}%, covered {int(h.indep_covered.sum())} of {len(h)}")
say(f"  other-replicate replay: medians {h.other_late_med.min():.0f}-{h.other_late_med.max():.0f}, errors {h.other_err_pct.min():+.1f} to {h.other_err_pct.max():+.1f}%, covered {int(h.other_covered.sum())} of {len(h)}")
say(f"  share-above-period baseline (controlled pool): {h.base_share_late_ctl.min():.0f}-{h.base_share_late_ctl.max():.0f}, errors {h.base_share_err_pct.min():+.1f} to {h.base_share_err_pct.max():+.1f}%")
q = T[T.period_ms == 250]
say(f"250 ms: observed late {q.late_obs.min()}-{q.late_obs.max()}; controlled-pool medians {q.ctl_late_med.min():.0f}-{q.ctl_late_med.max():.0f} "
    f"(intervals up to {q.ctl_late_hi.max():.0f}), covered {int(q.ctl_covered.sum())} of {len(q)}; other-replicate covered {int(q.other_covered.sum())} of {len(q)}")
k = T[T.period_ms == 1000]
say(f"1000 ms: observed late {k.late_obs.min()}-{k.late_obs.max()}; controlled-pool medians {k.ctl_late_med.min():.0f}-{k.ctl_late_med.max():.0f}")
say(f"level 1 reproduces every late count: {bool((T.late_obs == T.level1_late).all())}; ready timestamps within {T.level1_max_ready_diff_us.max()} us (max over runs; medians {T.level1_median_ready_diff_us.min():.0f}-{T.level1_median_ready_diff_us.max():.0f} us)")
q2 = T[T.period_ms == 250]
say(f"250 ms independent forecast: medians {q2.indep_late_med.min():.0f}-{q2.indep_late_med.max():.0f}, intervals up to {q2.indep_late_hi.max():.0f}, covered {int(q2.indep_covered.sum())} of {len(q2)}")
say(f"all runs fresh (distinct fixture ids = requests): {bool((T.distinct_fixtures == T.n).all())}; digests ok: {int(T.digests_ok.sum())} of {int(T.n.sum())}")
say(f"dispatch {T.dispatch_ms.min():.2f}-{T.dispatch_ms.max():.2f} ms (inline {T[T['mode']=='inline'].dispatch_ms.min():.2f}-{T[T['mode']=='inline'].dispatch_ms.max():.2f}, "
    f"worker {T[T['mode']=='worker'].dispatch_ms.min():.2f}-{T[T['mode']=='worker'].dispatch_ms.max():.2f}); post-signing (100 ms runs) {h.post_signing_ms.min():.2f}-{h.post_signing_ms.max():.2f} ms")
say(f"controlled pool mean {ctl.mean()/1000:.1f} ms, share above 100 ms {100*(ctl>100000).mean():.2f}%, above 250 ms {100*(ctl>250000).mean():.3f}%")
say("\nFixed-fixture runs for comparison (manuscript): 375, 281, 563 late of 6,000 at 100 ms; none at 250 and 1,000 ms; controlled-pool scenario 500-608 at 100 ms, 0-7 at 250 ms.")
# supplementary Table S10 rows (Section S-XI): one row per run
say("\nSupplementary table rows (mode, P, rep, mean signing ms, share above P %, late obs, other-replicate replay med (lo--hi), err %, controlled pool conditional med (lo--hi), err %, independent med (lo--hi), err %, share baseline):")
def pm(x): return "--" if np.isnan(x) else f"{x:+.1f}"
for _, r in T.sort_values(["mode", "period_ms", "replicate"]).iterrows():
    say(f"{r['mode']} & {r.period_ms:,} & {r.replicate} & {r.mean_sign_ms:.1f} & {100*r.share_above_P:.2f} & {r.late_obs} & "
        f"{r.other_late_med:.0f} ({r.other_late_lo:.0f}--{r.other_late_hi:.0f}) & {pm(r.other_err_pct)} & "
        f"{r.ctl_late_med:.0f} ({r.ctl_late_lo:.0f}--{r.ctl_late_hi:.0f}) & {pm(r.ctl_err_pct)} & "
        f"{r.indep_late_med:.0f} ({r.indep_late_lo:.0f}--{r.indep_late_hi:.0f}) & {pm(r.indep_err_pct)} & {r.base_share_late_ctl:.0f} \\\\")
open(OUT + "/fresh_esp32_summary.txt", "w").write("\n".join(lines) + "\n")
