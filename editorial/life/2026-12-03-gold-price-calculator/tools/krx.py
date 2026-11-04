import re,sys,html
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',t)
t=re.sub(r'(?s)<a [^>]*data-menu-id[^>]*>.*?</a>','',t)
t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
print(t)
