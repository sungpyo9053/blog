import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<(script|style).*?</\1>',' ',s)
s=re.sub(r'(?i)<br\s*/?>|</(p|tr|li|h\d|div|td|th)>','\n',s)
s=html.unescape(re.sub(r'<[^>]+>',' ',s))
s=re.sub(r'[ \t\xa0]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
print(s)
