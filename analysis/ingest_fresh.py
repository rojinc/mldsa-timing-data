"""Build the two released files of the fresh-input ESP32 telemetry runs from the capture folders.

Usage:  python3 -I ingest_fresh.py <runs_dir> <data>

<runs_dir> holds one folder per run named telf_r<replicate>_<inline|worker>_<period>ms with the
capture of tools/capture_serial.py (telemetry_reports.csv, device_meta.txt, capture_status.txt).
Writes <data>/measurements/telemetry/esp32_reports_fresh.csv (same columns as esp32_reports.csv)
and esp32_runs_fresh.csv (same columns as esp32_runs.csv, plus fixture_policy and max_occupancy).
Only runs whose banner declares the fresh fixture policy and whose capture is complete are taken.
"""
import sys, re, os, glob
import pandas as pd

RUNS = sys.argv[1]; DATA = sys.argv[2]
rep_rows, run_rows = [], []
for d in sorted(glob.glob(os.path.join(RUNS, "telf_r*_*ms"))):
    m = re.search(r"telf_r(\d+)_(inline|worker)_(\d+)ms$", d)
    f = os.path.join(d, "telemetry_reports.csv")
    if not m or not os.path.isfile(f):
        continue
    meta = open(os.path.join(d, "device_meta.txt")).read() if os.path.isfile(os.path.join(d, "device_meta.txt")) else ""
    status = open(os.path.join(d, "capture_status.txt")).read() if os.path.isfile(os.path.join(d, "capture_status.txt")) else ""
    if "fixture policy: fresh" not in meta or "status=complete" not in status:
        print("skipped (not a complete fresh-input capture):", d); continue
    r, mode, p = int(m.group(1)), m.group(2), int(m.group(3))
    df = pd.read_csv(f)
    df.insert(0, "period_ms", p); df.insert(0, "mode", mode); df.insert(0, "replicate", r)
    rep_rows.append(df)
    kv = {}
    for line in meta.splitlines():
        for part in line.lstrip("# ").split():
            if "=" in part:
                k, v = part.split("=", 1)
                try: kv[k] = int(v)
                except ValueError: pass
    secs = int(re.search(r"run: (\d+) us", meta).group(1)) // 1_000_000
    run_rows.append(dict(replicate=r, mode=mode, period_ms=p, seconds=secs, acquisition_releases=kv["total"], on_time=kv["on_time"],
                         late=kv["late"], skipped=kv["skipped"], acquisition_misses=kv["deadline_failures"], report_rows=len(df),
                         dropped=kv["dropped"], completed=kv["completed"], censored=kv["censored"], max_pending=kv["max_occupancy"],
                         exception_log_truncated=kv["acq_exceptions"], all_passed=bool((df.status == 0).all() and (df.sign_rc == 0).all()),
                         fixture_policy="fresh", distinct_fixtures=int(df.fixture_id.nunique())))
if not rep_rows:
    sys.exit("no complete fresh-input runs found")
out = os.path.join(DATA, "measurements", "telemetry"); os.makedirs(out, exist_ok=True)
E = pd.concat(rep_rows, ignore_index=True); E.to_csv(os.path.join(out, "esp32_reports_fresh.csv"), index=False)
R = pd.DataFrame(run_rows).sort_values(["replicate", "mode", "period_ms"]); R.to_csv(os.path.join(out, "esp32_runs_fresh.csv"), index=False)
pd.set_option("display.width", 220); print(R.to_string(index=False))
print(f"\n{len(R)} runs, {len(E)} report rows -> {out}/esp32_reports_fresh.csv, esp32_runs_fresh.csv")
bad = R[R.distinct_fixtures < R.report_rows]
if len(bad):
    print("WARNING: repeated fixture ids in", bad.replicate.tolist(), bad["mode"].tolist(), bad.period_ms.tolist())
