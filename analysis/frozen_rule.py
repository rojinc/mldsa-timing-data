"""Freeze the calibration-coverage rule of Section VIII-D and pre-register its predictions.

Usage:  python3 -I frozen_rule.py <data> <out>

Everything here is computed from the original controlled campaign (dataset v1.0/v1.1, 50,000
calls per configuration).  The output, <out>/frozen_rule.json, is hashed (<out>/frozen_rule.sha256)
and the hash is recorded in the validation session before any new block is captured, so the rule
and its predicted deadlines cannot be adjusted after the new data are seen.

THE RULE (R1)
 1. Calibration subset S0: keys 0-7, boot blocks 0-2 (24,000 calls), as in Section VIII.
 2. Coverage condition: S0 must contain at least one single-rejection call (K = 2) for every
    reachable exit.  Reachable exits are z, w0 and hint; ct0 is unreachable for valid ML-DSA-65 and
    -87 keys and unobserved for ML-DSA-44 (it cannot be covered and is reported as such).
 3. If an exit is not covered, enlarge the subset in this fixed order and take the first that
    covers every reachable exit: S1 = all keys, blocks 0-2; S2 = all keys, blocks 0-3; S3 = the full
    campaign (all keys, blocks 0-4).  If S3 does not cover, no envelope is issued.
 4. From the chosen subset S: B+ = max signing time of K=1 calls; B- = min signing time of K=1
    calls; C+ = max over K=2 calls of (t - B-).  Envelope D(K) = B+ + (K - 1) C+.
 5. Attainable-target deadlines: q = 1 - 1/mean(K) over S; n_eps = ceil(log eps / log q) for
    eps = 1e-2 and 1e-3; D(n_eps) as in 4.

PRE-REGISTERED PREDICTIONS, tested on new reset-separated blocks with fresh randomness
(10,000 calls per configuration: two blocks of 10 keys x 5 messages x 100 repetitions):
 P1. No new call with K >= 2 exceeds D(K).  (Primary; one exceedance falsifies P1 for that
     configuration.)
 P2. New calls with K = 1 may exceed B+; their number and the largest excess are reported.
 P3. The exceedance rate of the fixed deadline D(n_eps) is at most eps for eps = 1e-2 and 1e-3,
     tested by whether the observed rate's Wilson 95% interval lies below eps (established),
     contains eps (not established), or lies above eps (contradicted).
 P4. The iteration-count exceedance K > n_eps occurs at a rate consistent with q^n_eps.
"""
import sys, os, glob, json, hashlib
import numpy as np, pandas as pd

ROOT = sys.argv[1]; OUT = sys.argv[2]
EXITS = {"z": "n_z", "w0": "n_w0", "hint": "n_hint"}

def subsets(d):
    yield "S0 (keys 0-7, blocks 0-2)", (d.key < 8) & (d.block < 3)
    yield "S1 (all keys, blocks 0-2)", d.block < 3
    yield "S2 (all keys, blocks 0-3)", d.block < 4
    yield "S3 (all keys, blocks 0-4)", d.block < 5

cfgs = []
esp = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
cfgs.append(("ESP32", 44, pd.DataFrame(dict(t=esp.elapsed_us / 1000, K=esp.K, key=esp.key_id, block=esp.block, n_z=esp.reject_z, n_w0=esp.reject_w0, n_ct0=esp.reject_ct0, n_hint=esp.reject_hint))))
for st in (44, 65, 87):
    for u in (1, 2):
        d = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
        cfgs.append((f"RP2040 unit {u}", st, pd.DataFrame(dict(t=d.sign_us / 1000, K=d.K, key=d.key, block=d.boot_block, n_z=d.n_z, n_w0=d.n_w0, n_ct0=d.n_ct0, n_hint=d.n_hint))))

out = {"rule": "R1", "description": __doc__.strip(), "configurations": []}
for name, st, d in cfgs:
    chosen = None
    cov_log = []
    for label, mask in subsets(d):
        s = d[mask]; k2 = s[s.K == 2]
        cov = {e: int((k2[c] > 0).sum()) for e, c in EXITS.items()}
        cov_log.append({"subset": label, "n": int(len(s)), "K2_single_rejection_calls_by_exit": cov})
        if all(v > 0 for v in cov.values()):
            chosen = (label, s); break
    if chosen is None:
        out["configurations"].append({"config": name, "set": st, "coverage": cov_log, "envelope": None}); continue
    label, s = chosen
    k1 = s[s.K == 1].t; k2 = s[s.K == 2]
    Bp, Bm = float(k1.max()), float(k1.min()); Cp = float((k2.t - Bm).max())
    gov = k2.loc[(k2.t - Bm).idxmax()]; gov_exit = [e for e, c in EXITS.items() if gov[c] > 0][0]
    q = 1 - 1 / float(s.K.mean())
    targets = {}
    for eps in (1e-2, 1e-3):
        n_eps = int(np.ceil(np.log(eps) / np.log(q)))
        targets[f"{eps:g}"] = {"n_eps": n_eps, "D_ms": round(Bp + (n_eps - 1) * Cp, 4), "predicted_iteration_tail": q ** n_eps}
    out["configurations"].append({
        "config": name, "set": st, "coverage": cov_log, "calibration_subset": label, "n_calibration": int(len(s)),
        "ct0_note": "unreachable for valid keys" if st in (65, 87) else "not excluded by the bound, unobserved in the campaign, not covered",
        "envelope": {"B_plus_ms": round(Bp, 4), "B_minus_ms": round(Bm, 4), "C_plus_ms": round(Cp, 4), "governing_exit": gov_exit,
                     "D_of_K_ms": "B_plus + (K-1)*C_plus", "D_examples_ms": {str(k): round(Bp + (k - 1) * Cp, 3) for k in (2, 5, 10, 20, 32, 50)}},
        "q_cal": q, "mean_K_cal": float(s.K.mean()), "attainable_targets": targets,
        "predictions": ["P1: zero exceedances of D(K) among new calls with K>=2",
                        "P2: K=1 exceedances of B_plus reported (count, max excess)",
                        "P3: rate(t > D(n_eps)) <= eps, by Wilson 95% interval",
                        "P4: rate(K > n_eps) consistent with q_cal^n_eps"]})
os.makedirs(OUT, exist_ok=True)
txt = json.dumps(out, indent=1, sort_keys=True)
open(OUT + "/frozen_rule.json", "w").write(txt + "\n")
h = hashlib.sha256((txt + "\n").encode()).hexdigest()
open(OUT + "/frozen_rule.sha256", "w").write(h + "  frozen_rule.json\n")
pd.set_option("display.width", 220)
rows = []
for c in out["configurations"]:
    e = c["envelope"]; t = c["attainable_targets"]
    rows.append(dict(config=c["config"], set=c["set"], subset=c["calibration_subset"], n_cal=c["n_calibration"], B_plus=e["B_plus_ms"], C_plus=e["C_plus_ms"], exit=e["governing_exit"],
                     n_1e2=t["0.01"]["n_eps"], D_1e2=t["0.01"]["D_ms"], n_1e3=t["0.001"]["n_eps"], D_1e3=t["0.001"]["D_ms"]))
print(pd.DataFrame(rows).to_string(index=False))
print("frozen_rule.json sha256:", h)
