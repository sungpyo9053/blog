import re,html,sys
for f in sys.argv[1:]:
    t=open(f,encoding='utf-8',errors='ignore').read()
    t=re.sub(r'<(script|style).*?</\1>','',t,flags=re.S)
    t=re.sub(r'<br\s*/?>|</p>|</div>|</tr>',chr(10),t)
    t=html.unescape(re.sub(r'<[^>]+>',' ',t))
    t=re.sub(r'[ \t\r\f\v\xa0]+',' ',t); t=re.sub(r'\n\s*\n+',chr(10),t)
    open(f.rsplit('.',1)[0]+'.txt','w').write(t)
