# usage: feed.py CODE... -> evidence/nhis-fee-detail-CODE.html + key fields
import subprocess,re,html,sys,os
ev=os.path.join(os.path.dirname(__file__),'..','evidence')
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
for code in sys.argv[1:]:
    f=os.path.join(ev,'nhis-fee-detail-%s.html'%code)
    subprocess.run(['curl','-s','--max-time','30','-A',UA,'-X','POST','https://www.nhis.or.kr/nhis/together/retrieveMediDenti.do','--data-urlencode','actnTypeCd=1','--data-urlencode','stndMechCd='+code,'--data-urlencode','adptFrDt=20260101','-o',f],timeout=40)
    t=open(f,encoding='utf-8').read()
    t=re.sub(r'<(script|style).*?</\1>','',t,flags=re.S)
    s=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
    i=s.find('코드')
    m=re.search(r'(기본정보.*?)(목록|진료받으실)',s)
    print('==',code, (m.group(1) if m else s[:100])[:900])
