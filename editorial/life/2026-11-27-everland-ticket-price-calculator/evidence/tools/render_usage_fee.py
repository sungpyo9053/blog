# usage: python3 -I render_usage_fee.py promo.js msg.json component_name
# Vue 렌더 함수에서 문자열 리터럴과 $t(KEY)를 등장 순서대로 뽑아 한국어 메시지로 치환
import re, sys, json
js = open(sys.argv[1], encoding='utf8').read()
msg = {m['messageResourcesId']: m['multiLanguageContent'] for m in json.load(open(sys.argv[2], encoding='utf8')) if m['langId'] == 'ko'}
j = js.find('name:"%s"' % sys.argv[3])
i = js.rfind('function(t,l,n){n.r(l)', 0, j)
body = js[i:j]
out = []
for m in re.finditer(r'\$t\("([A-Z0-9_]+)"\)|"((?:[^"\\]|\\.)*)"', body):
    if m.group(1):
        out.append(msg.get(m.group(1), '[' + m.group(1) + ']'))
    else:
        s = m.group(2)
        if re.search(r'[가-힣0-9]', s) and not re.fullmatch(r'[\w\-\. ]*', s) or re.search('[가-힣]', s):
            out.append(s)
print('\n'.join(out))
