import re,html,sys
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
s=re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>','',s,flags=re.S|re.I)
s=re.sub(r'<br\s*/?>|</(p|div|li|tr|h\d|td|th)>','\n',s,flags=re.I)
s=re.sub(r'<[^>]+>',' ',s)
s=html.unescape(s)
out=[]
for l in s.split('\n'):
    l=re.sub(r'[ \t\xa0]+',' ',l).strip()
    if l: out.append(l)
print('\n'.join(out))
