import re,sys,json
s=open(sys.argv[1],encoding='utf8').read()
recs=[]
for body in re.findall(r'\{(TP_NAME:.*?)\}(?=,\{TP_NAME|\])',s,re.S):
    d={}
    for k,v in re.findall(r"([A-Z_0-9]+):('(?:[^'\\]|\\.)*'|[-0-9.]+)",body):
        d[k]=v.strip("'") if v.startswith("'") else v
    recs.append(d)
json.dump(recs,open(sys.argv[2],'w'),ensure_ascii=False)
print(len(recs))
