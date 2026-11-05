# 연금복권720+ 확률·당첨금 검산 (python3 -I math-check.py)
from itertools import product
from fractions import Fraction as F
SPACE = 5 * 10**6  # 1조~5조 x 000000~999999
assert SPACE == 5_000_000
# 당첨 번호를 3조 123456, 보너스를 각조 654321로 두고 끝자리부터 연속 일치 수를 센다.
win_g, win = 3, '123456'
def tail(a, b):
    k = 0
    for x, y in zip(reversed(a), reversed(b)):
        if x != y: break
        k += 1
    return k
# 6자리 공간 10^6을 전부 돌려 '끝에서 k자리 연속 일치' 개수를 센다 (조 무관)
cnt = [0] * 7
for i in range(10**6):
    cnt[tail('%06d' % i, win)] += 1
print('끝자리 연속 일치 개수(6자리 10^6 전수):', cnt)
tiers = {}
tiers['1등'] = 1                      # 조 + 6자리
tiers['2등'] = 4 * cnt[6]             # 6자리 일치, 조 다름
for t, k in zip(['3등','4등','5등','6등','7등'], [5,4,3,2,1]):
    tiers[t] = 5 * cnt[k]
tiers['보너스'] = 5 * 1               # 보너스 6자리 일치, 각조
official = {'1등':1,'2등':4,'3등':45,'4등':450,'5등':4500,'6등':45000,'7등':450000,'보너스':5}
print('등위별 번호 개수(5,000,000개 중):', tiers)
assert tiers == official, 'bokgwon 2020 표의 판매점 당첨자 수와 불일치'
prize = {'1등':7_000_000*12*20,'2등':1_000_000*12*10,'3등':1_000_000,'4등':100_000,'5등':50_000,'6등':5_000,'7등':1_000,'보너스':1_000_000*12*10}
total_ev = F(0)
for t in official:
    p = F(official[t], SPACE)
    ev = p * prize[t]
    total_ev += ev
    print(f'{t}: 확률 {p} = {float(p):.10f} (1/{float(1/p):,.1f}), 명목 당첨금 {prize[t]:,}원, 1장당 기댓값 {float(ev):.2f}원')
p17 = F(sum(official[t] for t in ['1등','2등','3등','4등','5등','6등','7등']), SPACE)
print('1~7등 합계 확률:', p17); assert p17 == F(1,10)
print('1장(1,000원)당 명목 기댓값 합계:', float(total_ev), '원 =', float(total_ev/1000*100), '%'); assert total_ev == 750
# 세트(같은 6자리 x 1~5조 5장 가정): 6자리가 맞으면 1등 1장 + 2등 4장
print('세트 5장 1등 포함 확률:', F(cnt[6], 10**6), ' 서로 다른 번호 5장 1등 확률:', F(5, SPACE))
assert F(cnt[6], 10**6) == F(5, SPACE)
print('세트 5장 7등 이상(끝자리 일치) 확률:', F(1,10), ' 독립 5장 1번 이상:', 1-(1-F(1,10))**5, '=', float(1-(1-F(1,10))**5))
print('1등 낱장 명목 합계:', 7_000_000*240, ' 세트 추가분:', 4_000_000*120, ' 세트 합계:', 7_000_000*240 + 4_000_000*120)
assert 4_000_000 == 4 * 1_000_000  # 세트 추가분 = 2등 월 100만 원 x 4매와 같은 금액
# 세금(lottery-prize-tax 글·국세청): 매 지급분에 20% + 지방 10%, 10원 미만 절사, 3억 이하 구간
def net(a):
    it = a * 20 // 100 // 10 * 10
    lt = it // 10 // 10 * 10
    return a - it - lt, it, lt
for a in (7_000_000, 4_000_000, 1_000_000):
    print('월', f'{a:,}', '-> 세후', [f'{x:,}' for x in net(a)])
assert net(7_000_000)[0] == 5_460_000 and net(1_000_000)[0] == 780_000
# 현재가치: 연 r을 월 i=(1+r)^(1/12)-1, 매월 말 지급(첫 지급 1개월 뒤)
def pv(a, n, r):
    i = (1 + r) ** (1/12) - 1
    return a * n if i == 0 else a * (1 - (1 + i) ** -n) / i
for r in (0.0, 0.02, 0.03, 0.05):
    print(f'할인율 {r*100:.0f}%: 1등 낱장 세전 PV {pv(7e6,240,r):,.0f}원, 세후 PV {pv(5.46e6,240,r):,.0f}원, 세트 세전 PV {pv(7e6,240,r)+pv(4e6,120,r):,.0f}원, 2등 세전 PV {pv(1e6,120,r):,.0f}원')
# N장 독립 1번 이상
for n in (1, 5, 10, 100):
    row = [f'{t} {(1-(1-official[t]/SPACE)**n)*100:.6g}%' for t in ['1등','2등','보너스','3등','5등','7등']]
    print(f'N={n}:', ', '.join(row))
# 매주 M장 X년 (52회/년, 서로 다른 번호)
import math
for m, y in ((1,10),(5,10),(5,50)):
    q = m / SPACE; d = 52*y
    print(f'매주 {m}장 {y}년: 1등 1번 이상 {(-math.expm1(d*math.log1p(-q)))*100:.4f}%, 50% 기간 {math.log(0.5)/math.log1p(-q)/52:,.0f}년')
print('ALL CHECKS PASSED')
