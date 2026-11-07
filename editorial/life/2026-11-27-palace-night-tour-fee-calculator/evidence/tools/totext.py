import re,html,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->','',s)
s=re.sub(r'(?i)<br\s*/?>|</p>|</li>|</tr>|</h\d>|</div>','\n',s)
t=re.sub(r'<[^>]+>',' ',s); t=html.unescape(t)
t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
print(t)
