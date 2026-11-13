# 이월드 API JSON에서 인용 구간만 텍스트로 뽑는다: python3 -I excerpt.py discount|faq|time FILE
import json,re,html,sys
def strip(v):
    s=html.unescape(re.sub(r'<br\s*/?>|</li>|</p>','\n',v or '')); s=re.sub(r'<[^>]+>','',s); return re.sub(r'\n\s*\n+','\n',s).strip()
kind,f=sys.argv[1],sys.argv[2]; d=json.load(open(f))
if kind=='discount':
    for x in d:
        if x['isEnabled'] and (x['endTime'] or '9999')>='2026-11-13':
            print('## id',x['id'],x['type'],'|',x['name'],'|',x['startTime'],'~',x['endTime'],'|',x['target'],'|',x['contents'],'|',x['condition'])
            print('images:',re.findall(r'src="([^"]+)"',x['information'] or ''))
            print(strip(x['information'])); print(strip(x['notice'])); print()
elif kind=='faq':
    for x in d:
        t=json.dumps(x,ensure_ascii=False)
        if any(k in t for k in ['요금','할인','주차','36개월','장애','생일','티켓','단체','연간회원 유효']):
            print('Q:',x.get('question'),'\nA:',strip(x.get('answer')),'\n')
elif kind=='time':
    for x in d:
        if x['date']>='2026-11-01': print(x['date'][:10],x['startTime'],x['endTime'],x.get('memo') or '')
