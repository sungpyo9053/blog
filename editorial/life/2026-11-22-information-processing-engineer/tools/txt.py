import sys,re,html
t=open(sys.argv[1],encoding='utf-8',errors='replace').read()
t=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',t);t=re.sub(r'<[^>]+>',' ',t);print(html.unescape(re.sub(r'\s+',' ',t)))
