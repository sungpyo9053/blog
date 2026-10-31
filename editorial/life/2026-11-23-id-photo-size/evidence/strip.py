import re,sys,html
for f in sys.argv[1:]:
    s=open(f,encoding='utf-8',errors='ignore').read()
    s=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',s)
    t=html.unescape(re.sub(r'<[^>]+>',' ',s)); t=re.sub(r'[ \t\r\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
    open(f[:-5]+'.txt','w').write(t)
