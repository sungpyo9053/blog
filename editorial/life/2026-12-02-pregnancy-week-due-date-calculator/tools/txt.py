import re,sys,html
s=open(sys.argv[1],encoding='utf8',errors='ignore').read()
s=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',s)
s=re.sub(r'<br\s*/?>|</p>|</li>|</h\d>|</tr>','\n',s)
s=html.unescape(re.sub(r'<[^>]+>','',s))
s=re.sub(r'[ \t\r]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
print(s)
