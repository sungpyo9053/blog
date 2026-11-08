import re,html,sys
t=open(sys.argv[1]).read()
t=re.sub(r'<script[^>]*>.*?</script>','',t,flags=re.S)
t=re.sub(r'<style[^>]*>.*?</style>','',t,flags=re.S)
t=re.sub(r'<[^>]+>','\n',t); t=html.unescape(t)
L=[l.strip() for l in t.split('\n') if l.strip()]
s='\n'.join(L)
a=s.find('민속촌 고객센터')
print(s[:a] if a>0 else s)
