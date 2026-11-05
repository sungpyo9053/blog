# 2027 공휴일: 관공서공휴일규정 제2조·제3조①1호·2호·③을 적용해 대체공휴일을 계산하고 월력요항 표와 대조 (제3조①3호 평일 중복은 2027년에 없음: base 날짜가 서로 겹치지 않음)
from datetime import date, timedelta as td
D=lambda m,d: date(2027,m,d)
# 음력 공휴일 양력 날짜는 2027년 월력요항(우주항공청) 값: 설날 2/7, 부처님 오신 날 5/13, 추석 9/15
base={  # date: (이름, 조항 호)
 D(1,1):('1월 1일',3), D(2,6):('설날 연휴',4), D(2,7):('설날',4), D(2,8):('설날 연휴',4),
 D(3,1):('3·1절',2), D(5,1):('노동절',6), D(5,5):('어린이날',7), D(5,13):('부처님 오신 날',5),
 D(6,6):('현충일',8), D(7,17):('제헌절',2), D(8,15):('광복절',2), D(9,14):('추석 연휴',9),
 D(9,15):('추석',9), D(9,16):('추석 연휴',9), D(10,3):('개천절',2), D(10,9):('한글날',2), D(12,25):('기독탄신일',10)}
def is_hol(d,subs): return d.weekday()==6 or d in base or d in subs
subs={}
for d,(n,ho) in sorted(base.items()):
    wd=d.weekday()  # 5=토 6=일
    need = (ho in (2,5,6,7,10) and wd>=5) or (ho in (4,9) and wd==6)
    if not need: continue
    x=d+td(1)
    while is_hol(x,subs) or x.weekday()==5: x+=td(1)  # 제3조①·③: 첫 비공휴일, 토요일이면 다음 비공휴일
    subs[x]='대체공휴일('+n.replace(' 연휴','')+')'
official_subs={D(2,9),D(5,3),D(7,19),D(8,16),D(10,4),D(10,11),D(12,27)}
assert set(subs)==official_subs, sorted(subs)
allh={**{d:v[0] for d,v in base.items()},**subs}
days=[D(1,1)+td(i) for i in range(365)]
sun=sum(d.weekday()==6 for d in days); sat=sum(d.weekday()==5 for d in days)
red=set(allh)|{d for d in days if d.weekday()==6}
wk=[d for d in allh if d.weekday()<5]
print('공휴일 지정일(일요일 제외 목록):',len(allh),'일요일:',sun,'토요일:',sat)
print('관공서 공휴일(적색일) 실질:',len(red),' 일요일과 겹침:',sorted(str(d) for d in allh if d.weekday()==6))
print('토요일과 겹침:',sorted(str(d) for d in allh if d.weekday()==5))
print('평일 공휴일:',len(wk),sorted(str(d) for d in wk))
off={d for d in days if d.weekday()>=5}|set(allh)
print('주5일 근무자 총 휴일:',len(off),' 근무일:',365-len(off))
assert len(red)==72 and len(off)==119
# 연차 붙이기: k일 연속 근무일을 쉬면 앞뒤 휴일까지 이어지는 연휴 길이 (2027년 안에서만)
work=[d for d in days if d not in off]
plans=[]
for k in (1,2,3,4,5):
    for i in range(len(work)-k+1):
        if (work[i+k-1]-work[i]).days >= 7*k: continue
        s=work[i-1]+td(1) if i>0 else D(1,1)
        e=work[i+k]-td(1) if i+k<len(work) else D(12,31)
        n=(e-s).days+1
        plans.append((k,n,s,e,[str(w) for w in work[i:i+k]]))
for k in (1,2,3,4,5):
    best=sorted([p for p in plans if p[0]==k],key=lambda p:(-p[1],p[2]))[:3]
    for p in best: print('연차',k,'일 ->',p[1],'일 연휴',p[2],'~',p[3],'휴가일',p[4])
