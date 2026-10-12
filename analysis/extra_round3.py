"""Round-3 additions: two-stage replay intervals, boot F-tests, hazard LRT, counts per K, detectable effect sizes."""
import sys, os, glob, numpy as np, pandas as pd
from scipy import stats
ROOT=sys.argv[1]; OUT=sys.argv[2]
sys.argv=['x',ROOT,OUT]
HERE=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE,'queue_replay.py')).read().split('if __name__')[0])

# ---- admission-rule check under alternative rules (Section IX-D): admission evaluated
#      `delay_us` after the nominal release, and the pending slot freed at `ready`
#      instead of at `available`
def race_variant(runs, delay_us=0, free_at="available"):
    rows=[]
    for r in runs:
        if r["board"]=="esp32" or r["period_ms"]!=100: continue
        ok=r["start"]!=SENT; rel=r["release"]; n=r["n"]
        # a request's slot is held until the server dequeues it, i.e. just after the
        # previous executed request's `available` (or its `ready`, in the variant)
        prev_end=(r["ready"]+(r["chk"] if free_at=="available" else 0))[ok]
        free=np.zeros(n,dtype=np.int64); free[ok]=np.r_[0,prev_end[:-1]]
        unfinished=r["flags"]==4
        bad=0
        for i in range(n):
            t=rel[i]+delay_us
            m=np.ones(n,bool); m[i]=False
            pend=int((m&ok&(rel<t)&(free>t)).sum())+int((m&unfinished&(rel<t)).sum())
            admitted=r["flags"][i]!=1
            if (admitted and pend>=QCAP) or ((not admitted) and pend<QCAP): bad+=1
        rows.append(dict(run=r["run"],board=r["board"],mode=r["mode"],replicate=r["replicate"],delay_us=delay_us,free_at=free_at,inconsistent=bad))
    return pd.DataFrame(rows)
_runs=rp_runs(); vrows=[]
for d in (0,50,100,200,500,1000): vrows.append(race_variant(_runs,d,"available"))
vrows.append(race_variant(_runs,0,"ready"))
V=pd.concat(vrows); V.to_csv(OUT+'/replay_race_variants.csv',index=False)
print("admission-rule mismatches (sum over 12 runs) by variant:"); print(V.groupby(['free_at','delay_us']).inconsistent.sum().to_string())

# ---- two-stage intervals: predict each 100/250 ms run from each other replicate separately
rng=np.random.default_rng(11); runs=rp_runs()+esp_runs(); pool=pools(runs); rows=[]
for r in runs:
    if r["period_ms"]==1000: continue
    P=r["period_ms"]*1000; n=r["n"]
    others=[(k,v) for k,v in pool.items() if k[0]==r["board"] and k[1]==r["mode"] and k[2]!=r["replicate"]]
    allp={'late':[], 'dropped':[]}; per_pool={}
    for k,v in others:
        preds=[]
        for s in range(150):
            idx=rng.integers(0,len(v),n); sim=replay(P,n,v[idx,0],v[idx,1],v[idx,2]); preds.append(outcomes(sim,P))
        pr=pd.DataFrame(preds); per_pool[k[2]]=(pr.late.median(),pr.dropped.median())
        allp['late']+=pr.late.tolist(); allp['dropped']+=pr.dropped.tolist()
    row=dict(board=r["board"],mode=r["mode"],period_ms=r["period_ms"],replicate=r["replicate"],obs_late=r["obs"]["late"],obs_dropped=r["obs"]["dropped"])
    for k in ('late','dropped'):
        lo,hi=np.percentile(allp[k],[2.5,97.5]); row[f'two_{k}_lo']=lo; row[f'two_{k}_hi']=hi; row[f'two_{k}_med']=np.median(allp[k])
    row['pool_medians_late']=str({kk:round(v[0]) for kk,v in per_pool.items()}); row['pool_medians_dropped']=str({kk:round(v[1]) for kk,v in per_pool.items()})
    rows.append(row)
T=pd.DataFrame(rows); T.to_csv(OUT+'/replay_two_stage.csv',index=False)
rp=T[T.board!='esp32']
for k,per in (('dropped',100),('late',100),('late',250)):
    sub=rp[rp.period_ms==per]; inside=((sub[f'obs_{k}']>=sub[f'two_{k}_lo'])&(sub[f'obs_{k}']<=sub[f'two_{k}_hi'])).sum()
    print(f"two-stage {k}@{per}: inside {inside}/{len(sub)}")
