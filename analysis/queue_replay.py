"""Queue replay for the telemetry report workload (Section IX of the manuscript).

Semantics inferred from the timestamps (Section IV-D / V-E):
  * releases at i*P; a release is dropped when 8 requests are already pending;
  * a pending slot is held until the request starts; the server (signing core)
    becomes free at `available` (after the output check); the next request
    starts at max(available, release) + dispatch overhead.
Level 1: replay each unsaturated run with its own observed service, check and
         dispatch times; compare flags and timestamps.
Level 2a: predict every 100 ms and 250 ms run from service times of OTHER
         replicates of the same board and mode (independent fixtures).
Level 2b: ESP32 diverse-workload replay from the controlled campaign.
Permutation: ESP32 order sensitivity (same multiset of service times).
"""
import sys, glob
import numpy as np, pandas as pd

ROOT = sys.argv[1]
D = ROOT + "/measurements/telemetry/"
OUT = sys.argv[2]
NSIM = int(sys.argv[3]) if len(sys.argv) > 3 else 500
SENT = 4294967295
WINDOW = 600_000_000
QCAP = 8


def replay(period_us, n_rel, svc, chk, disp, window=WINDOW, qcap=QCAP):
    rel = np.arange(n_rel, dtype=np.int64) * period_us
    start = np.full(n_rel, SENT, np.int64); ready = start.copy(); avail = start.copy()
    flag = np.zeros(n_rel, np.int64)
    pending = []; free_at = 0; i = 0
    while i < n_rel or pending:
        t_rel = rel[i] if i < n_rel else None
        t_srv = free_at if pending else None
        if t_rel is not None and (t_srv is None or t_rel < t_srv):
            if len(pending) >= qcap:
                flag[i] = 1
            else:
                pending.append(i)
            i += 1
            continue
        j = pending.pop(0)
        s = max(free_at, rel[j]) + int(disp[j])
        start[j] = s; ready[j] = s + int(svc[j]); avail[j] = ready[j] + int(chk[j])
        free_at = avail[j]
    for j in range(n_rel):
        if flag[j] == 1:
            continue
        flag[j] = 4 if ready[j] == SENT else (6 if ready[j] > window else 2)
    return dict(release=rel, start=start, ready=ready, available=avail, flag=flag)


def outcomes(sim, P):
    f = sim["flag"]; late = (sim["ready"] - sim["release"]) > P
    return dict(dropped=int((f == 1).sum()), late=int(((f == 2) & late).sum()),
                censored=int(((f == 4) | (f == 6)).sum()), completed=int((f == 2).sum()),
                failures=int((f == 1).sum() + ((f == 2) & late).sum() + ((f == 4) | (f == 6)).sum()))


def rp_runs():
    rr = pd.read_csv(D + "rp2040_report.csv")
    out = []
    for (b, run), g in rr.groupby(["board", "run"]):
        g = g.sort_values("request").reset_index(drop=True)
        ok = g.start != SENT
        prev_av = g.available.where(g.available != SENT).shift(1).ffill().fillna(0)
        rec = dict(board=b, run=run, mode=g["mode"].iloc[0], period_ms=int(g.period_ms.iloc[0]), replicate=int(g.replicate.iloc[0]),
                   n=len(g), flags=g["flags"].values, release=g.release.values, start=g.start.values, ready=g.ready.values,
                   svc=(g.ready - g.start).where(ok).values, chk=(g.available - g.ready).where(ok).values,
                   disp=(g.start - np.maximum(g.release, prev_av)).where(ok).values)
        exe = g[g["flags"] == 2]
        rec["obs"] = dict(dropped=int((g["flags"] == 1).sum()), late=int(((exe.ready - exe.release) > rec["period_ms"] * 1000).sum()),
                          censored=int(g["flags"].isin([4, 6]).sum()), completed=int((g["flags"] == 2).sum()))
        rec["obs"]["failures"] = rec["obs"]["dropped"] + rec["obs"]["late"] + rec["obs"]["censored"]
        out.append(rec)
    return out


