# prices.txt(매장별 가격정보 발췌) -> stores.json
import re,sys,json
txt=open(sys.argv[1],encoding='utf-8').read()
blocks=re.split(r'^@@',txt,flags=re.M)[1:]
def nums(s):
    s=s.replace('36.900','36,900')  # 구로점 표기 '36.900원'
    s=re.sub(r'(\d{1,3})\s*,\s*(\d{3})',r'\1,\2',s)
    return [int(x.replace(',','')) for x in re.findall(r'\d{1,3},\d{3}',s)]
out=[]
for b in blocks:
    lines=b.split('\n'); head=lines[0]; body=[l.strip() for l in lines[1:] if l.strip()]
    wid=int(head.split()[0]); m=re.search(r'\[(.+?)\]\s*(.+)$',head); region,name=m.group(1),m.group(2).strip()
    if '나트랑' in name: continue
    gold='골드' in name
    name=re.sub(r'골드\s*☆\s*','',name); name=re.sub(r',.*$','',name).strip()
    ad=next((l for l in body if '평일런치' in l and '주말' in l),'')
    kd=next((l for l in body if ('초등학생' in l) and re.search(r'\d,\d{3}',l) and '→' not in l),'')
    pr=next((l for l in body if '미취학' in l and '→' not in l),'')
    a=nums(ad); k=nums(kd); p=nums(pr)
    s={'id':wid,'region':region,'name':name,'gold':gold,'note':''}
    s['L'],s['D'],s['W']=(a+[None]*3)[:3] if len(a)==3 else (None,None,None)
    if len(k)==3: s['KL'],s['KD'],s['KW']=k
    elif len(k)==2:
        first=kd.split('/')[0]
        if '런치' in first and '디너' not in first: s['KL'],s['KD'],s['KW']=k[0],k[1],k[1]
        else: s['KL'],s['KD'],s['KW']=k[0],k[0],k[1]
    else: s['KL']=s['KD']=s['KW']=None
    s['P']=p[0] if len(p)==1 else None
    if name=='대전점': s['KD']=s['KL']  # '(평일 런치/디너) 15,900원' 표기
    if name=='원주혁신점': s['note']='평일런치 11:30~15:30, 평일저녁 17:00~21:30으로 적혀 있음'
    if name=='광복점': s['KL']=s['KD']=s['KW']=None; s['note']='초등학생 요금이 두 칸 모두 평일로 적혀 있음'
    if name=='파주운정점': s['KD']=None; s['note']='평일디너 초등학생 요금이 17,00원으로 적혀 있음'
    if name=='구로점': s['note']='주말 성인 요금이 36.900원으로 적혀 있음'
    if s['L'] is None: s['note']='가격정보 칸에 금액이 비어 있음'
    s['src']=ad+' | '+kd+' | '+pr
    out.append(s)
json.dump(out,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False,indent=0)
for s in out: print(s['id'],s['region'],s['name'],'G' if s['gold'] else '-',s['L'],s['D'],s['W'],s['KL'],s['KD'],s['KW'],s['P'],s['note'])
print(len(out))
