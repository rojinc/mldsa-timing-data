import pandas as pd, numpy as np, sys
D=sys.argv[1]+"/measurements/telemetry/"
r=pd.read_csv(D+"esp32_runs.csv"); rep=pd.read_csv(D+"esp32_reports.csv"); e=pd.read_csv(D+"rp2040_end.csv"); rr=pd.read_csv(D+"rp2040_report.csv")
print("ESP32 runs:",len(r),"RP2040 runs:",len(e),"total",len(r)+len(e))
print("ESP32 acquisition misses by mode/period:")
print(r.groupby(['mode','period_ms']).acquisition_misses.agg(['min','max','count']))
print("RP2040 acquisition (late+skipped) by mode/period:")
e['miss']=e.late+e.skipped
print(e.groupby(['mode','period_ms']).agg(miss_min=('miss','min'),miss_max=('miss','max'),resp_max=('max_response_us','max'),resp_min=('max_response_us','min'),n=('miss','count')))
print("ESP32 report late counts (status codes):", rep.status.unique())
rep['sign_ms']=(rep.ready_off_us-rep.started_off_us)/1000
comp=rep[rep.status==0] if 0 in rep.status.unique() else rep
print("ESP32 completed reports mean sign ms:", rep.groupby(['mode','period_ms']).sign_ms.mean().round(2))
print("ESP32 report misses (late) per run:"); print(r[r.period_ms>0].groupby(['mode','period_ms'])[['report_rows','late','dropped','completed','censored']].sum())
# ESP32 reports late: ready_off_us > period?
rep['late']=rep.ready_off_us>rep.period_ms*1000
print(rep.groupby(['mode','period_ms','replicate']).late.sum().unstack('replicate'))
print("share of ESP32 signing >100ms at 100ms:", (rep[rep.period_ms==100].sign_ms>100).mean().round(4))
# RP2040 reports
rr['sign_ms']=(rr.ready-rr.start)/1000
print("RP2040 flags:",rr["flags"].unique())
print(rr.groupby(['board','mode','period_ms']).sign_ms.agg(['mean','count']).round(1))
rr['late']=(rr.ready-rr.release)>rr.period_ms*1000
print(rr.groupby(['board','mode','period_ms']).late.mean().round(4))
print("RP2040 share signing>250:", (rr[rr.period_ms==250].sign_ms>250).mean().round(3))
