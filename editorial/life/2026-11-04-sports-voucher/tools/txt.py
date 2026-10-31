import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s)
s=re.sub(r'(?s)<!--.*?-->',' ',s)
s=re.sub(r'(?i)<br\s*/?>|</(p|li|tr|h\d|div|dt|dd|th|td)>','\n',s)
s=html.unescape(re.sub(r'<[^>]+>',' ',s))
s='\n'.join(l.strip() for l in s.splitlines() if l.strip())
m=sys.argv[2] if len(sys.argv)>2 else None
if m and m in s: s=s[s.rfind(m):] if '--last' in sys.argv else s[s.find(m):]
print(s)
