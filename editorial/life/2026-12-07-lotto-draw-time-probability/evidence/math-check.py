# 로또 6/45 경우의 수·확률 검산 (python3 evidence/math-check.py)
from math import comb, log, ceil
from fractions import Fraction as F
C = comb(45, 6)
assert C == 8145060
tiers = {
 '1등 (6개 일치)': comb(6,6),
 '2등 (5개+보너스)': comb(6,5)*1,
 '3등 (5개, 보너스 아님)': comb(6,5)*38,
 '4등 (4개)': comb(6,4)*comb(39,2),
 '5등 (3개)': comb(6,3)*comb(39,3),
}
exp = [1, 6, 228, 11115, 182780]
assert list(tiers.values()) == exp
# 전수 검산: 당첨번호 1~6, 보너스 7로 고정하고 모든 8,145,060 조합을 센다
from itertools import combinations
win = set(range(1,7)); bonus = 7
cnt = [0]*6
for c in combinations(range(1,46), 6):
    m = len(win.intersection(c))
    if m == 6: cnt[1] += 1
    elif m == 5: cnt[2 if bonus in c else 3] += 1
    elif m == 4: cnt[4] += 1
    elif m == 3: cnt[5] += 1
assert cnt[1:] == exp, cnt
print('C(45,6) =', C, '| 전수 검산 일치:', cnt[1:])
tot = 0
for (k, v) in tiers.items():
    tot += v
    print(f'{k}: {v:,} / {C:,} = 1/{C/v:,.1f} = {v/C*100:.7f}%')
print(f'1~5등 합계 {tot:,} -> 1/{C/tot:.2f} = {tot/C*100:.4f}%, 꽝 {100-tot/C*100:.4f}%')
# 4·5등 고정 당첨금 기댓값 (복권위원회 2026.8.11 보도자료: 4등 5만 원, 5등 5천 원)
e4 = F(50000*11115, C); e5 = F(5000*182780, C)
print(f'4등 기댓값 {float(e4):.2f}원, 5등 {float(e5):.2f}원, 합 {float(e4+e5):.2f}원/게임')
def atleast(p, n): return 1-(1-p)**n
p = {k: v/C for k, v in tiers.items()}
for n in [1,5,10,50,100,1000,10000]:
    print(n, '게임:', ' | '.join(f'{k.split()[0]} {atleast(q,n)*100:.6f}%' for k, q in p.items()), f'| 서로 다른 조합 1등 {n/C*100:.6f}%')
for m, y in [(1,10),(5,10),(5,30),(5,50),(10,50)]:
    d = 52*y; q = m/C
    print(f'매주 {m}게임 {y}년({d}회): 1등 {atleast(q,d)*100:.4f}%')
for m in [1,5,10]:
    q = m/C
    print(f'매주 {m}게임 1등 50%: {ceil(log(0.5)/log(1-q))/52:,.0f}년, 평균 대기 {C/m/52:,.0f}년')
# 1등 기대 당첨자 수 (복권위원회 2022.6.14 보도설명: 1억장 x 1/814만 = 12.3)
print('1억 게임 균등 선택 시 1등 기대', round(1e8/C, 2), '명; 1057회 11,252만 게임 2등 기대', round(112520000*6/C, 1), '명')
