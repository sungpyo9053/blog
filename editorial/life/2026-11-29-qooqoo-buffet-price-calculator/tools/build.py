# tools/ko.src.html + evidence/stores-parsed.json -> ko.html
import json,os
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S=json.load(open(D+'/evidence/stores-parsed.json',encoding='utf-8'))
S.sort(key=lambda s:(s['region'],s['name']))
rows=[[s['region'],s['name'],1 if s['gold'] else 0,s['L'],s['D'],s['W'],s['KL'],s['KD'],s['KW'],s['P'],s['note']] for s in S]
data=json.dumps(rows,ensure_ascii=False,separators=(',',':'))
assert '&' not in data and '<' not in data
src=open(D+'/tools/ko.src.html',encoding='utf-8').read()
open(D+'/ko.html','w',encoding='utf-8').write(src.replace('__DATA__',data))
print(len(rows),'stores')
