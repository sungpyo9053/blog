import re,html,sys
for f in sys.argv[1:]:
    s=open(f,encoding='utf-8',errors='ignore').read()
    m=re.search(r'id="contents"|<div class="contents|<main',s)
    s=re.sub(r'<(script|style)[\s\S]*?</\1>','',s)
    s=re.sub(r'<br\s*/?>|</p>|</li>|</tr>|</h\d>|</div>','\n',s)
    s=re.sub(r'</t[dh]>',' | ',s)
    s=re.sub(r'<[^>]+>','',s)
    s=html.unescape(s)
    s=re.sub(r'[ \t\xa0]+',' ',s)
    s=re.sub(r'\n\s*\n+','\n',s)
    open(f.rsplit('.',1)[0]+'.txt','w').write(s)
