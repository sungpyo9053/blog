# 서울스카이 benefit/view JSON -> 텍스트 (표 행은 " | "로 연결)
import json, sys, html, re
def clean(s):
    s = html.unescape(html.unescape(s or ''))
    s = re.sub(r'</t[dh]>\s*', ' | ', s)
    s = re.sub(r'<br\s*/?>|</(tr|li|p|div)>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    lines = [re.sub(r'[ \t\xa0]+', ' ', l).strip(' |') for l in s.split('\n')]
    return '\n'.join(l for l in lines if l)
for f in sys.argv[1:]:
    d = json.load(open(f))['data']
    print('=== bnftSeq', d['bnftSeq'], d['bnftDvNm'], '|', d['titl'], '|', d['prgrsBgnDtFmt'], '~', d['prgrsEndDtFmt'])
    print('URL: https://seoulsky.lotteworld.com/api/price/benefit/view?storeCd=HC01805&langCd=HC01701&bnftSeq=' + d['bnftSeq'])
    print(clean(d.get('cntn'))); print('[유의]', clean(d.get('cutnCntn'))); print()
