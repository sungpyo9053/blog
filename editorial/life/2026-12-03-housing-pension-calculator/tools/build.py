# ko.template.html의 __DATA__ 자리에 일람표 JSON을 넣어 ../ko.html 생성
import json
d=open('data.json').read().strip()
s=open('ko.template.html').read().replace('__DATA__',d)
import sys; sys.path.insert(0, __import__('os').path.abspath(__file__).rsplit('/editorial/', 1)[0])  # repo root
from scripts.audit_content_repetition import template_flags  # refuse to write old template (pipeline-review C4)
if template_flags(s): raise SystemExit('template flags, not written: ' + ' '.join(template_flags(s)))
open('../ko.html','w').write(s)
