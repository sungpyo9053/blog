import re,html,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'<!--.*?-->','',s,flags=re.S)
s=re.sub(r'<(script|style)[^>]*>.*?</\1>','',s,flags=re.S|re.I)
s=re.sub(r'<br\s*/?>|</(p|div|li|tr|h\d|td|th|dt|dd)>','\n',s,flags=re.I)
s=re.sub(r'<(td|th)[^>]*>',' | ',s,flags=re.I)
s=html.unescape(re.sub(r'<[^>]+>','',s))
print('\n'.join(l.strip() for l in s.split('\n') if l.strip()))
