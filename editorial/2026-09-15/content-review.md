# 기존 핵심 글 편집 검토 — 2026-09-15

범위: 비공개 WordPress 백업 `output/audits/adsense-20260915/wordpress-backup.json`의 공개 글 9건 본문 전체와 관련 저장소 코드를 대조했다. WordPress 쓰기·서버 변경은 수행하지 않았다. 아래 HTML은 기존 ID 업데이트용 편집본이며, 공개 반영과 렌더링 QA는 별도 단계다. 실제 승인 확률을 계산한 문서가 아니다.

## 글별 판단

| ID | 독립적으로 남길 가치 | 변경 |
| --- | --- | --- |
| 50 | 날짜형 Retry-After가 float 파싱을 깨는 동일 입력 비교. 30초 상한·지터·POST 중복 한계까지 명시 | 유지. 역사 테스트와 현재 재실행을 혼동하지 않았고 과장된 운영 장애 주장 없음 |
| 96 | 내부 링크 대량 수정의 읽기/쓰기 경계, 원문 백업, 부분 실패와 복원 차이 | 구어적 군더더기 정리, 반복 FAQ 삭제, 관련성이 떨어지는 2개 추천 링크 제외. 11개 소스/타깃2개가 7월29일 역사범위임을 명시. 공개 고정 코드 링크 추가 |
| 132 | 실제 100+19개 누락 관측과 백업 ID 대조. 전체 수집과 변경 대상 집합의 분리 | 119개를 현재 게시물 수로 오독하지 않도록 명시. 정확히 100의 배수인 마지막 페이지는 특정 invalid-page 코드만 처리하며 X-WP-TotalPages 방식도 설명 |
| 290 | 같은 Fake Client 경계에서 태그 한 개 차이로 create 허용/차단 비교 | 공개 고정 테스트 링크와 설치·실행 명령 추가. fake payload를 실제 WordPress 응답으로 확대하지 않음 |
| 301 | 실제 중복 H2와 자동 상자를 구분해 센 운영 회고 | 같은 내용의 '한눈에 보기' 두 번째 요약 삭제. 고정 변경 커밋 링크, 다른 사이트의 원문/렌더 분리 진단 절차 추가. 과거 PHP 미검증·배포 실패 사실 유지 |
| 373 | missing artifact를 process success와 분리하고 한 번만 재시도하는 계약 | 사라진 운영 output 디렉터리 의존 제거. 시스템 임시 디렉터리로 예제 실행 가능하게 수정. agent 파일 경로 정정. 현재는 validation_error 경로도 있으므로 누락 전용 설명을 역사범위로 표시. 미공개 운영 로그의 셸 명령은 당시 관측임을 유지 |
| 698 | HTTP200 HTML을 정상 JSON과 같은 검사기로 비교하는 통제 실험 | JSON ID 양의 정수/기존 대상 기대ID 구분. 발췌 코드만으로 null·배열·bool 처리가 완전하지 않음을 경고. 재현 전 설치 절차 추가 |
| 699 | noindex와 sitemap을 URL집합으로 교차 검사하는 통제 실험 | self-canonical 검사는 HuntLab 대표 문서 목록의 자체 규칙이며 Google의 보편 필수조건이 아님을 정정. 공식 canonical 문서 링크, 입력 작성과 설치 안내 추가 |
| 706 | 무발행 정상 종료, dry-run 소비방지, 일일 한도와 발행 단계 분리 | 초기 '공개 감사 뒤 checkpoint' 설명을 역사 구현으로 표시. 현재 발행 확인→checkpoint→공개 감사 순서와 중복발행 방지 이유를 별도 보정 절로 기록. 기존 11개 테스트 로그·해시·측정 범위는 변경하지 않음 |

## 실제 확인

