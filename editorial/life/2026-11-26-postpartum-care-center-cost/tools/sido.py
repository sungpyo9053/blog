# evidence/mohw-2025h2-prices.csv -> 시도별 일반실·특실 평균/중앙값 (만원). 사용: python3 -I tools/sido.py evidence/mohw-2025h2-prices.csv
import csv,sys,statistics as st
N={'경기도':'경기','충청북도':'충북','전라남도':'전남','경상북도':'경북','경상남도':'경남'}
rows=list(csv.reader(open(sys.argv[1])))[2:]
f=lambda x: float(x) if x.replace('.','',1).isdigit() else None
def s(rs,i):
  a=[f(r[i]) for r in rs if f(r[i])]; return (len(a),round(st.mean(a)),round(st.median(a))) if a else (0,'-','-')
order=[]
for r in rows:
  k=N.get(r[1],r[1])
  if k not in order: order.append(k)
print('전체',len(rows),s(rows,4),s(rows,5))
print('지자체',s([r for r in rows if r[3]=='지자체'],4),'민간',s([r for r in rows if r[3]=='민간'],4))
for k in order:
  rs=[r for r in rows if N.get(r[1],r[1])==k]; print(k,len(rs),s(rs,4),s(rs,5))
