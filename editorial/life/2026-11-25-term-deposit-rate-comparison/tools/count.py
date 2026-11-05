import re,sys,html
t=open(sys.argv[1]).read()
t=re.sub(r'(?s)<script.*?</script>','',t)
h2=len(re.findall(r'<h2',t));h3=len(re.findall(r'<h3',t))
v=html.unescape(re.sub(r'<[^>]+>','',t))
print('visible(with spaces)',len(re.sub(r'\s+',' ',v).strip()),'no-space',len(re.sub(r'\s','',v)),'H2',h2,'H3',h3)
