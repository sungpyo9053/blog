#!/bin/bash
# KASI 음양력 변환 /life/lunc 로 음력 Y년 M월 1일을 조회 (평달+윤달 둘 다 응답됨). 1950~2050.
cd "$(dirname "$0")/.."
out=evidence/kasi-lunc-month-starts-1950-2050.jsonl
: > "$out"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
for y in $(seq 1950 2050); do for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
  r=$(curl -s --max-time 30 -A "$UA" "https://astro.kasi.re.kr/life/lunc?yyyy=$y&mm=$m&dd=01")
  echo "{\"q\":\"$y-$m-01\",\"r\":$r}" >> "$out"
  sleep 0.15
done; done
wc -l "$out"
