#!/bin/bash
# usage: fetch_law.sh <법령명> <outname>
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
P=$(curl -s -A "$UA" "https://www.law.go.kr/법령/$1")
SEQ=$(echo "$P" | grep -o "lsiSeq=[0-9]*" | head -1 | cut -d= -f2)
EF=$(echo "$P" | grep -o "efYd=[0-9]*" | head -1 | cut -d= -f2)
curl -s -A "$UA" -o "evidence/$2.html" "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=$SEQ&efYd=$EF"
python3 -c "import re,html,sys;t=open(sys.argv[1],encoding='utf-8',errors='ignore').read();t=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',t);t=re.sub(r'<[^>]+>',' ',t);t=html.unescape(t);t=re.sub(r'[ \t]+',' ',t);t=re.sub(r'\n\s*\n+','\n',t);open(sys.argv[2],'w').write(t)" "evidence/$2.html" "evidence/$2.txt"
echo "$1 lsiSeq=$SEQ efYd=$EF $(wc -c < evidence/$2.txt)"
