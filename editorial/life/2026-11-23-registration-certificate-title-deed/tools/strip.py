import re,html,sys
for f in sys.argv[1:]:
    t=open(f,'rb').read()
    try: t=t.decode('utf-8')
    except: t=t.decode('euc-kr',errors='ignore')
    s=re.sub(r'(?is)<script.*?</script>|<style.*?</style>','',t)
    s=re.sub(r'(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>','\n',s)
    s=html.unescape(re.sub(r'<[^>]+>',' ',s))
    s=re.sub(r'[ \t\r\xa0]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
    open(f+'.txt','w').write(s); print(f,len(s))
