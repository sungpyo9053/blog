# kfb-prepay-2026.utf8.html -> kfb-prepay-2026.json (가계 고정/변동만)
import re,html,json
t=open('kfb-prepay-2026.utf8.html').read()
out={};bank=None
for r in re.findall(r'<tr.*?</tr>',t,re.S):
    c=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',r,re.S)]
    if len(c)==8: bank=c[0].replace('-->','').strip(); c=c[2:]
    elif len(c)==6: pass
    else: continue
    out.setdefault(bank,{})[c[0]]={'fix':c[1],'var':c[2],'note':c[5]}
json.dump(out,open('kfb-prepay-2026.json','w'),ensure_ascii=False,indent=1)
for b,v in out.items(): print(b,'|',' '.join(k+':'+x['fix']+'/'+x['var'] for k,x in v.items()),'|',v['부동산 및 동산']['note'])
