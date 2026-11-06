import re,html,sys
t=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'<(script|style|noscript|svg)[\s\S]*?</\1>','',t,flags=re.I)
s=re.sub(r'<br\s*/?>|</(p|li|tr|div|h\d|dd|dt)>','\n',s,flags=re.I)
s=html.unescape(re.sub(r'<[^>]+>',' ',s))
lines=[' '.join(l.split()) for l in s.split('\n')]
print('\n'.join(l for l in lines if l))
