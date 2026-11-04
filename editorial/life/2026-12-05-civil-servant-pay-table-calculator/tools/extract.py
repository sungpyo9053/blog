# law.go.kr 별표 PDF(pdftotext) -> 봉급표 데이터, 인사혁신처 HTML 표와 셀 단위 대조. 출력: tools/tables.json
import re, json, html, os, sys
D = os.path.join(os.path.dirname(__file__), '..', 'evidence')
def law_grade(fn, ncol):
    lines = [l for l in open(os.path.join(D, fn)).read().splitlines()[1:] if re.match(r'^\s*\d{1,2}\s+\d,\d{3},\d{3}', l)]
    starts = [mm.start() for mm in re.finditer(r'\d,\d{3},\d{3}', lines[0])]  # 1호봉 행의 열 위치
    assert len(starts) == ncol
    tab = {}
    for lnh in lines:
        h = int(lnh.split()[0])
        for mm in re.finditer(r'\d,\d{3},\d{3}', lnh):
            c = min(range(ncol), key=lambda k: abs(starts[k] - mm.start()))
            tab.setdefault(c, {})[h] = int(mm.group(0).replace(',', ''))
    return [[tab[c].get(h) for h in range(1, max(tab[c]) + 1)] for c in range(ncol)]
def law_teacher(fn):
    t = {}
    for ln in open(os.path.join(D, fn)).read().splitlines()[1:]:
        for h, v in re.findall(r'(\d{1,2})\s+(\d,\d{3},\d{3})', ln): t[int(h)] = int(v.replace(',', ''))
    return [[t[h] for h in range(1, 41)]]
def mpm_tables():
    s = open(os.path.join(D, 'mpm-bizSalary-2026.html'), encoding='utf-8').read()
    out = []
    for tb in re.findall(r'(?s)<table.*?</table>', s):
        rows = []
        for r in re.findall(r'(?s)<tr.*?</tr>', tb):
            cells = [re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', c))).strip() for c in re.findall(r'(?s)<t[dh][^>]*>.*?</t[dh]>', r)]
            rows.append(cells)
        out.append(rows)
    return out
def mpm_grade(rows, ncol):
    tab = [dict() for _ in range(ncol)]
    for r in rows:
        m = re.match(r'^(\d{1,2})( 호봉)?$', r[0]) if r else None
        if not m or len(r) != ncol + 1: continue
        for c in range(ncol):
            if r[c + 1]: tab[c][int(m.group(1))] = int(r[c + 1].replace(',', ''))
    return [[t.get(h) for h in range(1, max(t) + 1)] for t in tab]
def mpm_teacher(rows):
    t = {}
    for r in rows:
        for i in range(0, len(r) - 1, 2):
            if re.match(r'^\d{1,2}$', r[i]) and r[i + 1]: t[int(r[i])] = int(r[i + 1].replace(',', ''))
    return [[t[h] for h in range(1, 41)]]
M = mpm_tables()
law = {'g': law_grade('law-bosu-byl3.txt', 9), 'a': law_grade('law-bosu-byl4.txt', 9),
       'p': law_grade('law-bosu-byl10.txt', 10), 't': law_teacher('law-bosu-byl11.txt')}
mpm = {'g': mpm_grade(M[0], 9), 'a': mpm_grade(M[2], 9), 'p': mpm_grade(M[6], 10), 't': mpm_teacher(M[7])}
n = 0
for k in law:
    assert law[k] == mpm[k], k
    for col in law[k]:
        assert None not in col, k
        assert all(a < b for a, b in zip(col, col[1:])), k  # 호봉이 오를수록 증가
        n += len(col)
print('law.go.kr 별표 == 인사혁신처 2026 봉급표, 셀', n, '개 일치')
print({k: [len(c) for c in v] for k, v in law.items()})
json.dump(law, open(os.path.join(os.path.dirname(__file__), 'tables.json'), 'w'), separators=(',', ':'))
