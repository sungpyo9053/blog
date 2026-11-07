import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<(script|style|option)[^>]*>.*?</\1>',' ',s)
s=html.unescape(re.sub(r'<[^>]+>',' ',s))
s=re.sub(r'\s+',' ',s)
if len(sys.argv)>2:
    for m in re.finditer(sys.argv[2],s): print('...',s[max(0,m.start()-int(sys.argv[3] if len(sys.argv)>3 else 150)):m.end()+400],'\n')
else: print(s)
