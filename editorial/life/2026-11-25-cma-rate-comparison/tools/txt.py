import re,sys,html
t=open(sys.argv[1],encoding=sys.argv[3] if len(sys.argv)>3 else 'utf-8',errors='ignore').read()
t=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
for m in re.finditer(r'.{0,350}(%s).{0,350}'%sys.argv[2],t): print('>>',m.group(0)); print()