def esp_runs(fname="esp32_reports.csv", board="esp32"):
    """ESP32 runs; fname="esp32_reports_fresh.csv", board="esp32_fresh" reads the fresh-input set."""
    e = pd.read_csv(D + fname)
    out = []
    for (m, p, r), g in e.groupby(["mode", "period_ms", "replicate"]):
        g = g.sort_values("rep_id").reset_index(drop=True)
        start = g.released_us + g.started_off_us; ready = g.released_us + g.ready_off_us
        prev_ready = ready.shift(1).fillna(0); busy = g.released_us < prev_ready
        d_idle = float((start - g.released_us)[~busy].median())
        d_busy = float((start - prev_ready)[busy].median()) if busy.any() else d_idle
        n = len(g)
        rec = dict(board=board, run=f"{m}-{p}-{r}", mode=m, period_ms=int(p), replicate=int(r), n=n,
                   flags=np.full(n, 2), release=g.released_us.values, start=start.values, ready=ready.values,
                   svc=(ready - start).values.astype(float), chk=np.full(n, d_busy - d_idle), disp=np.full(n, d_idle),
                   fixtures=int(g.fixture_id.nunique()), fixture_seq=g.fixture_id.values)
        late = int((g.ready_off_us > p * 1000).sum())
        rec["obs"] = dict(dropped=0, late=late, censored=0, completed=n, failures=late)
        out.append(rec)
    return out


def level1(runs):
    rows = []
    for r in runs:
        P = r["period_ms"] * 1000
        if r["board"] != "esp32" and r["period_ms"] == 100:
            continue  # saturated: dropped requests have no service time
        svc = np.where(np.isnan(r["svc"]), np.nanmedian(r["svc"]), r["svc"])
        chk = np.where(np.isnan(r["chk"]), np.nanmedian(r["chk"]), r["chk"])
        disp = np.where(np.isnan(r["disp"]), np.nanmedian(r["disp"]), r["disp"])
        sim = replay(P, r["n"], svc, chk, disp)
        pred = outcomes(sim, P)
        both = (sim["ready"] != SENT) & (r["ready"] != SENT)
        dready = np.abs(sim["ready"][both].astype(np.int64) - r["ready"][both].astype(np.int64))
        rows.append(dict(board=r["board"], run=r["run"], mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"], n=r["n"],
                         obs_late=r["obs"]["late"], pred_late=pred["late"], obs_censored=r["obs"]["censored"], pred_censored=pred["censored"],
                         obs_dropped=r["obs"]["dropped"], pred_dropped=pred["dropped"],
                         flag_agreement=int((sim["flag"] == r["flags"]).sum()), max_ready_diff_us=int(dready.max()), median_ready_diff_us=float(np.median(dready))))
    return pd.DataFrame(rows)


def race_check(runs):
    """At 100 ms on the RP2040: how many observed admission decisions contradict the
    bounded-queue rule when the pending count is evaluated at the nominal release
    instant (slot freed when the server becomes free)."""
    rows = []
    for r in runs:
        if r["board"] == "esp32" or r["period_ms"] != 100:
            continue
        ok = r["start"] != SENT
        rel_ex = r["release"][ok]
        av = np.r_[0, (r["ready"][ok] + r["chk"][ok])[:-1]]
        unfinished = r["flags"] == 4   # released, never started: pending until the window end
        rel_un = r["release"][unfinished]
        bad = 0; margins = []
        for i in range(r["n"]):
            t = r["release"][i]
            pend = int(((rel_ex < t) & (av > t)).sum()) + int((rel_un < t).sum())
            admitted = r["flags"][i] != 1
            if (admitted and pend >= QCAP) or ((not admitted) and pend < QCAP):
                bad += 1
                margins.append(int(np.min(np.abs(av - t))))
        rows.append(dict(board=r["board"], run=r["run"], mode=r["mode"], replicate=r["replicate"], decisions=r["n"],
                         inconsistent=bad, max_margin_us=max(margins) if margins else 0))
    return pd.DataFrame(rows)


def pools(runs):
    """Service pools by (board, mode, replicate): executed requests of runs with no drops."""
    pool = {}
    for r in runs:
        if r["board"] != "esp32" and r["period_ms"] == 100:
            continue
        ok = ~np.isnan(r["svc"])
        pool.setdefault((r["board"], r["mode"], r["replicate"]), []).append(
            np.c_[r["svc"][ok], r["chk"][ok], r["disp"][ok]])
    return {k: np.vstack(v) for k, v in pool.items()}


def level2a(runs, nsim, seed=1):
    rng = np.random.default_rng(seed); pool = pools(runs); rows = []
    for r in runs:
        if r["period_ms"] == 1000:
            continue
        P = r["period_ms"] * 1000; n = r["n"]
        others = np.vstack([v for k, v in pool.items() if k[0] == r["board"] and k[1] == r["mode"] and k[2] != r["replicate"]])
        preds = []
        for s in range(nsim):
            idx = rng.integers(0, len(others), n)
            sim = replay(P, n, others[idx, 0], others[idx, 1], others[idx, 2])
            preds.append(outcomes(sim, P))
        pr = pd.DataFrame(preds)
        row = dict(board=r["board"], run=r["run"], mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"], n=n,
                   pool_n=len(others), pool_mean_ms=others[:, 0].mean() / 1000,
                   run_mean_ms=np.nanmean(r["svc"]) / 1000)
        for k in ("failures", "late", "dropped", "censored"):
            lo, med, hi = np.percentile(pr[k], [2.5, 50, 97.5])
            row.update({f"obs_{k}": r["obs"][k], f"pred_{k}_lo": lo, f"pred_{k}_med": med, f"pred_{k}_hi": hi})
        rows.append(row)
    return pd.DataFrame(rows)


