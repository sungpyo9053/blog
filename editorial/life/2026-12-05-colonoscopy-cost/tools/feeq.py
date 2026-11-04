# usage: feeq.py COND KEYWORD MAXPAGES -> saves evidence/nhis-fee-q-<cond>-<kw>-pN.html, prints rows
import subprocess,re,html,sys,os
cond,kw,maxp=sys.argv[1],sys.argv[2],int(sys.argv[3])
ev=os.path.join(os.path.dirname(__file__),'..','evidence')
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
for p in range(1,maxp+1):
    f=os.path.join(ev,'nhis-fee-q-%s-%s-p%d.html'%(cond,kw,p))
    subprocess.run(['curl','-s','--max-time','30','-A',UA,'-X','POST','https://www.nhis.or.kr/nhis/together/retrieveMediDentiList.do','--data-urlencode','feeKind=1','--data-urlencode','searchCondition='+cond,'--data-urlencode','searchKeyword='+kw,'--data-urlencode','pageIndex=%d'%p,'-o',f],timeout=40)
    t=open(f,encoding='utf-8').read()
    tb=re.search(r'<tbody>(.*?)</tbody>',t,re.S)
    if p==1:
        m=re.search(r'총 게시글\s*<[^>]*>?\s*([\d,]+)',t) or re.search(r'총 게시글[^\d]*([\d,]+)',t)
        print('# total',m.group(1) if m else '?')
    if not tb: break
    rows=re.findall(r'<tr>(.*?)</tr>',tb.group(1),re.S)
    if not rows: break
    for r in rows:
        c=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',x))).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',r,re.S)]
        print(' | '.join(c))
