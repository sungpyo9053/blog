# usage: fc.py id -> evidence/moel-counsel-id.html, prints Q/A text
import re,html,sys,subprocess,os
i=sys.argv[1]; ev=os.path.join(os.path.dirname(__file__),'..','evidence'); h=os.path.join(ev,'moel-counsel-%s.html'%i)
subprocess.run(['curl','-sL','-A','Mozilla/5.0','-o',h,'https://www.moel.go.kr/minwon/fastcounsel/fastcounselView.do?inetDcssMngId='+i],check=True)
s=open(h).read(); s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s)
t=html.unescape(re.sub(r'<[^>]+>',' ',s)); t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
a=t.find(' 질의 \n'); b=t.find(' 이전글',a)
print(t[a:b if b>0 else a+5000][:6000])
