import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?s)<!--.*?-->',' ',s)
s=re.sub(r'(?is)<(script|style|head)[^>]*>.*?</\1>',' ',s)
s=re.sub(r'(?i)<br\s*/?>|</(p|li|tr|div|h\d|dt|dd)>','\n',s)
s=re.sub(r'(?i)</t[dh]>',' | ',s)
s=re.sub(r'<[^>]+>',' ',s)
s=html.unescape(s)
lines=[re.sub(r'[ \t\xa0]+',' ',l).strip() for l in s.split('\n')]
print('\n'.join(l for l in lines if l and l!='|'))
