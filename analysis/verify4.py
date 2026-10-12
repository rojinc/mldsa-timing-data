import pandas as pd, numpy as np, sys
D=sys.argv[1]+"/measurements/telemetry/"
rr=pd.read_csv(D+"rp2040_report.csv")
print("flags:",sorted(rr['flags'].unique()), "n rows",len(rr))
rr['sign_ms']=(rr.ready-rr.start)/1000
done=rr[rr.ready>0]
print(done.groupby(['board','mode','period_ms']).sign_ms.agg(['mean','count']).round(1))
# per run: late (ready-release>period), dropped?, censored
for (b,m,p,rep),g in rr.groupby(['board','mode','period_ms','replicate']):
    late=((g.ready-g.release)>p*1000)&(g.ready>0)
    unfinished=(g.ready==0).sum()
    print(b,m,p,rep,"rows",len(g),"late",late.sum(),"unfinished",unfinished,"flags",g['flags'].value_counts().to_dict())
print("share RP2040 signing >250ms:", (done[done.period_ms==250].sign_ms>250).mean().round(3), " >100:",(done[done.period_ms==100].sign_ms>100).mean().round(3))
