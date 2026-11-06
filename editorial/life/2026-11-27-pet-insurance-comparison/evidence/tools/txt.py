import re,sys,html
s=open(sys.argv[1],encoding='utf8',errors='ignore').read()
s=re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>','',s)
s=re.sub(r'(?i)<br\s*/?>|</p>|</li>|</tr>|</h\d>|</div>','\n',s)
s=html.unescape(re.sub(r'<[^>]+>',' ',s))
s=re.sub(r'[ \t ]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
print(s.strip())
