import re,html,sys
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'<script.*?</script>|<style.*?</style>','',s,flags=re.S)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'[ \t\r\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
print(t)
