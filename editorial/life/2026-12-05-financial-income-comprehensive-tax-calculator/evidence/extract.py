# 법령 전체 HTML(/tmp, 3MB 초과)에서 인용 조문만 뽑아 evidence/*.txt로 저장. 사용: python3 extract.py <txt> <out> <url> <조문...> [--buchik 법률번호]
import sys,re
src,out,url=sys.argv[1:4]; arts=sys.argv[4:]
s=open(src).read(); head=s[:1500]
m=re.search(r'\[시행[^\]]*\]\s*\[[^\]]*\]',head)
res=[url, m.group() if m else '']
for a in arts:
    if a.startswith('BUCHIK:'):
        key=a[7:]; i=s.find(key); res.append('===== 부칙 '+key); res.append(s[i:i+4000] if i>=0 else 'NOTFOUND'); continue
    mm=re.search(r'\n\s*'+re.escape(a)+r'\(',s)
    if not mm: res.append('NOTFOUND '+a); continue
    st=mm.start(); nx=re.search(r'\n\s*제\d+조(의\d+)?[\( ]',s[st+5:])
    res.append('===== '+a); res.append(s[st:st+5+(nx.start() if nx else 4000)].strip())
open(out,'w').write('\n'.join(res)+'\n')
