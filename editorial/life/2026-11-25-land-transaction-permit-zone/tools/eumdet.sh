#!/bin/sh
# usage: eumdet.sh seq  -> evidence/eum-gosi-<seq>.utf8.html + summary
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
E=$(dirname "$0")/../evidence
curl -sL -A "$UA" "https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp?seq=$1" | iconv -f EUC-KR -t UTF-8 -c > "$E/eum-gosi-$1.utf8.html"
python3 - "$E/eum-gosi-$1.utf8.html" <<'PY'
import re,html,sys
s=open(sys.argv[1],encoding='utf-8').read()
f=re.findall(r"download\('/web/FileDownload.do', '([^']+)'\)",s)
s=re.sub(r'(?s)<script.*?</script>|<style.*?</style>|<!--.*?-->','',s)
s=re.sub(r'<br\s*/?>|</p>|</div>|</li>|</tr>|</th>|</td>','\n',s)
t=html.unescape(re.sub(r'<[^>]+>',' ',s)); t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
i=t.find('고시번호'); j=t.find('목록으로')
print(t[i:j][:1500]); print('FILES',f)
PY
