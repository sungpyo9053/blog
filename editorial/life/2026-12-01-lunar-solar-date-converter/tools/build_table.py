# KASI /life/lunc 음력 매월 1일 조회 결과 → 연속성 검사 → 계산기 내장 표 문자열
import json, sys, datetime as dt
rows = [json.loads(l) for l in open('evidence/kasi-lunc-month-starts-1950-2050.jsonl')]
months = []  # (ly, lm, leap, solar date, len)
empty = []
for r in rows:
    if not r['r']: empty.append(r['q']); continue
    for x in sorted(r['r'], key=lambda x: x['LUNC_LEAP_MM'] == '윤'):
        months.append((int(x['LUNC_YYYY']), int(x['LUNC_MM']), x['LUNC_LEAP_MM'] == '윤',
                       dt.date(int(x['SOLC_YYYY']), int(x['SOLC_MM']), int(x['SOLC_DD'])), int(x['LUNC_EN_DD'])))
print('empty queries:', empty, file=sys.stderr)
bad = 0
for a, b in zip(months, months[1:]):
    if a[3] + dt.timedelta(a[4]) != b[3]: bad += 1; print('GAP', a, b, file=sys.stderr)
print('months', len(months), 'continuity breaks', bad, 'first', months[0], 'last', months[-1], file=sys.stderr)
leaps = [(m[0], m[1]) for m in months if m[2]]
print('leap months', len(leaps), leaps, file=sys.stderr)
# 인코딩: 해마다 [윤달 월(0=없음, 1-9, a-c)] + 월 순서대로 1(30일)/0(29일)
by = {}
for m in months: by.setdefault(m[0], []).append(m)
enc = []
for y in sorted(by):
    lp = [m[1] for m in by[y] if m[2]]
    enc.append(('0123456789abc'[lp[0]] if lp else '0') + ''.join('1' if m[4] == 30 else '0' for m in by[y]))
print(months[0][3].isoformat())
print(','.join(enc))
