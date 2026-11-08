# accesso GetKeywordCalendar / bootstrap JSON -> date|package|대인/소인 total (retail+tax)
import json,sys,collections,datetime
L=lambda v: v if isinstance(v,list) else [v]
def cal(f):
    s=json.load(open(f))['SERVICE']; print('== '+f, s.get('status'))
    for x in L(s.get('DATES',{}).get('D',[])):
        wd='월화수목금토일'[datetime.date.fromisoformat(x['date']).weekday()]
        print(x['date'],wd,' ; '.join(p['name']+' '+'/'.join(str(round(float(c['retail_amount'])+float(c['tax_amount']))) for c in sorted(L(p['CT']),key=lambda c:c['id'])) for p in L(x['PS']['P'])))
def boot(f,ids):
    P=json.load(open(f))['GetMerchantPackageList']['SERVICE']['PS']['P']
    for p in P:
        if p['id'] in ids:
            print(p['id'],p['name'],'| keywords:',p.get('assoc_keywords'))
            for c in L(p['CT']): print('   CT',c['id'],c['name'].strip(),'retail',c['retail_amount'],'tax',c['tax_amount'],'=',c['retail_value'])
if sys.argv[1]=='boot': boot(sys.argv[2],sys.argv[3].split(','))
else:
    for f in sys.argv[2:]: cal(f)