- 373 편집 HTML의 Python heredoc을 추출해 현행 저장소에서 실행: `missing_twice`는 의도된 PipelineError, `created_on_retry`는 호출2회와 파일 생성, 최대2회 계약 assertion 모두 통과. 실제 Planner subprocess/WordPress/서버 호출은 없음.
- 290 성공/실패 테스트2개와 50 Retry-After 회귀 테스트3개를 현재 로컬 가상환경에서 실행: 총5개 통과. 이는 역사 본문에 실린 실행시간을 새로 측정한 값으로 치환하지 않았다.
- 8개 편집 HTML의 GitHub 고정근거와 저장소 링크17개를 비로그인 HTTP GET 확인: 모두200. 200은 링크 가용성 증거이며 실험 재실행이나 사실성 전체 보장을 뜻하지 않는다.
- HTML 파싱, pre/table 태그 짝, 비밀키 표식 검사 통과. 원문 pre 블록은373의 의도적인 실행예제 수정1개를 제외하고 모두 그대로 유지했다. 새 실행명령290과 현재 흐름706은 추가했다.
- WordPress pagination 공식 문서와 Google canonical 공식 문서를 직접 열어 의미 대조: https://developer.wordpress.org/rest-api/using-the-rest-api/pagination/ 및 https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls

## 공개 전 남은 확인

- ID/slug/date를 유지하는 update만 적용하고 전체 백업을 보존할 것.
- 역사 이미지·로그를 2026-09-15 신규 측정이라고 표시하지 않을 것. original publication date와 수정일을 구분할 것.
- 관련 글을 archive/draft 처리하면8개 편집본의 내부 링크도 최종 공개 목록과 다시 대조할 것.
- 132 코드는 역사 알고리즘이라 범용 production drop-in으로 추천하지 않음. 96 역시 기존 고정 링크 그래프를 현 사이트에 apply하는 사용법으로 안내하지 않음.
- 698와699에는 mock/fixture 라벨을 유지. 실제 서비스 장애나 WordPress 쓰기 결과로 재포장하지 않음.
- 이 검토는 편집 내용·로컬 실행 결과이며 공개 사이트 QA, Reviewer 승인, AdSense 검토 결과와 구분한다.

## 편집본 승인 판정과 고정 해시

판정: **APPROVED — 아래8개 HTML의 기존 글 본문 업데이트 승인**. 역사 수치·로그와2026-09-15 코드 보정을 구분했고, 새로운 운영 실험결과나 발행성과를 만들어 넣지 않았다. 콘텐츠 정확성 관점의 미해결 차단 항목은 없다. 단, 공개 화면·내부 링크·도구 기능은 배포 뒤 확인이 필요하며 이는 AdSense 승인 판정이 아니다.

후속 처리 범위: 최종 공개9개 밖의 링크에서 앵커를 해제하고 표시본문을 남기는 처리, 과거 자동 related 섹션 제거,50/132/698의 새 로컬 도구 연결은 별도 최종 렌더 결과를 검토한다. 해당 처리가 파일 본문을 변경하면 아래 해시의 승인 대상과 다르므로 최종 산출물 해시와 변경 내역을 배포 기록에 따로 남긴다. 새 파이프라인 변경은 독립 글 수 채우기에 쓰지 않고706의 범위가 좁은 후속 보정으로만 연결하는 것이 적합하다.

```text
38c198626bfc5f6a0a96ec419def44fc514e0ecdc3b648a3712eef42de9639c4  post-132.html
1b63a5230c5e4972dcf73ee0714655b58b9f458a2965583d07ba49ec998c32ee  post-290.html
bea24af8ee15d051fa13c376c295df4ea2029a4da98c9df190c1d2f8a463e9f7  post-301.html
c9b160dbf179175922d111a550eb47c8c200cc5fb827eb03a2f2cc3e5cda233d  post-373.html
2c7622ffc35e2a3a1af83c1cff2ce21974ac772125e4afc8ef22f29290ea8d76  post-698.html
416bd9987fd313d53ad155e2bfde09f05120f0f32209f9319618936ccee9fda3  post-699.html
db2def0749422ea3e720e0dbfde03dec85bef98f97b411e05eca23800493e73b  post-706.html
4d39c243501453b4c090616c9bb224a77c969da9661c32b138c1e652c1a3f25c  post-96.html
```
