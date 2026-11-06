# ko.src.html + evidence/kobus-fares-summary.json.txt -> ko.html (요금표·계산기 데이터를 조회값에서 그대로 생성)
import json, os, re
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = open(os.path.join(B, 'evidence', 'kobus-fares-summary.json.txt'), encoding='utf-8').read().split('\n', 2)[2]
d = json.loads(raw)
ORDER = ['고속', '우등', '프리미엄', '심야고속', '심야우등', '심야프리미엄']
routes = {}
for k, v in d.items():
    m = re.match(r'(\d+) (.+?)->(.+?) \((\d+시간 \d+분) 소요예상 \(([\d.]+) Km\)\)', k)
    name = m.group(2) + '→' + m.group(3)
    r = routes.setdefault(name, {'dep': m.group(2), 'time': m.group(4), 'km': m.group(5), 'cls': {}})
    for c, fares in v.items():
        a, ch, t, _ = map(int, list(fares.keys())[0].split('/'))
        r['cls'][c] = [a, ch, t]
data = [[n, r['time'], [[c] + r['cls'][c] for c in ORDER if c in r['cls']]] for n, r in routes.items()]
js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
assert '&' not in js and '<' not in js
def table(dep):
    cols = ['고속', '우등', '프리미엄', '심야우등', '심야프리미엄']
    h = '<table><thead><tr><th>도착지(소요)</th>' + ''.join('<th>%s</th>' % c for c in cols) + '</tr></thead><tbody>\n'
    for n, r in routes.items():
        if r['dep'] != dep: continue
        h += '<tr><td>%s(%s)</td>' % (n.split('→')[1], r['time'].replace(' 0분', '').replace('시간 ', '시간').replace('분', '분')) + ''.join(
            '<td>%s</td>' % (format(r['cls'][c][0], ',') if c in r['cls'] else '-') for c in cols) + '</tr>\n'
    return h + '</tbody></table>'
src = open(os.path.join(B, 'tools', 'ko.src.html'), encoding='utf-8').read()
src = src.replace('__DATA__', js).replace('__T010__', table('서울경부')).replace('__T021__', table('센트럴시티(서울)')).replace('__T032__', table('동서울'))
assert not re.search(r'__(DATA|T0\d\d)__', src)
open(os.path.join(B, 'ko.html'), 'w', encoding='utf-8').write(src)
print('routes', len(data))
