import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s) if len(sys.argv)<3 else s
s=re.sub(r'(?s)<[^>]+>','\n',s)
s=html.unescape(s)
lines=[re.sub(r'\s+',' ',l).strip() for l in s.split('\n')]
print('\n'.join(l for l in lines if l))
