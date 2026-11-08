# 애슐리 멤버스 FAQ API(JSON) -> 텍스트. answerCon은 HTML 엔티티가 이중으로 들어 있어 unescape 후 태그 제거.
import json, re, html, sys
for fn in sys.argv[1:]:
    d = json.load(open(fn, encoding='utf-8'))['data']
    for f in d['faqItemList']:
        a = html.unescape(html.unescape(f['answerCon']))
        a = re.sub(r'<br\s*/?>|</p>|</div>|</li>', '\n', a)
        a = re.sub(r'<[^>]+>', '', a).replace('\xa0', ' ')
        a = '\n'.join(l.strip() for l in a.splitlines() if l.strip())
        print('### [' + f['faqLCode'] + '] ' + f['counselFaqNo'] + ' Q: ' + f['questionTitle'])
        print(a)
        print()
