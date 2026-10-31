# usage: law.py lsiSeq efYd name  -> evidence/name.html + .txt
import re,html,sys,subprocess,os
seq,ef,name=sys.argv[1:4]
ev=os.path.join(os.path.dirname(__file__),'..','evidence')
h=os.path.join(ev,name+'.html')
subprocess.run(['curl','-sL','-A','Mozilla/5.0','https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=%s&efYd=%s'%(seq,ef),'-o',h],check=True)
t=re.sub(r'<[^>]+>',' ',open(h).read()); t=html.unescape(t); t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(os.path.join(ev,name+'.txt'),'w').write(t); i=t.find('[시행'); print(name,len(t),t[i:i+90])
