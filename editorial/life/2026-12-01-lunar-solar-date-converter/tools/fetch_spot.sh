#!/bin/bash
# 계산기 검산용 KASI 개별 조회 (양력→음력 solc, 음력→양력 lunc)
cd "$(dirname "$0")/../evidence"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
: > kasi-solc-spotcheck.jsonl; : > kasi-lunc-spotcheck.jsonl
for d in 1950-02-17 1970-01-01 1984-12-22 1988-09-17 2000-01-01 2020-01-25 2020-05-23 2020-06-20 2020-10-01 2023-01-22 2023-03-22 2023-04-19 2023-09-29 2025-01-29 2025-07-25 2025-08-22 2025-10-06 2026-02-17 2026-09-25 2026-11-02 2026-12-01 2027-02-07 2027-09-15 2028-02-09 2033-12-22 2044-09-01 2050-12-31; do
  curl -s --max-time 30 -A "$UA" "https://astro.kasi.re.kr/life/solc?yyyy=${d:0:4}&mm=${d:5:2}&dd=${d:8:2}" >> kasi-solc-spotcheck.jsonl; echo >> kasi-solc-spotcheck.jsonl; sleep 0.2
done
for d in 1990-05-15 2001-04-10 2020-04-15 2023-02-29 2025-06-06 2026-01-01 2026-08-15 2027-01-15 2028-05-05 2033-11-01 2033-11-30; do
  curl -s --max-time 30 -A "$UA" "https://astro.kasi.re.kr/life/lunc?yyyy=${d:0:4}&mm=${d:5:2}&dd=${d:8:2}" | sed "s/^/{\"q\":\"$d\",\"r\":/; s/\$/}/" >> kasi-lunc-spotcheck.jsonl; echo >> kasi-lunc-spotcheck.jsonl; sleep 0.2
done
