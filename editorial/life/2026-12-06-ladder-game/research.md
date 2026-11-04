# 사다리타기 — 조사 메모 (2026-11-05)

키워드(네이버 월간): 사다리타기 267,100 · 사다리게임 144,400 · 사다리타기게임 134,000.
유형: 도구형(계산기형 허용). 정부 기관 출처가 없는 놀이라 "공식 자체가 출처" 규칙 적용. 이름 붙은 결과(인접 호환·마르코프 체인)는 수학 문헌 1건 + 위키백과로 확인.
기존 life 글과 겹침: ~/blog/editorial/life/*/ko.html 에서 사다리 관련 글 없음(grep '사다리' 결과는 청약·경매 등 무관한 글뿐). 관련 글 링크는 wpdates.csv 상 2026-12-06 12:00 이전 발행분만.
카테고리 330(일반 계산기).
사용 통계·이용률 같은 수치는 쓰지 않았다(확인 가능한 공식 통계 없음).

## 출처와 원문 (curl 11/05, evidence/ 저장)

- Crossref 메타데이터 (evidence/crossref-lange-miller-1992.json, https://api.crossref.org/works/10.1080/07468342.1992.11973487)
  - title: "A Random Ladder Game: Permutations, Eigenvalues, and Convergence of Markov Chains"
  - container-title: "The College Mathematics Journal", volume 23, issue 5, page "373-385", authors Lange, Miller, DOI https://doi.org/10.1080/07468342.1992.11973487
  - 본문 PDF는 유료라 확인하지 못했다. 본문에서는 논문 존재와 주제(사다리를 마르코프 체인으로 분석)만 언급하고, 수치는 인용하지 않았다.
- 한국어 위키백과 사다리타기 (evidence/wiki-ko-sadaritagi.txt)
  - "n개의 세로줄로 된 사다리타기가 있다고 했을 때, 사다리타기의 가로줄 선분 하나는 두 인접한 원소 사이의 치환 으로 볼 수 있으며 전체는 그 치환의 곱이므로 역시 n개의 원소에 대한 치환이다."
  - "또한, 임의의 사다리타기의 끝에 하나의 가로줄을 무작위로 더하는 것은, 그 사다리타기에 해당하는 치환으로부터 다른 치환으로 전체 상태를 바꾸는 마르코프 체인 에 해당한다. [ 1 ]" — 각주 1이 Lange·Miller(1992).
- 영어 위키백과 Ghost leg (evidence/wiki-en-ghost-leg.txt, https://en.wikipedia.org/wiki/Amidakuji)
  - "It is guaranteed that two items at the top will never have the same corresponding item at the bottom, nor will any item on the bottom ever lack a corresponding item at the top. It also works regardless of how many horizontal lines are added."
  - "As each leg exchanges the two neighboring elements at its ends, the number of legs indicates the odd/even permutation property of the ghost leg. An odd number of legs represents an odd permutation, and an even number of legs gives an even permutation."
  - "It is possible to express every permutation as a ghost leg"
  - "If the number of legs is small relative to number of tracks, the probabilities of different attainable permutations may vary greatly; for large numbers of legs the probabilities of different attainable permutations approach equality."

## 직접 계산한 값 (모형과 공식)

모형: 가로줄마다 N-1개의 이웃 쌍 중 하나를 확률 1/(N-1)로 고르고, 서로 다른 높이에 긋는다.
한 사람 위치의 전이: 왼쪽 1/(N-1), 오른쪽 1/(N-1), 나머지 제자리(끝 칸은 한쪽만). K개 뒤 분포 = 전이행렬^K. 대칭 이중확률행렬이라 극한은 균등(1/N). N=2는 주기 2라 수렴하지 않음(짝수 제자리, 홀수 교환).
'±10% 안' = 모든 시작 칸 s, 결과 칸 j에 대해 |P(s→j)·N − 1| ≤ 0.1 을 만족하는 최소 K.

| N | 1/N | K=N 1→1 | K=3N 1→1 | ±10% K | ±5% K |
|---|---|---|---|---|---|
| 3 | 33.3 | 37.5 | 33.4 | 5 | 6 |
| 4 | 25.0 | 43.2 | 28.1 | 14 | 17 |
| 5 | 20.0 | 45.1 | 28.1 | 29 | 36 |
| 6 | 16.7 | 46.4 | 28.7 | 54 | 66 |
| 7 | 14.3 | 47.3 | 29.1 | 88 | 109 |
| 8 | 12.5 | 47.9 | 29.5 | 135 | 166 |
| 9 | 11.1 | 48.5 | 29.7 | 196 | 241 |
| 10 | 10.0 | 48.9 | 30.0 | 272 | 336 |
| 11 | 9.1 | 49.2 | 30.1 | 366 | 451 |
| 12 | 8.3 | 49.5 | 30.3 | 480 | 591 |

모두 evidence/calc-test.js 가 ko.html 스크립트로 재계산하고 몬테카를로 시뮬레이션(20만 회)과 대조한다.

## 페이지 사다리 생성 방식

위쪽: 무작위 가로줄 N개(crypto.getRandomValues, 거부 샘플링). 아래쪽: Fisher-Yates로 균등 순열 τ를 뽑고, τ의 역전(인접 내림)을 무작위 순서로 하나씩 풀어 얻은 인접 교환 열을 뒤집어 붙임(가로줄 수 = 역전 수 ≤ N(N-1)/2). 전체 = 위쪽 ∘ τ, τ가 균등하고 위쪽과 독립이므로 전체도 균등. 검산: 4명 20만 회 24가지 배정 카이제곱(df=23) 통과, 12명 12만 회 1번 자리 결과 칸별 비율 8.3% 내외.
