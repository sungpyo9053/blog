import re,sys,html
s=open(sys.argv[1]).read()
s=re.sub(r'<script.*?</script>','',s,flags=re.S)
t=html.unescape(re.sub(r'<[^>]+>','',s))
print('with spaces',len(re.sub(r'\s+',' ',t).strip()),'nospace',len(re.sub(r'\s','',t)),'h2',s.count('<h2'),'h3',s.count('<h3'))
