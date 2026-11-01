#!/bin/bash
# KASI 음양력 변환(astro.kasi.re.kr/life/solc)으로 2026-12-01 ~ 2027-12-31 양력 하루씩 조회
out=evidence/kasi-solc-2026-12_2027-12.jsonl
: > "$out"
d=2026-12-01
while [ "$d" != "2028-01-01" ]; do
  y=${d:0:4}; m=${d:5:2}; dd=${d:8:2}
  r=$(curl -s -m 20 "https://astro.kasi.re.kr/life/solc?yyyy=$y&mm=$m&dd=$dd")
  echo "$r" >> "$out"
  d=$(date -j -v+1d -f %Y-%m-%d "$d" +%Y-%m-%d)
  sleep 0.2
done
wc -l "$out"
