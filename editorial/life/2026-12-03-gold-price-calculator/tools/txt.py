import re,sys,html
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',t)
t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
pat=sys.argv[2] if len(sys.argv)>2 else None
if pat:
    for m in re.findall(r'.{0,150}(?:'+pat+r').{0,150}',t)[:15]: print('-',m)
else: print(t)
