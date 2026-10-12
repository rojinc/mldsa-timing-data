import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUTD=sys.argv[1]; FIG=sys.argv[2]
C1,C2,C3="#2a78d6","#eb6834","#1baf7a"; INK,MUTED="#0b0b0b","#52514e"
plt.rcParams.update({"font.family":"sans-serif","font.size":7.5,"axes.labelsize":7.5,"axes.titlesize":8,"legend.fontsize":6.5,"xtick.labelsize":6.8,"ytick.labelsize":6.8,"axes.linewidth":0.6,"lines.linewidth":1.1,"pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False,"savefig.bbox":"tight","savefig.pad_inches":0.02,"axes.edgecolor":MUTED,"xtick.color":MUTED,"ytick.color":MUTED,"axes.labelcolor":INK,"text.color":INK})
h=pd.read_csv(OUTD+"/hazard.csv"); kr=pd.read_csv(OUTD+"/per_key.csv")
fig,axes=plt.subplots(1,3,figsize=(7.1,2.0),sharey=False)
for ax,st in zip(axes,(44,65,87)):
    g=h[(h.set==st)&(h.at_risk>=100)]
    ax.errorbar(g.k,g.hazard,yerr=[g.hazard-g.lo,g.hi-g.hazard],fmt="o",ms=2.6,color=C1,ecolor=C1,elinewidth=0.7,capsize=0,label="pooled devices, 95% Wilson")
    ax.axhline(g.ref.iloc[0],color=C2,lw=1.0,label="corrected reference $1/m$ (4.36, 5.14, 3.91)")
    # per-key hazard estimate 1/mean as horizontal ticks at k=1 region
    kk=kr[kr.set==st]
    ax.plot(np.full(len(kk),0.3),1/kk["mean"],"_",color=C3,ms=6,mew=1.0,label="per-key $1/\\bar K$ (ten keys)")
    ax.set_xlim(-0.5,g.k.max()+1); ax.set_xlabel("iteration index $k$")
    ax.set_title(f"ML-DSA-{st}: $h(k)=\\Pr[K=k\\mid K\\geq k]$",loc="left")
    ax.grid(axis="y",lw=0.3,color="0.88")
axes[0].set_ylabel("discrete hazard")
h0,l0=axes[1].get_legend_handles_labels(); fig.legend(h0,l0,frameon=False,loc="lower center",ncol=3,bbox_to_anchor=(0.5,-0.08))
fig.tight_layout(w_pad=1.0); fig.savefig(FIG+"/fig_hazard.pdf"); print("ok")
