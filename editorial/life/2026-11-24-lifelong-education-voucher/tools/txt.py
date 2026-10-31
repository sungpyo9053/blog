import re,html,sys
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<!--[\s\S]*?-->','',t)
s=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
i=s.find(sys.argv[2]) if len(sys.argv)>2 else 0
print(s[max(i,0):max(i,0)+int(sys.argv[3]) if len(sys.argv)>3 else None])
