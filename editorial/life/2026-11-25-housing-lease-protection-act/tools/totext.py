import re,sys,html
for f in sys.argv[1:]:
    t=open(f,encoding='utf-8',errors='ignore').read()
    t=re.sub(r'<(script|style).*?</\1>','',t,flags=re.S|re.I);t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(t);t=re.sub(r'\s+',' ',t)
    open(f.rsplit('.',1)[0]+'.txt','w').write(t)
