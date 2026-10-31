import re,html,sys
t=open(sys.argv[1],encoding='utf8').read();t=re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>',' ',t);t=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)));print(t)
