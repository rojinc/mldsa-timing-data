"""Check the recorded signing-randomness streams of the RP2040 campaign (supplementary Section S-XIII).

Usage:  python3 -I randomness_check.py <out.csv> <randomness_dir> [<randomness_dir> ...]

Each <randomness_dir> is the `randomness/` folder of a campaign or validation capture session
(rp2040_<unit>_<set>_<block|pilot|stages>.bin with a JSON sidecar giving its SHA-256 and record
count; one record = the 32 bytes served to one randombytes() call). For every file:
  - the SHA-256 and the record count are checked against the sidecar;
  - byte uniformity: Pearson chi-square over the 256 byte values (255 degrees of freedom);
  - fraction of one bits.
Across all files: number of duplicated 32-byte records. A summary line is printed for all files and
for the streams of RP2040 unit 1 at ML-DSA-65 (the configuration with few single-hint calls).
Uses only the Python standard library, so it runs where numpy/scipy are not installed.
"""
import sys, os, glob, json, hashlib, math, csv


def chi2_sf(x, k):
    """Upper tail of the chi-square distribution: regularized upper incomplete gamma Q(k/2, x/2)."""
    a, z = k / 2.0, x / 2.0
    if z <= 0:
        return 1.0
    if z < a + 1:                       # series for P, then Q = 1 - P
        term = s = 1.0 / a; n = a
        for _ in range(10000):
            n += 1; term *= z / n; s += term
            if abs(term) < abs(s) * 1e-15:
                break
        return max(0.0, 1.0 - s * math.exp(-z + a * math.log(z) - math.lgamma(a)))
    b = z + 1 - a; c = 1e300; d = 1 / b; h = d   # continued fraction for Q (Lentz)
    for i in range(1, 10000):
        an = -i * (i - a); b += 2
        d = an * d + b; d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c; c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d; delta = d * c; h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-z + a * math.log(z) - math.lgamma(a)) * h


OUT = sys.argv[1]; DIRS = sys.argv[2:]
rows = []; seen = set(); dup = 0; total = 0
POP = [bin(i).count("1") for i in range(256)]
for D in DIRS:
    for f in sorted(glob.glob(os.path.join(D, "rp2040_*.bin"))):
        raw = open(f, "rb").read(); side = json.load(open(f[:-4] + ".json"))
        n = len(raw) // 32
        cnt = [0] * 256
        for b in raw:
            cnt[b] += 1
        e = len(raw) / 256.0
        chi = sum((c - e) ** 2 for c in cnt) / e
        ones = sum(c * POP[i] for i, c in enumerate(cnt)) / (8.0 * len(raw))
        for i in range(n):
            r = raw[32 * i:32 * i + 32]
            if r in seen:
                dup += 1
            else:
                seen.add(r)
        total += n
        rows.append(dict(session=os.path.basename(os.path.dirname(os.path.abspath(D))), file=os.path.basename(f), records=n,
                         count_ok=int(n == side["count"] and len(raw) == 32 * n),
                         sha256_ok=int(hashlib.sha256(raw).hexdigest() == side["sha256"]),
                         chi2=round(chi, 3), chi2_p=round(chi2_sf(chi, 255), 4), ones_fraction=round(ones, 5)))
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def summary(rs, label):
    ps = [r["chi2_p"] for r in rs]; fr = [r["ones_fraction"] for r in rs]
    print(f"{label}: {len(rs)} files, {sum(r['records'] for r in rs):,} records, hashes ok {sum(r['sha256_ok'] for r in rs)}/{len(rs)}, "
          f"counts ok {sum(r['count_ok'] for r in rs)}/{len(rs)}; byte chi2 p {min(ps):.3f}-{max(ps):.3f}, "
          f"{sum(p < 0.05 for p in ps)} below 0.05; one-bit fraction {min(fr):.4f}-{max(fr):.4f}")


summary(rows, "All files")
summary([r for r in rows if r["file"].startswith("rp2040_1_65_")], "RP2040 unit 1, ML-DSA-65")
print(f"Duplicated 32-byte records across all files: {dup} of {total:,}")
