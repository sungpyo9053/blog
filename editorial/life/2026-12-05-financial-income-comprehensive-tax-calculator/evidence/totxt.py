import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
s=re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>',r' [img:\1] ',s)
s=re.sub(r'<(script|style)[\s\S]*?</\1>','',s)
s=re.sub(r'<br\s*/?>|</p>|</div>','\n',s)
s=re.sub(r'<[^>]+>','',s); s=html.unescape(s)
s=re.sub(r'[ \t\xa0]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
open(sys.argv[2],'w').write(s)
