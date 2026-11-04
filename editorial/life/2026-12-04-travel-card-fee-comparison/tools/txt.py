import re,sys,html
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'(?s)<(script|style)[^>]*>.*?</\1>','',t);t=html.unescape(re.sub(r'<[^>]+>',' ',t));t=re.sub(r'\s+',' ',t)
if len(sys.argv)>2:
  for k in sys.argv[2:]:
    for m in re.finditer(k,t): print('['+k+']',t[max(0,m.start()-150):m.end()+200]);print()
else: print(t)
