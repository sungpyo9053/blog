# xlsx(HF 월지급금 일람표 2026.6.1) -> JS 데이터 한 줄. 열: B,D=우대1·2억 월, F..AB 홀수=1~12억 월, G..AC=인출한도
import subprocess,sys,json
cols=['B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC']
def sheet(n):
    out=subprocess.run(['python3','xlsx_dump.py','../evidence/hf-monthly-table-20260601.xlsx',str(n)],capture_output=True,text=True).stdout
    rows={}
    for line in out.splitlines():
        parts=dict(p.split('=',1)[0].split(':')[1:2]+[p.split('=',1)[1]] for p in [] ) if False else {}
        for p in line.split(' '):
            if '=' in p and ':' in p:
                k,v=p.split('=',1); parts[k.split(':')[1]]=v
        a=parts.get('A','')
        if a.isdigit() and 55<=int(a)<=90:
            rows[int(a)]=[int(parts[c]) for c in cols]
    assert sorted(rows)==list(range(55,91)),sorted(rows)
    m=[[r[4+2*i] for i in range(12)] for a,r in sorted(rows.items())]
    w=[[r[5+2*i] for i in range(12)] for a,r in sorted(rows.items())]
    u=[[r[0],r[2]] for a,r in sorted(rows.items())]
    return {'m':m,'w':w,'u':u}
print(json.dumps({'house':sheet(2),'officetel':sheet(4)},separators=(',',':')))
