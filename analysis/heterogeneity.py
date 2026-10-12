"""Heterogeneity and dependence of the iteration count K (Section VII-D of the manuscript).

Pooled device records per parameter set (ESP32 + both RP2040 units for set 44; both
RP2040 units for 65 and 87), with key, boot block, message and repetition index.
"""
import sys, glob, itertools
import numpy as np, pandas as pd
from scipy import stats
from math import comb

ROOT = sys.argv[1]; OUT = sys.argv[2]
EPS = (1e-3, 1e-6, 1e-9)
REF = {44: 4.36, 65: 5.14, 87: 3.91}


def budget(mean, eps):
    q = 1 - 1 / mean
    return int(np.ceil(np.log(eps) / np.log(q)))


def load():
    esp = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
    data = {44: [pd.DataFrame(dict(K=esp.K, key=esp.key_id, boot=esp.block, msg=esp.message_id, rep=esp.rand_index, board="esp32", order=esp.invocation_id))],
            65: [], 87: []}
    for st in (44, 65, 87):
        for u in (1, 2):
            d = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
            data[st].append(pd.DataFrame(dict(K=d.K, key=d.key, boot=d.boot_block, msg=d.message, rep=d.repetition, board=f"rp2040_{u}", order=d.index)))
    return {st: pd.concat(v, ignore_index=True) for st, v in data.items()}


