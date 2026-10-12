"""Regenerate the analytical figures for the revised deadline manuscript from the public dataset."""
import math, glob, sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import nnls

DATA = sys.argv[1]; OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"     # validated categorical slots
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 7.5, "axes.labelsize": 7.5, "axes.titlesize": 8,
    "legend.fontsize": 6.8, "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "axes.linewidth": 0.6, "lines.linewidth": 1.1,
    "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK, "text.color": INK})
COL, DBL = 3.45, 7.1

def arch(name):
    return pd.read_csv(f"{DATA}/measurements/archived/{name}.csv")

def sel(df, lvl):
    d = df[(df.algorithm == "ML-DSA") & (df.operation == "sign") & (df.security_level == lvl)]
    return d.sort_values("run_number").time_us.to_numpy(float) / 1000

def modes(t, bw):
    cut = np.percentile(t, 80); x = t[t <= cut]
    edges = np.arange(x.min() - bw, cut + 2 * bw, bw); cnt, _ = np.histogram(x, edges); ctr = (edges[:-1] + edges[1:]) / 2
    sm = np.concatenate([[0], gaussian_filter1d(cnt.astype(float), 1.2), [0]]); ctr = np.concatenate([[ctr[0] - bw], ctr, [ctr[-1] + bw]])
    thr = max(1.0, 0.003 * sm.max()); peaks = [i for i in range(1, len(sm) - 1) if sm[i] > sm[i - 1] and sm[i] >= sm[i + 1] and sm[i] > thr]
    kept = []
    for i in sorted(peaks, key=lambda i: -sm[i]):
        if all(abs(ctr[i] - ctr[j]) >= 1.0 for j in kept): kept.append(i)
    return [ctr[i] for i in sorted(kept)[:4]]

# ---------------------------------------------------------------- Fig: latency comb (RP2040 deep)
def fig_comb():
    t = sel(arch("rp2040_deep"), 44); m = modes(t, 0.05)
    b01, b12, b23 = (m[0] + m[1]) / 2, (m[1] + m[2]) / 2, (m[2] + m[3]) / 2
    C0 = t[t < b01]; C1_ = t[(t >= b01) & (t < b12)]; C2_ = np.sort(t[(t >= b12) & (t < b23)])
    B = C0.mean(); Rz = C1_.mean() - B
    gaps = np.diff(C2_); cand = [(g, i) for i, g in enumerate(gaps) if i + 1 >= 10 and g > 0.05 * Rz]; g, i = max(cand)
    main, upper = C2_[:i + 1], C2_[i + 1:]; Rl = main.mean() - B
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(DBL, 2.25), gridspec_kw={"width_ratios": [1.6, 1]})
    edges = np.arange(78, 206, 0.15); ax.hist(t[(t >= 78) & (t < 206)], edges, color=C1, lw=0)
    ax.set_yscale("log"); ax.set_ylim(0.7, 6000); ax.set_xlim(78, 206)
    ax.set_xlabel("Signing latency (ms)"); ax.set_ylabel("Signatures per 0.15 ms bin")
    for x, lab, y, ha in ((B, r"$B$", 3200, "left"), (B + Rz, r"$B+R_z$", 3200, "right"), (B + Rl, r"$B+R_{late}$", 900, "left"), (B + 2 * Rz, r"$B+2R_z$", 3200, "center")):
        ax.annotate(lab, (x + (0.6 if ha == "left" else -0.6 if ha == "right" else 0), y), ha=ha, va="bottom", fontsize=7, color=INK)
        ax.axvline(x, color=MUTED, lw=0.5, ls=":")
    ax.set_title("(a) First modes of the 10,000-signature trace", loc="left")
    edges2 = np.arange(114.5, 122.2, 0.05); bx.hist(C2_, edges2, color=C1, lw=0)
    bx.set_yscale("log"); bx.set_ylim(0.7, 600); bx.set_xlim(114.5, 122.2)
    bx.set_xlabel("Signing latency (ms)"); bx.set_ylabel("Signatures per 0.05 ms bin")
    bx.annotate(f"single $w_0$ rejections,\n{len(main)} signatures", (main.max() + 0.25, 120), fontsize=6.8, color=INK)
    bx.annotate(f"{len(upper)} hint-path\nobservations", (upper.min() - 0.15, 8), ha="right", fontsize=6.8, color=INK)
    bx.annotate("", xy=(upper.min(), 2.2), xytext=(main.max(), 2.2), arrowprops=dict(arrowstyle="<->", lw=0.6, color=MUTED))
    bx.text((main.max() + upper.min()) / 2, 2.6, f"{upper.min() - main.max():.3f} ms gap", ha="center", fontsize=6.5, color=MUTED)
    bx.set_title("(b) Late-rejection band, enlarged", loc="left")
    fig.tight_layout(w_pad=1.6); fig.savefig(f"{OUT}/fig_latency_comb.pdf"); plt.close(fig)
    print("comb:", round(B, 3), round(Rz, 3), round(Rl, 3), len(main), len(upper), round(main.max(), 3), round(upper.min(), 3))

