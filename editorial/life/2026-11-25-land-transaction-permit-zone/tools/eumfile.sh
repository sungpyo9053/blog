#!/bin/sh
# usage: eumfile.sh seq filepath outname
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
E=$(dirname "$0")/../evidence
FE=$(printf '%s' "$2" | iconv -f UTF-8 -t EUC-KR | python3 -c "import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.buffer.read()))")
curl -sL -A "$UA" -e "https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp?seq=$1" "https://www.eum.go.kr/web/FileDownload.do" --data "file=$FE&gosi=Y&seq=$1&mobile_yn=" -o "$E/$3"
file "$E/$3"
