import re,sys,html
for f in sys.argv[1:]:
    t=open(f,encoding='utf-8',errors='ignore').read()
    t=re.sub(r'<script.*?</script>','',t,flags=re.S);t=html.unescape(re.sub(r'<[^>]+>',' ',t));t=re.sub(r'[ \t\r\f\v]+',' ',t);t=re.sub(r'\n\s*\n+','\n',t)
    open(f+'.txt','w').write(t)
