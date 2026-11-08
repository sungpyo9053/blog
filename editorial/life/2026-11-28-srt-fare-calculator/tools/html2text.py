import re,sys,html
s=open(sys.argv[1],encoding='utf-8').read()
i=s.find('class="board_view') if 'board_view' in s else s.find('<h2')
s=re.sub(r'<(script|style).*?</\1>','',s,flags=re.S)
t=re.sub(r'<br\s*/?>|</p>|</li>|</tr>|</h\d>|</div>','\n',s)
t=re.sub(r'</t[dh]>',' | ',t)
t=html.unescape(re.sub(r'<[^>]+>','',t))
t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
print(t)
