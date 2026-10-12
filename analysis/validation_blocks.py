"""Test the frozen calibration-coverage rule on the new validation blocks (Section VIII-F).

Usage:  python3 -I validation_blocks.py <data> <out> [frozen_rule.json]

Reads <data>/measurements/signing/rp2040/validation/rp2040_<u>_set<N>_validation.csv (from
ingest_validation.py) and the pre-registered frozen_rule.json (default: <data>/frozen_rule.json;
its SHA-256 is printed so it can be compared with the one recorded in the validation session).
Nothing is re-estimated: B+, C+, n_eps and D(n_eps) are read from the frozen file.

Per configuration it reports the pre-registered predictions:
  P1  exceedances of D(K) = B+ + (K-1) C+ among new calls with K >= 2 (prediction: none);
  P2  first-candidate calls above B+ (count, largest excess);
  P3  exceedance rate of the fixed deadline D(n_eps) at eps = 1e-2 and 1e-3, with Wilson 95%
      intervals, classified as established (interval below eps), not established (contains eps)
      or contradicted (interval above eps);
  P4  rate of K > n_eps against q_cal^n_eps.
Also, for comparison only: what the unfrozen first-24,000-call envelope of the original paper
would have given on the same new calls (i.e. C+ from the w0 cost for unit 1 at ML-DSA-65).
Writes <out>/validation_blocks.csv and prints LaTeX rows.
"""
import sys, os, glob, json, hashlib
import numpy as np, pandas as pd

ROOT = sys.argv[1]; OUT = sys.argv[2]
FR = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "frozen_rule.json")
raw = open(FR, "rb").read(); print("frozen_rule.json sha256:", hashlib.sha256(raw).hexdigest())
rule = json.loads(raw)
cfg = {(c["config"], c["set"]): c for c in rule["configurations"]}

def wilson(x, N, z=1.959964):
    p = x / N; ctr = (p + z * z / (2 * N)) / (1 + z * z / N); half = z * np.sqrt(p * (1 - p) / N + z * z / (4 * N * N)) / (1 + z * z / N)
    return max(0.0, ctr - half), ctr + half

rows = []
for f in sorted(glob.glob(f"{ROOT}/measurements/signing/rp2040/validation/rp2040_*_set*_validation.csv")):
    d = pd.read_csv(f); u = int(d.board.iloc[0][-1]); st = int(d.set.iloc[0]); name = f"RP2040 unit {u}"
    c = cfg[(name, st)]; e = c["envelope"]; Bp, Cp = e["B_plus_ms"], e["C_plus_ms"]
    t = d.sign_us / 1000; K = d.K
    env = Bp + (K - 1) * Cp
    exc2 = d[(K >= 2) & (t > env)]
    first = d[(K == 1) & (t > Bp)]
    row = dict(config=name, set=st, blocks=int(d.boot_block.nunique()), n=len(d), max_K=int(K.max()), mean_K=float(K.mean()),
               calibration_subset=c["calibration_subset"], B_plus_ms=Bp, C_plus_ms=Cp, governing_exit=e["governing_exit"],
               P1_exceed_Kge2=len(exc2), P1_max_excess_ms=float((t - env)[exc2.index].max()) if len(exc2) else 0.0,
               P1_K_of_exceed=sorted(exc2.K.tolist())[:10],
               P2_first_candidate_exceed=len(first), P2_max_excess_ms=float((t[first.index] - Bp).max()) if len(first) else 0.0,
               min_margin_Kge2_ms=float((env - t)[K >= 2].min()))
    for eps_s, tg in c["attainable_targets"].items():
        eps = float(eps_s); n_eps = tg["n_eps"]; D = tg["D_ms"]
        x = int((t > D).sum()); it = int((K > n_eps).sum()); lo, hi = wilson(x, len(d))
        verdict = "established" if hi < eps else ("contradicted" if lo > eps else "not established")
        tag = "1e2" if eps == 1e-2 else "1e3"
        row.update({f"P3_{tag}_n_eps": n_eps, f"P3_{tag}_D_ms": D, f"P3_{tag}_exceed": x, f"P3_{tag}_rate": x / len(d), f"P3_{tag}_wilson_lo": lo, f"P3_{tag}_wilson_hi": hi, f"P3_{tag}_verdict": verdict,
                    f"P4_{tag}_K_gt_n": it, f"P4_{tag}_expected": len(d) * tg["predicted_iteration_tail"], f"P3_{tag}_exceed_with_K_le_n": int(((t > D) & (K <= n_eps)).sum())})
    # comparison: the unfrozen first-24,000-call envelope of the original paper
    orig = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
    cal = orig[(orig.key < 8) & (orig.boot_block < 3)]; k1 = cal[cal.K == 1].sign_us / 1000; k2 = cal[cal.K == 2]
    Bp0, Bm0 = k1.max(), k1.min(); Cp0 = (k2.sign_us / 1000 - Bm0).max()
    env0 = Bp0 + (K - 1) * Cp0
    row.update(orig_B_plus_ms=float(Bp0), orig_C_plus_ms=float(Cp0), orig_exceed_Kge2=int(((K >= 2) & (t > env0)).sum()))
    rows.append(row)
T = pd.DataFrame(rows); T.to_csv(OUT + "/validation_blocks.csv", index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 60)
print(T.drop(columns=["P1_K_of_exceed"]).round(5).to_string())
print("\nLaTeX rows (config, set, n, B+, C+, exit, P1 exceed K>=2, P2 first-candidate exceed (max excess ms), 1e-2: D, exc, rate (Wilson), 1e-3: D, exc, rate (Wilson)):")
for _, r in T.iterrows():
    print(f"RP U{r.config[-1]} & {r.set} & {r.n:,} & {r.B_plus_ms:.1f} & {r.C_plus_ms:.2f} & {r.governing_exit} & {r.P1_exceed_Kge2} & " + (f"{r.P2_first_candidate_exceed}" if r.P2_first_candidate_exceed == 0 else f"{r.P2_first_candidate_exceed} ({r.P2_max_excess_ms:.3f})") + " & "
          f"{r.P3_1e2_D_ms:,.0f} & {r.P3_1e2_exceed} & {100*r.P3_1e2_rate:.2f} ({100*r.P3_1e2_wilson_lo:.2f}--{100*r.P3_1e2_wilson_hi:.2f}) & "
          f"{r.P3_1e3_D_ms:,.0f} & {r.P3_1e3_exceed} & {100*r.P3_1e3_rate:.3f} ({100*r.P3_1e3_wilson_lo:.3f}--{100*r.P3_1e3_wilson_hi:.3f}) \\\\")
