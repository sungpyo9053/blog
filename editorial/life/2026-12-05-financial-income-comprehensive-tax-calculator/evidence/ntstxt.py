import re,html,sys
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
i=s.find('id="contents"'); t=s[i:]
j=t.find('콘텐츠 만족도'); t=t[:j] if j>0 else t
t=re.sub(r'<(script|style)[\s\S]*?</\1>','',t)
t=re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>',r' [img:\1] ',t)
t=re.sub(r'<br\s*/?>|</p>|</li>|</tr>|</h\d>|</div>','\n',t); t=re.sub(r'</t[dh]>',' | ',t)
t=re.sub(r'<[^>]+>','',t); t=html.unescape(t); t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(sys.argv[2],'w').write(sys.argv[3]+'\n'+t); print(t)
