import re,html,sys
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
i=t.find('id="contents"');
if i<0: i=t.find('class="contents');
t=t[i if i>0 else 0:]
t=re.sub(r'<(script|style).*?</\1>','',t,flags=re.S)
t=re.sub(r'<(br|/p|/tr|/li|/h\d|/div)[^>]*>','\n',t)
t=re.sub(r'<t[dh][^>]*>',' | ',t)
t=re.sub(r'<[^>]+>','',t);t=html.unescape(t)
t=re.sub(r'[ \t]+',' ',t);t=re.sub(r'\n\s*\n+','\n',t)
print(t)
