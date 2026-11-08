import re,sys,html
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'(?s)<(script|style).*?</\1>','',t);t=re.sub(r'(?s)<!--.*?-->','',t)
t=re.sub(r'<(br|/p|/div|/tr|/li|/h\d)[^>]*>','\n',t,flags=re.I);t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(t)
print('\n'.join(re.sub(r'\s+',' ',l).strip() for l in t.splitlines() if l.strip()))
