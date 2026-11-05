# tools/body.html + tools/cal.js -> ko.html
import re,json,os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
b=open('tools/body.html').read(); js=open('tools/cal.js').read().strip()
assert '\n\n' not in js and '&' not in js and '<' not in js
anchor='<div id="cal-out" aria-live="polite"></div>\n</div>\n'
b=b.replace(anchor,anchor+'<script>\n'+js+'\n</script>\n')
open('ko.html','w').write(b)
ld=re.search(r'application/ld\+json">(.*?)</script>',b,re.S).group(1); d=json.loads(ld); assert '&' not in ld and '<' not in ld
t=re.sub(r'<script.*?</script>','',b,flags=re.S); t=re.sub(r'<[^>]+>','',t); t=re.sub(r'\s+',' ',t).strip()
print('faq-ld',len(d['mainEntity']),'visible(공백 포함)',len(t),'공백 제외',len(t.replace(' ','')),'h2',b.count('<h2'),'h3',b.count('<h3'))
