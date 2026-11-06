import re,sys,html
src,url,out,start,end=sys.argv[1:6]
t=open(src,encoding='utf-8',errors='ignore').read()
t=re.sub(r'(?s)<(script|style)[^>]*>.*?</\1>','',t);t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(t);t=re.sub(r'\s+',' ',t)
i=t.find(start);j=t.find(end,i+1) if end else len(t)
open(out,'w').write(url+'\n(curl '+'2026-11-06, script/style 제거 후 본문 발췌)\n'+t[i:j if j>0 else len(t)].strip()+'\n')
