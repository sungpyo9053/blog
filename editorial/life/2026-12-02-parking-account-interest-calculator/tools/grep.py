import sys,re,html
f,pat=sys.argv[1],sys.argv[2]; w=int(sys.argv[3]) if len(sys.argv)>3 else 150
t=open(f,encoding='utf-8',errors='ignore').read()
t=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
n=0
for m in re.finditer(pat,t):
    print('>>',t[max(0,m.start()-w):m.end()+w]); n+=1
    if n>=int(sys.argv[4] if len(sys.argv)>4 else 5): break
