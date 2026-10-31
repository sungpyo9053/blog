import sys,re,html
for f in sys.argv[1:]:
    s=open(f,encoding='utf-8',errors='replace').read()
    s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s)
    s=re.sub(r'(?i)<br\s*/?>|</(p|li|tr|div|h\d|dt|dd)>','\n',s)
    s=re.sub(r'<[^>]+>',' ',s); s=html.unescape(s)
    s=re.sub(r'[ \t\r\xa0]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
    open(f.rsplit('.',1)[0]+'.txt','w').write(s)
