# 열차운임(2026.9.1.).xls -> 수서·동탄·평택지제 출발 구간 운임 요약 + 계산기용 JSON
# usage: python -I extract_fares.py fare.xls out.txt
import sys, json, xlrd
b = xlrd.open_workbook(sys.argv[1])
lines_js = {'gb': 14, 'gp': 16, 'hn': 18, 'jr': 20, 'gj': 21, 'ph': 23}  # 11, 12, 13, 15, 16, 17번 시트
extra = [15, 17, 19, 22]  # 11-1, 12-1, 14, 16-1 (서대구·서대전 경유) — 표 참고용
cmp_sheets = [0, 2, 5, 7, 9, 12]  # 서울 출발 비교 (1, 2, 4, 5, 6, 9번 시트)
def rows(s):
    for r in range(s.nrows):
        v = [c.value for c in s.row(r)]
        if not isinstance(v[3], float): continue
        if s.ncols > 7: yield v[1], v[2], int(v[3]), int(v[8]), int(v[9])   # 일반 | 우등 | 특실(운임·요금·계)
        else: yield v[1], v[2], int(v[3]), int(v[5]), int(v[6])
data = {}; out = []
for key, i in list(lines_js.items()) + [(None, i) for i in extra + cmp_sheets]:
    s = b.sheet_by_index(i); out.append('## sheet %d: %s' % (i, s.name))
    keep = ('수서', '동탄', '평택지제') if i not in cmp_sheets else ('서울',)
    for a, d, gen, fee, spc in rows(s):
        if a not in keep: continue
        out.append('%s-%s 일반실 %d / 특실 운임 %d + 요금 %d = %d' % (a, d, gen, gen, fee, spc))
        if key: data.setdefault(key, {}).setdefault(a, []).append([d, gen, spc])
open(sys.argv[2], 'w').write('source: https://www.srail.or.kr/cms/attach/download.do?pageId=TK0402050000&atchNo=28 (열차운임(2026.9.1.).xls, https://etk.srail.kr/cms/archive.do?pageId=TK0402050000 열차운임 및 시간표 > 열차 운임(2026.09.01~) 운임표 다운로드)\n' + '\n'.join(out) + '\n\nJSON ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
print(sum(len(o) for l in data.values() for o in l.values()))
