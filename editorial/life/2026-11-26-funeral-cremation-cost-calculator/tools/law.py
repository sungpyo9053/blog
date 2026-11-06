# usage: law.py lsiSeq outdir name -> outdir/name.txt (본문 텍스트), 시행일은 lsInfoP의 efYd에서 읽음
import re,html,sys,subprocess
seq,out,name=sys.argv[1:4]
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
g=lambda u: subprocess.run(['curl','-sSL','--max-time','30','-A',UA,u],capture_output=True,check=True).stdout.decode('utf-8','replace')
p=g('https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq='+seq)
ef=re.search(r"efYd = '(\d{8})'",p).group(1)
t=g('https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=%s&efYd=%s'%(seq,ef))
t=re.sub(r'<(script|style)[\s\S]*?</\1>','',t,flags=re.I)
t=re.sub(r'<br\s*/?>|</(p|div|li|tr)>','\n',t,flags=re.I)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(out+'/'+name+'.txt','w').write('https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=%s (efYd=%s)\n'%(seq,ef)+t)
i=t.find('[시행'); print(name,ef,len(t),t[i:i+80].replace('\n',' '))
