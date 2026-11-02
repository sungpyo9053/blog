import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<(script|style).*?</\1>',' ',s);s=re.sub(r'<[^>]+>',' ',s);s=html.unescape(s);s=re.sub(r'[ \t\r\xa0]+',' ',s);s=re.sub(r'\n\s*\n+','\n',s)
print(s)
