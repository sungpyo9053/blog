import json,sys
d=json.load(open(sys.argv[1]))
cat={x['id']:x['name'] for x in d}
for x in d:
  for p in x['products'] or []:
    tm=p.get('ticketMaster') or {}
    dm=p.get('discountMaster') or {}
    print(x['id'],cat.get(x['parentId']),'>',x['name'],'|',p['id'],p['name'],'|',p['price'],'->',p['discountedPrice'],'| age',tm.get('ageLimit'),'| dates',p['dates'],'| grp',p['group'],'max',p['maxCount'],'req',p['requirement'],'| dm',dm.get('name'),dm.get('value'))
