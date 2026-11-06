import json,glob,collections,sys
rot={ (r['deprCd'],r['arvlCd']):(r['deprNm'],r['arvlNm']) for r in json.load(open('rot.json'))['rotInfList']}
out={}
for f in sorted(glob.glob('raw_*.json')):
    _,dt,d,a=f[:-5].split('_')
    try: j=json.load(open(f))
    except Exception as e: print('ERR',f,e); continue
    m=collections.OrderedDict()
    for x in j.get('alcnAllList') or []:
        k=x['BUS_CLS_NM']; v=(int(x['ADLT_FEE']),int(x['CHLD_FEE']),int(x['TEEN_FEE']),int(x.get('UVSD_FEE') or 0))
        m.setdefault(k,collections.Counter())[v]+=1
    out[f'{dt} {rot[(d,a)][0]}->{rot[(d,a)][1]} ({j.get("alcnCmnMap",{}).get("takeDrtm")})']={k:{'%d/%d/%d/%d'%v:c for v,c in cc.items()} for k,cc in m.items()}
json.dump(out,open(sys.argv[1],'w'),ensure_ascii=False,indent=0)
for k,v in out.items(): print(k, json.dumps(v,ensure_ascii=False))
