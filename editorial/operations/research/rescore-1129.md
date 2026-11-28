# 새 채점 도구로 다시 채점 (11/29, 개발 담당)

판결(court-20261128-powerblogger) 무죄 조건 3: 안 2·4만 넣고, 고친 4편과 비교용 20편을 새 도구로 다시 채점한다.

- 도구: `scripts/style_score.py`(그룹 A~D), `scripts/audit_content_repetition.py` template_flags — QA 수정 반영(qa-style-baseline.md §4)
  - 질문 소제목: 맨 '지'·맨 '요' 삭제, '가'는 받침 ㄴ 뒤만, 수가·단가·정가·개요 등 제외, 끝 괄호·콜론 앞뒤 확인
  - 말투: 끝 괄호 주석 제거, '~자' 해라체, 따옴표 끝 처리, '2026.1.1.'에서 문장 안 끊음, '개요·필요·중요'는 other
  - closer `확인하자\.?$`(마지막 3문단), opener 날짜 없어도, FAQ 6개 이상 = `faq_block:N`, `함께 읽으면 좋은 글` 고정 소제목 추가
  - 점수식: FAQ는 FAQ 항목에서만 감점(이중 감점 없음), rules는 FAQ 외 플래그당 −5(8종 다 있어야 0점)
- 대상: 고친 4편 = 로컬 ko.html(WP 본문으로 되받은 것, 그림 포함), 비교용 20편 = ko81-queue.md "비교용(그대로)" 행, 본문 `~/huntlab-ops/fut1128/<ID>.html`. 2006(스타일 시험 대조)은 "그대로" 행이 아니라 뺐다.
- 그룹: qa-style-baseline.md §5 매핑. 옛 도구 총점도 같은 표에서 가져왔다.

## 요약

| 세트 | n | 옛 도구 중앙값 | 새 도구 중앙값 | 새 도구 말투 제외(/80) 중앙값 | 새 도구 범위 |
|---|---|---|---|---|---|
| 고친 4편 | 4 | 75.5 | 72.5 | 72.5 | 69~96 |
| 비교용 | 20 | 12.0 | 20.0 | 20.0 | 16~30 |

해석: 비교용 점수가 12 → 20으로 오른 것은 글이 바뀐 게 아니라 rules가 0에서 멈추지 않고 FAQ를 두 번 깎지 않게 된 결과다. 고친 4편은 질문 소제목 오탐('…가지' 등)이 빠지면서 1~4점 내려갔다(1919는 말투 판정 수정으로 +3). 두 세트 차이는 여전히 약 50점이다. FAQ 8개 글(2276·2301·2360)이 7개 글보다 높게 나오던 문제(옛 20점 대 10점)는 이제 같은 점수다.

## 글별 점수

| ID | 세트 | 그룹 | 옛 도구 총점 | 새 도구 총점 | 말투 제외(/80) | rules | 질문 소제목 | FAQ(개수) | 길이 | 말투 | 플래그 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1916 | 고친 4편 | C | 77 | 75 | 75 | 40 | 15 | 10 (2) | 10 | 0 | 없음 |
| 1919 | 고친 4편 | A | 93 | 96 | 78 | 40 | 18 | 10 (4) | 10 | 18 | 없음 |
| 1925 | 고친 4편 | D | 73 | 69 | 69 | 40 | 14 | 10 (2) | 5 | 0 | 없음 |
| 2070 | 고친 4편 | C | 74 | 70 | 70 | 40 | 15 | 10 (5) | 5 | 0 | 없음 |
| 1944 | 비교용 | D | 10 | 25 | 25 | 15 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box |
| 1953 | 비교용 | D | 10 | 20 | 20 | 10 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 1974 | 비교용 | B | 12 | 22 | 22 | 10 | 2 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 1997 | 비교용 | D | 12 | 25 | 25 | 15 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box |
| 2011 | 비교용 | B | 10 | 20 | 20 | 10 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2055 | 비교용 | A | 13 | 23 | 22 | 10 | 2 | 0 (7) | 10 | 1 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2076 | 비교용 | D | 18 | 18 | 18 | 10 | 3 | 0 (6) | 5 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:6 opener checked_box closer |
| 2098 | 비교용 | B | 10 | 25 | 25 | 15 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box |
| 2125 | 비교용 | B | 15 | 30 | 30 | 15 | 5 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box |
| 2146 | 비교용 | A | 12 | 22 | 22 | 10 | 2 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2158 | 비교용 | D | 13 | 20 | 20 | 10 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2204 | 비교용 | A | 14 | 27 | 27 | 15 | 2 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box |
| 2225 | 비교용 | A | 10 | 20 | 20 | 10 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2255 | 비교용 | A | 8 | 16 | 16 | 10 | 0 | 0 (7) | 6 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2264 | 비교용 | A | 10 | 20 | 20 | 10 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2276 | 비교용 | A | 20 | 20 | 20 | 10 | 0 | 0 (8) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:8 opener checked_box closer |
| 2301 | 비교용 | A | 20 | 20 | 20 | 10 | 0 | 0 (8) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:8 opener checked_box closer |
| 2307 | 비교용 | A | 10 | 20 | 20 | 10 | 0 | 0 (7) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box closer |
| 2360 | 비교용 | A | 20 | 20 | 20 | 10 | 0 | 0 (8) | 10 | 0 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:8 opener checked_box closer |
| 2394 | 비교용 | C | 11 | 26 | 25 | 15 | 0 | 0 (7) | 10 | 1 | fixed_heading:30초 핵심 요약 fixed_heading:자주 묻는 질문 fixed_heading:같이 보면 좋은 글 faq_block:7 opener checked_box |