print(T[['board','mode','period_ms','replicate','obs_late','two_late_lo','two_late_hi','obs_dropped','two_dropped_lo','two_dropped_hi','pool_medians_late']].round(0).to_string())

# ---- boot F-tests, hazard LRT, ACF beyond 2SE, detectable effect size, counts per K
esp=pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{ROOT}/measurements/signing/esp32/block_*.csv"))])
data={44:[pd.DataFrame(dict(K=esp.K,key=esp.key_id,boot=esp.block,board='esp32'))],65:[],87:[]}
for st in (44,65,87):
    for u in (1,2):
        d=pd.read_csv(f"{ROOT}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv"); data[st].append(pd.DataFrame(dict(K=d.K,key=d.key,boot=d.boot_block,board=f'rp2040_{u}')))
REF={44:4.36,65:5.14,87:3.91}
for st,lst in data.items():
    d=pd.concat(lst,ignore_index=True); K=d.K.values; m=K.mean()
    # boot effect: one-way ANOVA on boot block within each board, and pooled board-boot cells
    groups=[g.K.values for _,g in d.groupby(['board','boot'])]
    F,p=stats.f_oneway(*groups)
    # key-level detectable sd: critical F(9, N-10) at 0.05; n0 ~ n per key
    km=d.groupby('key').K.agg(['mean','size','var']); n0=km['size'].mean(); msw=(km['var']*(km['size']-1)).sum()/(len(d)-len(km))
    Fcrit=stats.f.ppf(0.95,len(km)-1,len(d)-len(km)); sd_det=np.sqrt((Fcrit-1)*msw/n0)
    # hazard LRT: constant hazard h0=1/m vs free h_k over k with >=100 at risk
    kmax=int(K.max()); ll_free=0; ll_null=0; dfk=0; h0=1/m
    for k in range(1,kmax+1):
        at=int((K>=k).sum()); ev=int((K==k).sum())
        if at<100: break
        hk=ev/at; dfk+=1
        if 0<hk<1: ll_free+=ev*np.log(hk)+(at-ev)*np.log(1-hk)
        ll_null+=ev*np.log(h0)+(at-ev)*np.log(1-h0)
    G=2*(ll_free-ll_null); pG=1-stats.chi2.cdf(G,dfk-1)
    # chi-square GOF of K distribution vs geometric(1/m) with pooled tail
    obs=np.bincount(K)[1:]; probs=[(1-h0)**(k-1)*h0 for k in range(1,len(obs)+1)]; exp=np.array(probs)*len(K)
    # pool bins with expected<5
    o=[];e=[];acc_o=0;acc_e=0
    for oo,ee in zip(obs,exp):
        acc_o+=oo; acc_e+=ee
        if acc_e>=5: o.append(acc_o); e.append(acc_e); acc_o=0; acc_e=0
    o[-1]+=acc_o; e[-1]+=acc_e; e=np.array(e)*sum(o)/sum(e)
    chi2=((np.array(o)-e)**2/e).sum(); dfc=len(o)-2; pc=1-stats.chi2.cdf(chi2,dfc)
    print(f"set {st}: boot F={F:.2f} p={p:.2f} (cells={len(groups)}); detectable between-key sd (F>crit {Fcrit:.2f}) = {sd_det:.3f} ({100*sd_det/m:.1f}% of mean); hazard LRT G={G:.1f} df={dfk-1} p={pG:.2f}; chi2 GOF={chi2:.1f} df={dfc} p={pc:.2f}")
a=pd.read_csv(OUT+'/acf.csv'); vals=a[['acf1','acf2','acf3','acf5','acf10']].values.ravel(); print("ACF values:",len(vals)," beyond 2SE:",(np.abs(vals)>2*0.0045).sum()," beyond 2.5SE:",(np.abs(vals)>2.5*0.0045).sum())
byk=pd.read_csv(OUT+'/envelope_by_K.csv')
for (c,s),g in byk.groupby(['config','set']):
    print(c,s,"holdout calls: K>=20:",int(g[g.K>=20].n.sum()),"K>=30:",int(g[g.K>=30].n.sum()),"K>=40:",int(g[g.K>=40].n.sum()),"maxK",int(g.K.max()))
