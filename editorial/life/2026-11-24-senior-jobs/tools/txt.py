import re,sys,html
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'<script.*?</script>|<style.*?</style>','',s,flags=re.S)
t=re.sub(r'<br\s*/?>|</p>|</tr>|</li>|</div>','\n',t);t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(t)
t=re.sub(r'[ \t\xa0]+',' ',t);t=re.sub(r'\n\s*\n+','\n',t)
a=sys.argv[2] if len(sys.argv)>2 else None
if a:
  i=t.find(a);t=t[i:]
print(t[:int(sys.argv[3]) if len(sys.argv)>3 else 20000])
