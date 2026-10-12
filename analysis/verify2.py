import pandas as pd, numpy as np, glob, sys
from scipy.optimize import nnls
D=sys.argv[1]
def load_rp(u,st):
    return pd.read_csv(f"{D}/measurements/signing/rp2040/rp2040_{u}_set{st}.csv")
esp=pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{D}/measurements/signing/esp32/block_*.csv"))])
# partition for esp: key 0-7 & block 0-2 calibration; keys>=8 & block<=2 unseen keys; keys<8 & block>=3 unseen boots; else both
def part(k,b):
    if k<8 and b<3: return 'cal'
    if k>=8 and b<3: return 'keys'
    if k<8 and b>=3: return 'boots'
    return 'both'
print("== Table III controlled")
rows=[]
cfgs=[('ESP32',44,None)]+[(f'RP2040 unit {u}',st,u) for st in (44,65,87) for u in (1,2)]
for name,st,u in cfgs:
    if u is None:
        df=esp.copy(); t=df.elapsed_us/1000; K=df.K; nz=df.reject_z; nw=df.reject_w0; nh=df.reject_hint; nc=df.reject_ct0
        p=np.array([part(k,b) for k,b in zip(df.key_id,df.block)])
    else:
        df=load_rp(u,st); t=df.sign_us/1000; K=df.K; nz=df.n_z; nw=df.n_w0; nh=df.n_hint; nc=df.n_ct0
        p=np.array([part(k,b) for k,b in zip(df.key,df.boot_block)])
    t=np.asarray(t,float); nl=np.asarray(nw+nh+nc,float); nz=np.asarray(nz,float)
    cal=p=='cal'
    X2=np.c_[np.ones(cal.sum()),nz[cal],nl[cal]]
    c2,_=nnls(X2,t[cal])
    X1=np.c_[np.ones(cal.sum()),(nz+nl)[cal]]; c1,_=nnls(X1,t[cal])
    maes=[]; maes1=[]
    for h in ('keys','boots','both'):
        m=p==h
        pred=c2[0]+c2[1]*nz[m]+c2[2]*nl[m]; maes.append(np.abs(pred-t[m]).mean())
        pred1=c1[0]+c1[1]*(nz+nl)[m]; maes1.append(np.abs(pred1-t[m]).mean())
    print(f"{name:14s} {st} N={len(t)} mean={t.mean():.3f} meanK={K.mean():.3f} K1={100*(K==1).mean():.2f} ratio={c2[2]/c2[1]:.4f} MAE={min(maes):.3f}-{max(maes):.3f} pct={100*min(maes)/t.mean():.3f}-{100*max(maes)/t.mean():.2f} red={100*(1-max(np.array(maes)/np.array(maes1))):.1f}-{100*(1-min(np.array(maes)/np.array(maes1))):.1f}")
print("== Table IV iteration stats (pooled devices)")
allK={44:[],65:[],87:[]}
for name,st,u in cfgs:
    df=esp if u is None else load_rp(u,st)
    key=df.key_id if u is None else df.key
    allK[st].append(pd.DataFrame({'K':df.K.values,'key':key.values}))
from scipy import stats
for st in (44,65,87):
    d=pd.concat(allK[st]); km=d.groupby('key').K.mean(); m=d.K.mean()
    se=km.std(ddof=1)/np.sqrt(len(km)); tcrit=stats.t.ppf(0.975,len(km)-1)
    print(st,len(d),f"{m:.3f} ({m-tcrit*se:.3f}, {m+tcrit*se:.3f}) P1={ (d.K==1).mean():.3f} max={d.K.max()} perkey={km.min():.2f}-{km.max():.2f}")
x=pd.read_csv(f"{D}/measurements/archived/x86_iterations.csv"); print(x.columns.tolist()[:8]); 