data = load()
summary = []; hazard_rows = []; key_rows = []; loko_rows = []; acf_rows = []; boot_rows = []
for st, d in data.items():
    K = d.K.values; N = len(K); m = K.mean(); qhat = 1 - 1 / m
    # ---- discrete hazard h(k) = P(K = k | K >= k) with Wilson intervals
    kmax = int(K.max())
    for k in range(1, kmax + 1):
        at_risk = int((K >= k).sum()); ev = int((K == k).sum())
        if at_risk == 0:
            continue
        p = ev / at_risk; z = 1.959964
        den = 1 + z * z / at_risk; ctr = (p + z * z / (2 * at_risk)) / den; half = z * np.sqrt(p * (1 - p) / at_risk + z * z / (4 * at_risk * at_risk)) / den
        hazard_rows.append(dict(set=st, k=k, at_risk=at_risk, events=ev, hazard=p, lo=ctr - half, hi=ctr + half, ref=1 / REF[st], pooled=1 / m))
    # ---- per-key means, q, budgets; mixture tail
    km = d.groupby("key").K.agg(["mean", "size", "std"])
    for key, r in km.iterrows():
        key_rows.append(dict(set=st, key=int(key), n=int(r["size"]), mean=r["mean"], q=1 - 1 / r["mean"], se=r["std"] / np.sqrt(r["size"]),
                             **{f"n_{e:.0e}": budget(r["mean"], e) for e in EPS}))
    qk = 1 - 1 / km["mean"].values; w = km["size"].values / N
    mix = lambda n: float((w * qk ** n).sum())
    pooled = lambda n: qhat ** n
    # budgets under the mixture: smallest n with mix(n) <= eps
    mix_budget = {}
    for e in EPS:
        n = 1
        while mix(n) > e:
            n += 1
        mix_budget[e] = n
    # between-key variance components (one-way ANOVA): var of key means minus sampling part
    n_per = km["size"].values; grand = m
    msb = (n_per * (km["mean"].values - grand) ** 2).sum() / (len(km) - 1)
    msw = ((d.groupby("key").K.var(ddof=1) * (n_per - 1)).sum()) / (N - len(km))
    n0 = (N - (n_per ** 2).sum() / N) / (len(km) - 1)
    var_between = max(0.0, (msb - msw) / n0)
    F = msb / msw; pF = 1 - stats.f.cdf(F, len(km) - 1, N - len(km))
    # ---- leave-one-key-out means
    for key in km.index:
        sub = d[d.key != key].K
        loko_rows.append(dict(set=st, left_out=int(key), mean=sub.mean(), n=len(sub), n_1e9=budget(sub.mean(), 1e-9)))
    # ---- per boot block and per board means
    for (board, boot), g in d.groupby(["board", "boot"]):
        boot_rows.append(dict(set=st, board=board, boot=int(boot), n=len(g), mean=g.K.mean()))
    # ---- serial dependence: lag-1..5 autocorrelation of K within each board's chronological order
    for board, g in d.groupby("board"):
        x = g.sort_values("order").K.values.astype(float); x = x - x.mean(); v = (x * x).sum()
        row = dict(set=st, board=board, n=len(x), se=1 / np.sqrt(len(x)))
        for lag in (1, 2, 3, 5, 10):
            row[f"acf{lag}"] = float((x[:-lag] * x[lag:]).sum() / v)
        # runs test on K > median
        y = (g.sort_values("order").K.values > np.median(g.K.values)).astype(int)
        runs = 1 + int((y[1:] != y[:-1]).sum()); n1, n0_ = y.sum(), len(y) - y.sum()
        mu = 1 + 2 * n1 * n0_ / (n1 + n0_); sd = np.sqrt(2 * n1 * n0_ * (2 * n1 * n0_ - n1 - n0_) / ((n1 + n0_) ** 2 * (n1 + n0_ - 1)))
        row["runs_z"] = (runs - mu) / sd
        acf_rows.append(row)
    # ---- exact key-bootstrap: full support of the 99.9th percentile over all 92,378 multisets
    hist = {key: np.bincount(g.K.values, minlength=kmax + 1) for key, g in d.groupby("key")}
    keys = sorted(hist); H = np.array([hist[k] for k in keys])
    support = {}
    for combo in itertools.combinations_with_replacement(range(len(keys)), len(keys)):
        mult = np.bincount(combo, minlength=len(keys))
        h = mult @ H; n = h.sum(); rank = int(np.ceil(0.999 * n))
        p = int(np.searchsorted(np.cumsum(h), rank))
        weight = np.exp(stats.multinomial.logpmf(mult, len(keys), np.full(len(keys), 1 / len(keys))))
        support[p] = support.get(p, 0.0) + weight
    summary.append(dict(set=st, N=N, mean=m, qhat=qhat, ref=REF[st], keys=len(km), key_mean_min=km["mean"].min(), key_mean_max=km["mean"].max(),
                        key_mean_sd=km["mean"].std(ddof=1), var_between=var_between, sd_between=np.sqrt(var_between), F=F, p_F=pF,
                        **{f"pooled_n_{e:.0e}": budget(m, e) for e in EPS}, **{f"mix_n_{e:.0e}": mix_budget[e] for e in EPS},
                        mix_tail_at_pooled_1e9=mix(budget(m, 1e-9)), pooled_tail_1e9=pooled(budget(m, 1e-9)),
                        ratio_mix_pooled_96=mix(96) / pooled(96),
                        loko_min=min(r["mean"] for r in loko_rows if r["set"] == st), loko_max=max(r["mean"] for r in loko_rows if r["set"] == st),
                        p999_support={int(k): round(v, 6) for k, v in sorted(support.items())}))

pd.set_option("display.width", 250)
S = pd.DataFrame(summary); S.to_csv(OUT + "/heterogeneity_summary.csv", index=False); print(S.to_string())
pd.DataFrame(hazard_rows).to_csv(OUT + "/hazard.csv", index=False)
KR = pd.DataFrame(key_rows); KR.to_csv(OUT + "/per_key.csv", index=False); print(KR.round(4).to_string())
pd.DataFrame(loko_rows).to_csv(OUT + "/loko.csv", index=False); print(pd.DataFrame(loko_rows).round(4).to_string())
A = pd.DataFrame(acf_rows); A.to_csv(OUT + "/acf.csv", index=False); print(A.round(4).to_string())
Bt = pd.DataFrame(boot_rows); Bt.to_csv(OUT + "/per_boot.csv", index=False); print(Bt.round(3).to_string())
