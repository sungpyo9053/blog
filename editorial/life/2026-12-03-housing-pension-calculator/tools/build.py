# ko.template.html의 __DATA__ 자리에 일람표 JSON을 넣어 ../ko.html 생성
import json
d=open('data.json').read().strip()
s=open('ko.template.html').read().replace('__DATA__',d)
open('../ko.html','w').write(s)
