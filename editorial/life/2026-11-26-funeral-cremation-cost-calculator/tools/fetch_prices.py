# e하늘 공개 가격 JSON 수집 (일반 브라우저 UA, 시설별 0.5초 간격)
import json,sys,time,urllib.request,urllib.parse
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
B='https://www.15774129.go.kr/portal/fnlfac/'
def post(path,data):
    r=urllib.request.Request(B+path,urllib.parse.urlencode(data).encode(),{'User-Agent':UA})
    return json.load(urllib.request.urlopen(r,timeout=30))
grp,out=sys.argv[1],sys.argv[2]
lst=[];p=1
while True:
    d=post('fac_list.ajax',{'pageInqCnt':100,'curPageNo':p,'facilitygroupcd':grp,'sidocd':'','gungucd':'','companyname':'','publiccode':''})
    lst+=d['list']
    if len(lst)>=d['cnt'] or not d['list']: break
    p+=1
res=[]
for f in lst:
    try: d=post('price_info.ajax',{'facilitycd':f['facilitycd'],'sanbundiv':f.get('sanbundiv') or 'N'})
    except Exception as e: d={'hallRent':[],'err':str(e)}
    res.append({'name':f['companyname'],'sido':f['sidonm'],'public':f['publiccode'],'updated':f['lastUpdateDate'],'cd':f['facilitycd'],
      'fees':[{k:r.get(k) for k in ('item','rentcontent','facilityamt','tier1Nm','tier2Nm','sale')} for r in d.get('hallRent',[])]})
    time.sleep(0.5)
json.dump(res,open(out,'w'),ensure_ascii=False,indent=0)
print(len(lst),'facilities')