def level2b_esp32(runs, nsim, seed=3):
    """Diverse-workload replay: service times drawn from the controlled ESP32 campaign."""
    rng = np.random.default_rng(seed)
    ctl = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(ROOT + "/measurements/signing/esp32/block_*.csv"))])
    svc_pool = ctl.elapsed_us.values.astype(float)
    rows = []
    for r in runs:
        if r["board"] != "esp32" or r["period_ms"] == 1000:
            continue
        P = r["period_ms"] * 1000; n = r["n"]
        lates = []
        for s in range(nsim):
            sv = svc_pool[rng.integers(0, len(svc_pool), n)]
            sim = replay(P, n, sv, r["chk"], r["disp"])
            lates.append(outcomes(sim, P)["late"])
        lo, med, hi = np.percentile(lates, [2.5, 50, 97.5])
        rows.append(dict(run=r["run"], mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"], obs_late=r["obs"]["late"],
                         ctl_pool_n=len(svc_pool), ctl_mean_ms=svc_pool.mean() / 1000, run_mean_ms=r["svc"].mean() / 1000,
                         pred_late_lo=lo, pred_late_med=med, pred_late_hi=hi, pred_late_min=min(lates), pred_late_max=max(lates)))
    return pd.DataFrame(rows)


def permutation_esp32(runs, nperm, seed=2):
    rng = np.random.default_rng(seed); rows = []
    for r in runs:
        if r["board"] != "esp32" or r["period_ms"] == 1000:
            continue
        P = r["period_ms"] * 1000; n = r["n"]
        lates = []
        for s in range(nperm):
            sim = replay(P, n, rng.permutation(r["svc"]), r["chk"], r["disp"])
            lates.append(outcomes(sim, P)["late"])
        lo, med, hi = np.percentile(lates, [2.5, 50, 97.5])
        rows.append(dict(run=r["run"], mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"], obs_late=r["obs"]["late"],
                         distinct_tuples=r["fixtures"], over_period=int((r["svc"] > P).sum()),
                         perm_late_lo=lo, perm_late_med=med, perm_late_hi=hi, perm_late_min=min(lates), perm_late_max=max(lates)))
    return pd.DataFrame(rows)


def response_curves(runs, seed=5):
    """Observed vs replayed (level 2a, one draw) response-time samples for figure panels."""
    rng = np.random.default_rng(seed); pool = pools(runs); out = {}
    for r in runs:
        key = (r["board"], r["mode"], r["period_ms"], r["replicate"])
        if key not in [("esp32", "inline", 100, 1), ("rp2040_1", "worker", 250, 1), ("rp2040_1", "worker", 100, 1)]:
            continue
        P = r["period_ms"] * 1000; n = r["n"]
        others = np.vstack([v for k, v in pool.items() if k[0] == r["board"] and k[1] == r["mode"] and k[2] != r["replicate"]])
        idx = rng.integers(0, len(others), n)
        sim = replay(P, n, others[idx, 0], others[idx, 1], others[idx, 2])
        ok = r["ready"] != SENT
        obs = (r["ready"][ok].astype(np.int64) - r["release"][ok].astype(np.int64)) / 1000
        sok = sim["ready"] != SENT
        pred = (sim["ready"][sok] - sim["release"][sok]) / 1000
        name = "_".join(map(str, key))
        out[name + "_obs"] = np.sort(obs); out[name + "_pred"] = np.sort(pred)
    np.savez(OUT + "/response_curves.npz", **out)


if __name__ == "__main__":
    runs = rp_runs() + esp_runs()
    l1 = level1(runs); l1.to_csv(OUT + "/replay_level1.csv", index=False); print(l1.to_string())
    rc = race_check(runs); rc.to_csv(OUT + "/replay_race.csv", index=False); print(rc.to_string())
    l2 = level2a(runs, NSIM); l2.to_csv(OUT + "/replay_level2a.csv", index=False); print(l2.round(1).to_string())
    l2b = level2b_esp32(runs, NSIM); l2b.to_csv(OUT + "/replay_level2b_esp32.csv", index=False); print(l2b.round(1).to_string())
    pe = permutation_esp32(runs, NSIM); pe.to_csv(OUT + "/replay_permutation_esp32.csv", index=False); print(pe.round(1).to_string())
    response_curves(runs)
