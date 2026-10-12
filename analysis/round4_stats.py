"""Round-4 statistics (Sections V-C and VII-D of the manuscript).

1. Power of the between-key F test by simulation under the actual design (ten keys with their
   observed sample sizes, geometric counts with key means m + delta_j, delta_j ~ N(0, sigma_b^2)):
   rejection probability at the mean-square-ratio sensitivity thresholds reported earlier, and the
   between-key standard deviation that gives 80% power.
2. Likelihood-ratio test of a constant hazard with the common hazard fitted to the same truncated
   (right-censored at the last inspected index) likelihood as the free hazards, referred to chi-square
   with (number of inspected hazards - 1) degrees of freedom, and its p-value calibrated by parametric
   simulation of geometric samples of the same size under the same >=100-at-risk inspection rule.
3. Pearson chi-square goodness of fit with the same parametric calibration.

Seeds are fixed (numpy default_rng(2024) for power, default_rng(4042) for calibration).
"""
import sys, glob
import numpy as np, pandas as pd
from scipy import stats

ROOT = sys.argv[1]; OUT = sys.argv[2]
NPOW = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
NCAL = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
MIN_AT_RISK = 100


def load():
    esp = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
    data = {44: [pd.DataFrame(dict(K=esp.K, key=esp.key_id))], 65: [], 87: []}
    for st in (44, 65, 87):
        for u in (1, 2):
            d = pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
            data[st].append(pd.DataFrame(dict(K=d.K, key=d.key)))
    return {st: pd.concat(v, ignore_index=True) for st, v in data.items()}


def f_stat(K, key_idx, nkeys):
    """One-way ANOVA F for unbalanced groups (same estimator as heterogeneity.py)."""
    n = np.bincount(key_idx, minlength=nkeys).astype(float)
    s = np.bincount(key_idx, weights=K, minlength=nkeys); s2 = np.bincount(key_idx, weights=K * K, minlength=nkeys)
    mean_j = s / n; grand = s.sum() / n.sum()
    msb = (n * (mean_j - grand) ** 2).sum() / (nkeys - 1)
    ssw = (s2 - n * mean_j ** 2).sum(); msw = ssw / (n.sum() - nkeys)
    return msb / msw


def power(rng, m, n_j, sigma_b, nsim, fcrit):
    nkeys = len(n_j); key_idx = np.repeat(np.arange(nkeys), n_j); N = key_idx.size
    rej = 0
    for _ in range(nsim):
        mu_j = m + rng.normal(0, sigma_b, nkeys)
        mu_j = np.maximum(mu_j, 1.0001)
        p_j = 1 / mu_j                      # geometric success probability per key
        K = rng.geometric(p_j[key_idx]).astype(float)
        rej += f_stat(K, key_idx, nkeys) > fcrit
    return rej / nsim


def lrt(K):
    """G with the common hazard fitted to the inspected risk sets; returns G, df, p, h0_trunc, kmax."""
    kmax = int(K.max()); r = []; e = []
    for k in range(1, kmax + 1):
        at = int((K >= k).sum())
        if at < MIN_AT_RISK:
            break
        r.append(at); e.append(int((K == k).sum()))
    r = np.array(r, float); e = np.array(e, float); h0 = e.sum() / r.sum(); h = e / r
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = np.where(e > 0, e * np.log(h / h0), 0.0)
        t2 = np.where(r - e > 0, (r - e) * np.log((1 - h) / (1 - h0)), 0.0)
    G = 2 * (t1 + t2).sum(); df = len(r) - 1
    return G, df, 1 - stats.chi2.cdf(G, df), h0, len(r)


def chi2_gof(K, m):
    h0 = 1 / m; obs = np.bincount(K.astype(int))[1:]; kk = np.arange(1, len(obs) + 1)
    exp = len(K) * (1 - h0) ** (kk - 1) * h0
    o = []; ex = []; ao = 0; ae = 0
    for oo, ee in zip(obs, exp):
        ao += oo; ae += ee
        if ae >= 5:
            o.append(ao); ex.append(ae); ao = 0; ae = 0
    o[-1] += ao; ex[-1] += ae; o = np.array(o, float); ex = np.array(ex) * o.sum() / sum(ex)
    c = ((o - ex) ** 2 / ex).sum(); df = len(o) - 2
    return c, df, 1 - stats.chi2.cdf(c, df)


rng_p = np.random.default_rng(2024); rng_c = np.random.default_rng(4042)
rows = []
for st, d in load().items():
    K = d.K.values.astype(float); N = len(K); m = K.mean()
    keys, key_idx = np.unique(d.key.values, return_inverse=True); nkeys = len(keys); n_j = np.bincount(key_idx)
    F_obs = f_stat(K, key_idx, nkeys); fcrit = stats.f.ppf(0.95, nkeys - 1, N - nkeys)
    msw = ((np.bincount(key_idx, weights=K * K) - n_j * (np.bincount(key_idx, weights=K) / n_j) ** 2).sum()) / (N - nkeys)
    n0 = (N - (n_j ** 2).sum() / N) / (nkeys - 1)
    sd_thr = np.sqrt((fcrit - 1) * msw / n0)        # mean-square-ratio sensitivity threshold
    pow_thr = power(rng_p, m, n_j, sd_thr, NPOW, fcrit)
    # bisection for 80% power
    lo, hi = sd_thr, 3 * sd_thr
    for _ in range(9):
        mid = (lo + hi) / 2
        if power(rng_p, m, n_j, mid, NPOW // 2, fcrit) < 0.8:
            lo = mid
        else:
            hi = mid
    sd_80 = (lo + hi) / 2; pow_80 = power(rng_p, m, n_j, sd_80, NPOW, fcrit)
    # hazard LRT, refitted, and parametric calibration
    G, df, pG, h0t, nh = lrt(K); C, dfc, pC = chi2_gof(K, m)
    Gs = np.empty(NCAL); Cs = np.empty(NCAL)
    for s in range(NCAL):
        Ks = rng_c.geometric(1 / m, N).astype(float)
        Gs[s] = lrt(Ks)[0]; Cs[s] = chi2_gof(Ks, Ks.mean())[0]
    rows.append(dict(set=st, N=N, mean=m, keys=nkeys, F_obs=F_obs, F_crit=fcrit, sd_threshold=sd_thr, sd_threshold_pct=100 * sd_thr / m,
                     power_at_threshold=pow_thr, sd_80_power=sd_80, sd_80_pct=100 * sd_80 / m, power_check_at_sd80=pow_80,
                     G=G, df=df, p_chi2=pG, p_sim=float((Gs >= G).mean()), h0_truncated=h0t, h0_full=1 / m, hazards_inspected=nh,
                     chi2=C, df_chi2=dfc, p_chi2_gof=pC, p_sim_gof=float((Cs >= C).mean())))
    print(f"set {st}: F={F_obs:.3f} crit={fcrit:.3f}; threshold sd={sd_thr:.4f} ({100*sd_thr/m:.2f}%) power={pow_thr:.3f}; "
          f"sd for 80% power={sd_80:.4f} ({100*sd_80/m:.2f}%) check={pow_80:.3f}; "
          f"LRT G={G:.2f} df={df} p={pG:.3f} p_sim={rows[-1]['p_sim']:.3f} h0_trunc={h0t:.5f} h0_full={1/m:.5f}; "
          f"chi2={C:.2f} df={dfc} p={pC:.3f} p_sim={rows[-1]['p_sim_gof']:.3f}")
pd.DataFrame(rows).to_csv(OUT + "/round4_stats.csv", index=False)
