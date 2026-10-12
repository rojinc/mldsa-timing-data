"""Utilisation of the report server (Table IX of the manuscript).

Partial utilisation: mean signing time (ready - start) / period.
Complete-server utilisation: mean complete service cycle / period, where the cycle is
dispatch + signing + post-signing work per executed request, as the replay defines them
(Section V-E).  On the ESP32 the post-signing duration is inferred per run from busy
periods and is only observable in the 100 ms runs (no request finds the server busy at
250 or 1,000 ms); for those runs the mean post-signing duration of the same mode's
100 ms runs is used.

Also: direction of the 28 admission-rule mismatches at 100 ms on the RP2040.
"""
import sys, os
import numpy as np, pandas as pd

ROOT = sys.argv[1]; OUT = sys.argv[2]
sys.argv = ["x", ROOT, OUT]
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "queue_replay.py")).read().split("if __name__")[0])

runs = rp_runs() + esp_runs()
if os.path.exists(D + "esp32_reports_fresh.csv"):      # fresh-input ESP32 set (dataset v1.1.0)
    runs += esp_runs("esp32_reports_fresh.csv", "esp32_fresh")
rows = []
for r in runs:
    ok = ~np.isnan(np.asarray(r["svc"], float))
    svc = np.asarray(r["svc"], float)[ok]; chk = np.asarray(r["chk"], float)[ok]; disp = np.asarray(r["disp"], float)[ok]
    rows.append(dict(board=r["board"], mode=r["mode"], period_ms=r["period_ms"], replicate=r["replicate"], n=int(ok.sum()),
                     svc_ms=svc.mean() / 1000, chk_ms=chk.mean() / 1000, disp_ms=disp.mean() / 1000))
T = pd.DataFrame(rows)
# ESP32: post-signing duration observable only at 100 ms
for b in ("esp32", "esp32_fresh"):
    for m in ("inline", "worker"):
        ref = T[(T.board == b) & (T["mode"] == m) & (T.period_ms == 100)].chk_ms.mean()
        sel = (T.board == b) & (T["mode"] == m) & (T.period_ms != 100)
        T.loc[sel, "chk_ms"] = ref; T.loc[sel, "chk_source"] = "100 ms runs, same mode"
T["chk_source"] = T["chk_source"].fillna("same run")
T["cycle_ms"] = T.svc_ms + T.chk_ms + T.disp_ms
T["rho_signing"] = T.svc_ms / T.period_ms; T["rho_server"] = T.cycle_ms / T.period_ms
T.to_csv(OUT + "/utilisation.csv", index=False)
pd.set_option("display.width", 200)
T["platform"] = np.where(T.board == "esp32", "ESP32", np.where(T.board == "esp32_fresh", "ESP32 fresh", "RP2040"))
g = T.groupby(["platform", "period_ms"]).agg(svc_min=("svc_ms", "min"), svc_max=("svc_ms", "max"), cyc_min=("cycle_ms", "min"), cyc_max=("cycle_ms", "max"),
                                            rs_min=("rho_signing", "min"), rs_max=("rho_signing", "max"), rv_min=("rho_server", "min"), rv_max=("rho_server", "max"))
print(g.round(3).to_string())
print("post-signing (ms) by board/mode at 100 ms:"); print(T[T.period_ms == 100].groupby(["board", "mode"]).chk_ms.agg(["min", "max"]).round(3).to_string())
print("dispatch (ms) by board/mode:"); print(T.groupby(["board", "mode"]).disp_ms.agg(["min", "max"]).round(3).to_string())

# ---- direction of the admission-rule mismatches (nominal-instant rule, slot freed at previous `available`)
drows = []
for r in rp_runs():
    if r["period_ms"] != 100:
        continue
    ok = r["start"] != SENT; rel = r["release"]; n = r["n"]
    prev_av = (r["ready"] + r["chk"])[ok]; free = np.zeros(n, np.int64); free[ok] = np.r_[0, prev_av[:-1]]
    unfinished = r["flags"] == 4
    for i in range(n):
        t = rel[i]; m = np.ones(n, bool); m[i] = False
        pend = int((m & ok & (rel < t) & (free > t)).sum()) + int((m & unfinished & (rel < t)).sum())
        admitted = r["flags"][i] != 1
        if admitted and pend >= QCAP:
            drows.append(dict(board=r["board"], run=r["run"], mode=r["mode"], kind="device admitted, rule drops", margin_us=int(np.min(np.abs(free[ok] - t)))))
        elif (not admitted) and pend < QCAP:
            drows.append(dict(board=r["board"], run=r["run"], mode=r["mode"], kind="device dropped, rule admits", margin_us=int(np.min(np.abs(free[ok] - t)))))
Dm = pd.DataFrame(drows); Dm.to_csv(OUT + "/replay_race_direction.csv", index=False)
print("admission mismatches by mode and direction:"); print(Dm.groupby(["mode", "kind"]).margin_us.agg(["count", "max"]).to_string())
