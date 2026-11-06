# 화장시설별 '대인 일반 관내/관외' 요금만 추출
import json,re,sys
BAD=('수급','유공','보훈','기타','군','자녀','인접','준관내','장애','다자녀','무연고','희생','배우자','저소득','차상위','한부모','감면','복지')
def pick(fees,where):
    c=[]
    for x in fees:
        t=x['rentcontent'] or ''
        if x['tier1Nm']!='시신' or x['sale']!='Y': continue
        if '대인' not in t or where not in t: continue
        if any(b in t for b in BAD): continue
        other='관외' if where=='관내' else '관내'
        if other in t: continue
        c.append(x['facilityamt'])
    return c
rows=[]
for f in json.load(open(sys.argv[1])):
    a,b=pick(f['fees'],'관내'),pick(f['fees'],'관외')
    rows.append([f['name'],f['sido'],f['updated'],a[0] if len(a)==1 else a,b[0] if len(b)==1 else b])
for r in rows: print(r)
