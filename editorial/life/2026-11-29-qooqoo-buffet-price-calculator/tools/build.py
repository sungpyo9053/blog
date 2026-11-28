# tools/ko.src.html + evidence/stores-parsed.json -> ko.html
import json,os
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S=json.load(open(D+'/evidence/stores-parsed.json',encoding='utf-8'))
S.sort(key=lambda s:(s['region'],s['name']))
rows=[[s['region'],s['name'],1 if s['gold'] else 0,s['L'],s['D'],s['W'],s['KL'],s['KD'],s['KW'],s['P'],s['note']] for s in S]
data=json.dumps(rows,ensure_ascii=False,separators=(',',':'))
assert '&' not in data and '<' not in data
src=open(D+'/tools/ko.src.html',encoding='utf-8').read()
import sys; sys.path.insert(0, __import__('os').path.abspath(__file__).rsplit('/editorial/', 1)[0])  # repo root
from scripts.audit_content_repetition import template_flags  # refuse to write old template (pipeline-review C4)
if template_flags(src.replace('__DATA__',data)): raise SystemExit('template flags, not written: ' + ' '.join(template_flags(src.replace('__DATA__',data))))
open(D+'/ko.html','w',encoding='utf-8').write(src.replace('__DATA__',data))
print(len(rows),'stores')