# ---------------------------------------------------------------- Fig: prediction from counters
def load_controlled():
    out = []
    esp = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{DATA}/measurements/signing/esp32/block_*.csv"))], ignore_index=True)
    esp = esp.rename(columns={"block": "boot_block", "key_id": "key", "elapsed_us": "sign_us", "reject_z": "n_z", "reject_w0": "n_w0", "reject_ct0": "n_ct0", "reject_hint": "n_hint"})
    out.append(("ESP32\n44", esp))
    for b in (1, 2):
        for s in (44, 65, 87):
            out.append((f"RP{b}\n{s}", pd.read_csv(f"{DATA}/measurements/signing/rp2040/rp2040_{b}_set{s}.csv")))
    order = ["ESP32\n44", "RP1\n44", "RP2\n44", "RP1\n65", "RP2\n65", "RP1\n87", "RP2\n87"]
    d = dict(out); return [(k, d[k]) for k in order]

def fits(d):
    cal = (d.key <= 7) & (d.boot_block <= 2); uk = (d.key > 7) & (d.boot_block <= 2); ub = (d.key <= 7) & (d.boot_block > 2); both = (d.key > 7) & (d.boot_block > 2)
    t = d.sign_us.to_numpy(float) / 1000
    X1 = np.column_stack([np.ones(len(d)), d.K - 1]); X2 = np.column_stack([np.ones(len(d)), d.n_z, d.n_w0 + d.n_ct0 + d.n_hint])
    XS = np.column_stack([np.ones(len(d)), d.n_z, d.n_w0] + ([d.n_hint] if d.n_hint.sum() > 0 else []))
    res = {}
    for name, X in (("shared", X1), ("two", X2), ("separate", XS)):
        c, _ = nnls(X[cal], t[cal]); res[name] = {k: float(np.mean(np.abs(X[m] @ c - t[m]))) for k, m in (("keys", uk), ("boots", ub), ("both", both))}
    return res, t.mean()

def fig_validation():
    cfg = load_controlled(); names = [k for k, _ in cfg]; R = [fits(d) for _, d in cfg]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(DBL, 2.2))
    x = np.arange(len(cfg))
    for model, col, mk, lab in (("shared", C2, "o", "Shared rejection cost"), ("two", C1, "s", "Early and late costs"), ("separate", C3, "^", "Separate observed exits")):
        ax.plot(x, [r[0][model]["both"] for r in R], marker=mk, ms=4, color=col, label=lab)
    ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels([n.replace("\n", "-") for n in names]); ax.set_ylabel("Held-out MAE (ms)")
    ax.legend(frameon=False, loc="center right"); ax.grid(axis="y", lw=0.3, color="0.88"); ax.set_title("(a) Three cost models, unseen keys and boots", loc="left")
    for part, col, mk, lab in (("keys", C1, "o", "Unseen keys"), ("boots", C2, "s", "Unseen boots"), ("both", C3, "^", "Both unseen")):
        bx.plot(x, [100 * r[0]["two"][part] / r[1] for r in R], marker=mk, ms=4, color=col, label=lab)
    bx.set_xticks(x); bx.set_xticklabels([n.replace("\n", "-") for n in names]); bx.set_ylabel("Two-cost MAE (% of mean signing time)")
    bx.set_ylim(0, 0.4); bx.legend(frameon=False); bx.grid(axis="y", lw=0.3, color="0.88"); bx.set_title("(b) Early/late model, by holdout", loc="left")
    fig.tight_layout(w_pad=1.6); fig.savefig(f"{OUT}/fig_counter_validation.pdf"); plt.close(fig)
    print("validation both-holdout two-cost MAE:", [round(r[0]["two"]["both"], 3) for r in R])

