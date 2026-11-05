# mvnohub-products.html(2026-11-06 curl)에서 요금제 카드를 뽑아 데이터 구간별 '할인 이후 월요금' 통계를 낸다
import re,sys,html,statistics as st
t=open(sys.argv[1],encoding='utf-8').read()
t=re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>','',t)
s=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
items=sorted(set(re.findall(r'(SKT|KT|LGU\+) (\S+(?: \S+)?) (LTE|5G)?\s*(?:이벤트상품 )?(?:허브전용 )?월 ([\d,]+) 원 (?:([\d,]+)\s*\d+% 할인 )?(?:(\d+)개월 이후 ([\d,]+) 원/월 )?데이터 (\S+) 통화 (\S+) 문자 (\S+)',s)))
n=lambda x:int(x.replace(',',''))
print('요금제 카드(중복 제외):',len(items),'/ 할인기간 있는 것:',sum(1 for i in items if i[5]))
for b,lo,hi in [('5GB 이하',0,5),('6~10GB',5.01,10),('11~20GB',10.01,20),('21~99GB',20.01,99),('100GB 이상',99.01,1e9)]:
  r=[i for i in items if lo<=float(re.match(r'[\d.]+',i[7]).group())<=hi]
  a=[n(i[6]) if i[6] else n(i[3]) for i in r]
  print(b,'개수',len(r),'할인 이후 월요금 최저',min(a),'중앙값',st.median(a),'최고',max(a),'할인개월',sorted(set(int(i[5]) for i in r if i[5])))
c={}
for i in items: c[i[8]]=c.get(i[8],0)+1
print('통화 제공량 분포',c)
