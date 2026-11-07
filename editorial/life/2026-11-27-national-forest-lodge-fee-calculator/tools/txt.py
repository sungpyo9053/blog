import re,sys,html
for f in sys.argv[1:]:
    t=open(f,encoding='utf-8',errors='ignore').read()
    t=re.sub(r'(?is)<(script|style).*?</\1>','',t)
    t=re.sub(r'(?is)<!--.*?-->','',t)
    t=re.sub(r'(?s)<[^>]+>','\n',t);t=html.unescape(t)
    t='\n'.join(l.strip() for l in t.split('\n') if l.strip())
    open(f.rsplit('.',1)[0]+'.txt','w').write(t); print(f,len(t))
