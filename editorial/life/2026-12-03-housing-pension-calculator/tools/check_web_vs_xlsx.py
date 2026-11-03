# HF 월지급금 예시 웹 표(2026.03.01. 기준)와 일람표 xlsx(2026.6.1 적용) 대조
import json,re
d=json.load(open('data.json'))
t=open('../evidence/hf-sub03_01_01_02.txt').read()
blocks=t.split('(종신지급방식, 정액형)')[1:4]
for name,b in zip(['house','senior','officetel'],blocks):
    rows=re.findall(r'\|\s*(\d\d)세\s*((?:\n\s*\|\s*[\d,]+\s*){12})',b)
    ok=bad=0
    for age,vals in rows:
        v=[int(x.replace(',','')) for x in re.findall(r'[\d,]+',vals)]
        if name in d:
            if d[name]['m'][int(age)-55]==v: ok+=1
            else: bad+=1;print(name,age,v)
    print(name,'rows',len(rows),'ok',ok,'bad',bad,'(senior: xlsx에 없음)' if name=='senior' else '')
