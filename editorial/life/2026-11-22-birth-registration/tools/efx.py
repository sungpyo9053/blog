import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
for m in re.finditer(r'\$\("#contentSpan"\)\.html\("(.*?)"\);\s*\n',s,re.S):
    t=m.group(1).replace('\\"','"').replace('\\/','/')
    t=re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>',r' [그림: \1] ',t)
    t=re.sub(r'(?i)<br\s*/?>|</(p|div|li|tr|h\d|th|td)>','\n',t)
    t=re.sub(r'<[^>]+>','',t); t=html.unescape(t)
    print(re.sub(r'\n\s*\n+','\n',t))
