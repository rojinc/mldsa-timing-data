import pandas as pd, numpy as np, sys
from scipy.ndimage import gaussian_filter1d
D=sys.argv[1]+"/measurements/archived/"
def load(name,lvl):
    df=pd.read_csv(D+name+".csv"); d=df[(df.algorithm=="ML-DSA")&(df.operation=="sign")&(df.security_level==lvl)]
    return d.time_us.values/1000.0
def clusters(t,bw,frac=0.80,sigma=1.2,gap=0.05):
    lo=t[t<=np.quantile(t,frac)]
    edges=np.arange(lo.min(),lo.max()+2*bw,bw)
    h,_=np.histogram(lo,bins=edges)
    hp=np.r_[np.zeros(5),h,np.zeros(5)]
    sp=gaussian_filter1d(hp.astype(float),sigma)
    centers=(edges[:-1]+edges[1:])/2
    pk=[i for i in range(1,len(sp)-1) if sp[i]>sp[i-1] and sp[i]>=sp[i+1] and sp[i]>1 and sp[i]>0.003*sp.max()]
    peaks=[i-5 for i in pk if 0<=i-5<len(centers)]
    sel=[]
    for i in peaks:
        if all(abs(centers[i]-centers[j])>=1.0 for j in sel): sel.append(i)
        if len(sel)==4: break
    m=[centers[i] for i in sel]
    b01=(m[0]+m[1])/2; b12=(m[1]+m[2])/2; b23=(m[2]+m[3])/2
    C0=t[t<b01]; C1=t[(t>=b01)&(t<b12)]; band=np.sort(t[(t>=b12)&(t<b23)])
    B=C0.mean(); Rz=C1.mean()-B
    gaps=np.diff(band); U=np.array([]); C2=band
    cand=[i for i in range(len(gaps)) if gaps[i]>gap*Rz and i+1>=10]
    if cand:
        i=max(cand,key=lambda i:gaps[i]); C2=band[:i+1]; U=band[i+1:]
    Rl=C2.mean()-B
    return dict(m=m,C0=C0,C1=C1,C2=C2,U=U,B=B,Rz=Rz,Rl=Rl)
rows=[("ESP32 deep","esp32_deep",44,0.01),("RP2040 deep","rp2040_deep",44,0.05),
      ("RP2040 unit 1","rp2040_unit1",44,0.05),("RP2040 unit 2","rp2040_unit2",44,0.05),
      ("RP2040 unit 1","rp2040_unit1",65,0.05),("RP2040 unit 2","rp2040_unit2",65,0.05),
      ("RP2040 unit 1","rp2040_unit1",87,0.05),("RP2040 unit 2","rp2040_unit2",87,0.05)]
out=[]
for name,f,lvl,bw in rows:
    t=load(f,lvl); c=clusters(t,bw)
    Bp=c['C0'].max(); Cp=max(c['C1'].max(),c['C2'].max(),(c['U'].max() if len(c['U']) else 0))-c['C0'].min()
    def Dn(n,Bp=Bp,Cp=Cp): return (Bp+(n-1)*Cp)/1000
    # single-extreme deletions
    alts={}
    # baseline max deleted
    C0s=np.sort(c['C0']); alts['base max']=(C0s[-2]+95*Cp)/1000
    # baseline min deleted
    Cp2=max(c['C1'].max(),c['C2'].max(),(c['U'].max() if len(c['U']) else 0))-C0s[1]; alts['base min']=(Bp+95*Cp2)/1000
    # rejection max deleted
    allrej=np.sort(np.concatenate([c['C1'],c['C2'],c['U']])); Cp3=allrej[-2]-c['C0'].min(); alts['rej max']=(Bp+95*Cp3)/1000
    k=min(alts,key=alts.get)
    D96=Dn(96); D821=Dn(821)
    alt821={'base max':(C0s[-2]+820*Cp)/1000,'base min':(Bp+820*Cp2)/1000,'rej max':(Bp+820*Cp3)/1000}
    k2=min(alt821,key=alt821.get)
    print(f"{name:14s} {lvl} n0={len(c['C0'])} nz={len(c['C1'])} nl={len(c['C2'])} nu={len(c['U'])} B={c['B']:.3f} Rz={c['Rz']:.3f} Rl={c['Rl']:.3f} | B+={Bp:.3f} C+={Cp:.3f} max={t.max()/1000:.3f} D32={Dn(32):.3f} D64={Dn(64):.3f} D96={D96:.3f} D821={D821:.3f} | D96 del({k})={alts[k]:.3f} ({100*(alts[k]/D96-1):+.2f}%) | D821 del({k2})={alt821[k2]:.3f} ({100*(alt821[k2]/D821-1):+.2f}%)")
