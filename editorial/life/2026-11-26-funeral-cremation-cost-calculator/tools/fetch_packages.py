# e하늘 장례예식 패키지 상품 중 이름에 '무빈소'가 들어간 상품 + 각 상세 항목 수집
import json,sys,time,urllib.request,urllib.parse
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
B='https://www.15774129.go.kr/portal/fnlfac/'
def post(path,data):
    r=urllib.request.Request(B+path,urllib.parse.urlencode(data).encode(),{'User-Agent':UA})
    return json.load(urllib.request.urlopen(r,timeout=30))
name,out=sys.argv[1],sys.argv[2]
d=post('funeral_package_list.ajax',{'pageInqCnt':200,'curPageNo':1,'sidocd':'','gungucd':'','packagename':name,'publiccodes':''})
res=[]
for x in d['list']:
    det=post('package_detail.ajax',{'facilitycd':x['mstfaid'],'packageseq':x['packageseq']})
    res.append({'list':x,'detail':det.get('detail'),'items':[{k:i.get(k) for k in ('groupnm','packageitemnm','packageitemdetail','packageitemprice')} for i in det.get('itemList',[])]})
    time.sleep(0.4)
json.dump({'cnt':d['cnt'],'packages':res},open(out,'w'),ensure_ascii=False,indent=0)
print(d['cnt'],len(res))
