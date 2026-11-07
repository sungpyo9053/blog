import re,html,sys
for f in sys.argv[1:]:
    t=open(f,encoding='utf-8').read()
    t=re.sub(r'<(script|style).*?</\1>','',t,flags=re.S)
    t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(t);t=re.sub(r'\s+',' ',t)
    print('=====',f);print(t)
