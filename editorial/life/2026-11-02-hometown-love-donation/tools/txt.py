import re,html,sys
for f in sys.argv[1:]:
  t=open(f,encoding='utf-8').read()
  t=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S)
  t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
  open(f.rsplit('.',1)[0]+'.txt','w').write(t); print(f,len(t))
