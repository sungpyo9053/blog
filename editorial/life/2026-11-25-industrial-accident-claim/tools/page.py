# usage: page.py url name  -> evidence/name.html + .txt (main text)
import re,html,sys,subprocess,os
url,name=sys.argv[1:3]
ev=os.path.join(os.path.dirname(__file__),'..','evidence')
h=os.path.join(ev,name+'.html')
subprocess.run(['curl','-sL','-A','Mozilla/5.0','-o',h,url],check=True)
s=open(h,errors='replace').read()
s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s)
t=re.sub(r'<[^>]+>',' ',s); t=html.unescape(t); t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(os.path.join(ev,name+'.txt'),'w').write(t); print(name,len(t))
