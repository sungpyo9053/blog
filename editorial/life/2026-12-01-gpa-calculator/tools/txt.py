import re,html,sys
t=open(sys.argv[1],encoding=sys.argv[3] if len(sys.argv)>3 else 'utf-8',errors='ignore').read()
t=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S|re.I)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
k=sys.argv[2]; i=t.find(k); print(len(t), i); print(t[max(0,i-200):i+int(sys.argv[4]) if len(sys.argv)>4 else i+3500])
