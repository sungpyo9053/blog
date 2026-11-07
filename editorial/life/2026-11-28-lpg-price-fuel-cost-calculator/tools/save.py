import sys,re
src,url,dst=sys.argv[1:4]
s=open(src,encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<(script|style|option)[^>]*>.*?</\1>','',s)
s=re.sub(r'\n\s*\n+','\n',s)
open(dst,'w',encoding='utf-8').write('<!-- '+url+' -->\n'+s)
