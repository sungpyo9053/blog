import re,sys,html
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
s=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',s); t=html.unescape(re.sub(r'<[^>]+>','\n',s))
L=[l.strip() for l in t.split('\n') if l.strip()]
seen=set()
for i,l in enumerate(L):
  if re.search(sys.argv[2],l):
    c=' / '.join(L[max(0,i-5):i+2])[:400]
    if c not in seen: seen.add(c); print('...',c)