# ---------------------------------------------------------------- Fig: iteration survival
def fig_survival():
    cfg = dict(load_controlled())
    dev = {44: pd.concat([cfg["ESP32\n44"].K, cfg["RP1\n44"].K, cfg["RP2\n44"].K]).to_numpy(), 65: pd.concat([cfg["RP1\n65"].K, cfg["RP2\n65"].K]).to_numpy(), 87: pd.concat([cfg["RP1\n87"].K, cfg["RP2\n87"].K]).to_numpy()}
    x86 = arch("x86_iterations")
    fig, axes = plt.subplots(1, 3, figsize=(DBL, 2.35), sharey=True)
    for ax, (s, ref) in zip(axes, ((44, 4.36), (65, 5.14), (87, 3.91))):
        K = dev[s]; n = np.arange(0, K.max() + 1); surv = [(K > k).mean() for k in n]
        ax.step(n, surv, where="post", color=C1, lw=1.3, label="Devices (pooled)")
        h = x86[x86.parameter_set == s].iterations.to_numpy(); nh = np.arange(0, h.max() + 1)
        ax.step(nh, [(h > k).mean() for k in nh], where="post", color=C2, lw=0.9, label="x86 host")
        nn = np.arange(0, 56); ax.plot(nn, (1 - 1 / ref) ** nn, color=INK, lw=0.8, ls="--", label="Per-set geometric reference")
        ax.plot(nn, (1 - 1 / 5.14) ** nn, color=MUTED, lw=0.7, ls=":", label="Common reference, mean 5.14")
        ax.set_yscale("log"); ax.set_ylim(5e-6, 1.3); ax.set_xlim(0, 55); ax.set_xlabel("Iteration budget $n$")
        ax.set_title(f"ML-DSA-{s} (reference mean {ref})", loc="left", fontsize=7.5)
        ax.grid(lw=0.3, color="0.9")
    axes[0].set_ylabel(r"Fraction of signatures with $K>n$")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=6.8, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(w_pad=1.2, rect=(0, 0.06, 1, 1)); fig.savefig(f"{OUT}/fig_iteration_survival.pdf"); plt.close(fig)

# ---------------------------------------------------------------- Fig: deadline vs iteration budget
def fig_deadline():
    rows = {"ESP32 deep": (21.522, 10.556, C2), "RP2040 deep": (80.284, 41.564, C1)}   # B+ and C+ in ms, reproduced from the archived traces
    fig, ax = plt.subplots(figsize=(COL, 2.1)); n = np.arange(1, 111)
    for name, (Bp, Cp, col) in rows.items():
        ax.plot(n, (Bp + (n - 1) * Cp) / 1000, color=col, label=name)
        ax.annotate(name, (78, (Bp + 77 * Cp) / 1000 - 0.12), fontsize=6.8, ha="left", va="top", color=INK)
    for nb, lab in ((32, r"$10^{-3}$"), (64, r"$10^{-6}$"), (96, r"$10^{-9}$")):
        ax.axvline(nb, color=MUTED, lw=0.5, ls=":"); ax.text(nb, 5.35, f"{lab}\n$n$={nb}", ha="center", va="top", fontsize=6.3, color=MUTED)
    ax.set_xlim(0, 110); ax.set_ylim(0, 5.4); ax.set_xlabel("Iteration budget $n$"); ax.set_ylabel("$D(n)$ (s)")
    ax.grid(axis="y", lw=0.3, color="0.9")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_deadline_budget.pdf"); plt.close(fig)

fig_comb(); fig_validation(); fig_survival(); fig_deadline()
print("done")
