import sys,re,html
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
s=re.sub(r'(?s)<!--.*?-->|<script.*?</script>|<style.*?</style>','',s)
s=re.sub(r'(?i)<(td|th)[^>]*>','\n| ',s)
s=re.sub(r'<[^>]+>','\n',s)
s=html.unescape(s)
lines=[l.strip() for l in s.split('\n')]
print('\n'.join(l for l in lines if l))
