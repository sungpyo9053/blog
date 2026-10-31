import re,html,sys
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r"(?s)<!--.*?-->","",t)
t=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',t);t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(re.sub(r'\s+',' ',t))
k=sys.argv[2] if len(sys.argv)>2 else ''
i=t.rfind(k) if k else 0
print(t[max(i,0):][:int(sys.argv[3]) if len(sys.argv)>3 else 8000])
