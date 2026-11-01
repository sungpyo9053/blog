import re,html,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?s)<script.*?</script>|<style.*?</style>|<!--.*?-->','',s)
s=re.sub(r'(?i)<(br|/p|/tr|/li|/h\d|/div|/caption)[^>]*>','\n',s)
s=re.sub(r'(?i)</t[dh]>',' | ',s)
t=html.unescape(re.sub(r'<[^>]+>',' ',s)); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
print(t)
