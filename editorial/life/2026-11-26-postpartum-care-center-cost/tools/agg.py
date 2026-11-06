import csv,sys,statistics as st
rows=[r for r in csv.reader(open(sys.argv[1])) if r and r[0].strip().isdigit()]
def num(x):
  try: return float(x)
  except: return None
print('total',len(rows))
by={}
for r in rows:
  by.setdefault(r[1].strip(),[]).append(r)
def s(lst):
  g=[num(r[7]) for r in lst if num(r[7])]; t=[num(r[8]) for r in lst if num(r[8])]
  f=lambda a:(len(a),round(st.mean(a)) if a else '-',round(st.median(a)) if a else '-',min(a) if a else '-',max(a) if a else '-')
  return f(g),f(t)
print('ALL',s(rows))
pub=[r for r in rows if '지자체' in r[3]]; pri=[r for r in rows if '지자체' not in r[3]]
print('PUB',s(pub)); print('PRI',s(pri))
for k in by: print(k,s(by[k]))
print('운영주체',set(r[3] for r in rows))
for r in pub: print('공공',r[1],r[2],r[4],r[7],r[8])
