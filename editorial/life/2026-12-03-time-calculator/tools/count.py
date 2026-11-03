import sys,re,html
s=open(sys.argv[1],encoding='utf-8').read()
h2=len(re.findall(r'<h2[ >]',s));h3=len(re.findall(r'<h3[ >]',s))
t=re.sub(r'(?is)<(script|style).*?</\1>',' ',s);t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(t)
print('chars_total',len(re.sub(r'\s+',' ',t).strip()),'chars_nospace',len(re.sub(r'\s','',t)),'H2',h2,'H3',h3)
