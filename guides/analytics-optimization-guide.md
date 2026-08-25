# HuntLab Search·Analytics 수익화 최적화 가이드

이 문서는 HuntLab의 독립 분석 사이클이 Search Console과 Analytics 데이터를 읽고,
다음 콘텐츠 사이클에 전달할 개선 제안을 만드는 운영 기준이다. Daily Pipeline과
Publisher 정책을 대체하거나 자동 발행 권한을 부여하지 않는다.

## 최상위 원칙

- 검색자의 문제를 해결하는 콘텐츠가 수익화보다 항상 우선한다.
- 관측된 데이터와 해석·가설을 구분한다.
- 표본이 부족한 1시간 데이터만으로 결론을 내리지 않는다. 가능하면 24시간·7일 누적값을 함께 본다.
- CTA 변경은 검색 의도를 해결한 뒤에만 제안한다.
- 분석 Agent는 글을 수정하거나 WordPress에 공개 발행하지 않는다.
- 분석 결과만으로 Daily Pipeline을 추가 실행하지 않는다. 신규 글보다 기존 글
  Refresh를 우선하고 다음 정규 Planner 실행에 근거를 전달한다.

## 입력

- Search Console 검색어·노출수·클릭수·CTR·평균 순위
- Analytics 페이지뷰·유입 경로·참여 시간·이탈 또는 참여율·전환 이벤트
- 공개 글의 URL·제목·카테고리·기존 CTA
- 확인 기간, 측정 ID, 사이트 URL

### 선택적 Naver·Whereispost Shadow Mode

- 네이버 서치어드바이저는 소유자가 내보낸 데이터 또는 공식 지원 API만 입력으로
  사용한다. 일반 성과 데이터 API가 확인되지 않은 상태에서 로그인 화면을 자동
  조작하거나 내부 요청을 역공학하지 않는다.
- Whereispost 키워드마스터는 공식 자동화 API와 허용 조건이 확인되기 전까지
  화면을 크롤링하지 않는다. 소유자 또는 소유자의 요청을 수행하는 승인된 운영자가
  공식 UI에서 직접 확인해 제공한 JSON만 읽는다. Daily Pipeline에 명시적으로
  전달한 행은 동일한 `primary_keyword`의 수요 검증에만 사용할 수 있으며, 자동
  선정이나 정책·가격·시점의 사실 근거로 사용하지 않는다.
- 입력 경로는 각각 `NAVER_SEARCHADVISOR_EXPORT`,
  `WHEREISPOST_SHADOW_EXPORT` 환경 변수로 전달한다. 예시는
  `config/search-signals/`에 있으며 실제 내보내기 파일과 인증정보는 Git에 넣지
  않는다.
- 데이터가 없으면 `0`이 아니라 `N/A`로 보고한다.

인증정보는 환경 변수 또는 승인된 Secret Store에서만 읽고 로그에 출력하지 않는다.

## 분석 기준

- 성과 진단 언어는 `INDEXING → IMPRESSION → CLICK → ENGAGEMENT`로 통일한다.
- `0`은 측정했으나 발생하지 않은 값, `N/A`는 측정 자체가 없거나 연결할 수 없는
  값이다. 둘을 상호 변환하거나 결측치를 학습용 0으로 대체하지 않는다.
- Search Console의 impression→click과 GA4의 page_view→engaged_read는 서로 다른
  데이터 소스와 집계 기준을 사용하므로 동일 모집단의 연속 전환율로 계산하지 않는다.
- INDEXING은 당일 완료된 Search Console URL Inspection 표본만 집계한다. 완료된
  표본이 없으면 `N/A`, 완료된 표본에서 색인 건수가 없으면 `0`으로 둔다. 표본
  수와 `indexed`·`not_indexed`·`inconclusive`를 함께 표시하며 전체 발행 글의
  색인율로 확대 해석하지 않는다.
- URL Inspection의 `NEUTRAL`은 일괄 `inconclusive`로 처리하지 않는다. Coverage가
  `발견됨 - 현재 색인이 생성되지 않음`, `크롤링됨 - 현재 색인이 생성되지 않음`,
  `Google에는 아직 알려지지 않은 URL`처럼 미색인을 명시하면 `not_indexed`로
  분류하고, Coverage로 상태를 확정할 수 없을 때만 `inconclusive`로 둔다.
- 노출은 높고 CTR이 낮으면 제목·Meta Description 개선안을 제안한다.
- 클릭은 있으나 참여가 낮으면 첫 화면·목차·내부 링크 개선안을 제안한다.
- 검색 의도와 CTA가 어긋나면 CTA를 관련 글·공식 문서·무료 체험·문의 중 하나로 조정한다.
- 전환 데이터가 없으면 전환이 있었다고 추정하지 않는다.
- 상업 키워드는 가격·조건·제휴 여부를 공식 자료와 확인일로 검증한다.
- 수익·투자·성과를 보장하는 표현과 숨겨진 제휴 유도는 금지한다.

## 출력

`output/analytics/latest.md`에 다음을 기록한다.

- 수집 시각과 분석 기간
- 데이터 출처 및 표본 수
- 상위 유입 검색어와 페이지
- CTR·참여·전환 관측값
- 확정 사실과 가설의 구분
- 우선순위가 있는 CTA·제목·내부 링크 제안
- 다음 Planner/Writer 사이클에 전달할 검색 의도와 상업 키워드
- URL별 Refresh 후보와 관측 근거
- 기존 글로 해결되지 않는 Content Gap 후보
- 신규 6개·성숙 회복 4개를 우선 배분한 URL Inspection 점검 결과
- `index-recovery-queue.json`의 문맥상 관련 내부링크 출처 후보
- URL 인코딩 표현이 달라도 동일 경로의 최신 Inspection 상태를 연결하고, 이미
  `PASS`인 URL은 색인 회복 큐에서 제외한다.
- `ctr-experiment-queue.json`의 제목 또는 Meta 단일변수 실험 후보
- GA4 `page_view` → `huntlab_engaged_read` → `huntlab_article_complete`와
  `huntlab_internal_click`·`huntlab_article_share`·`huntlab_return_visit` 관측값
- `internal_click / engaged_read`는 서로 다른 이벤트 횟수의 비율이므로 백분율
  전환율이 아니라 `읽기 이벤트당 내부 클릭 이벤트 수`로 표시한다.
- `hunt-news-performance-funnel.v1` 책임 단계와 `0`/`N/A` 의미
- 계측 입력이 없으면 `N/A`, 계측됐으나 발생하지 않으면 `0`
- 데이터 부족·API 실패·측정 누락

분석 결과는 다음 글쓰기 사이클에서 참고 자료로 제공할 수 있지만, 기존 Guide의
정책이나 Reviewer 승인 계약을 변경하지 않는다.

전달 책임은 정규 Harness에 있다. Harness는 Planner와 Writer 호출 프롬프트에
`output/analytics/latest.md` 경로를 명시적으로 제공하며, Analytics Agent가
Daily Pipeline을 직접 호출하거나 암묵적인 전역 컨텍스트를 변경하지 않는다.

## WordPress 운영 경계

- WordPress 공개 글·Draft·카테고리·태그는 읽기만 한다.
- 공개 사이트 감사는 `robots.txt`, Sitemap, `ads.txt`, 빈 카테고리, 내부 링크,
  canonical, 작성자명과 대표 이미지·ALT를 읽기 전용으로 점검한다. 감사 실패는
  Search Console·GA4 수집을 막지 않으며 WordPress를 자동 수정하지 않는다.
- 설정 변경은 관리자가 명시적으로 승인한 항목만 수행한다.
- SEO 플러그인, Sitemap, 공개성, 퍼머링크를 추측해 변경하지 않는다.
- 분석 Agent는 Publisher를 호출하지 않는다.

## 오류와 로그

API 인증·네트워크·쿼리 오류를 구분해 `logs/analytics-YYYY-MM-DD.log`에 기록한다.
부분 데이터는 성공으로 가장하지 않고 `INCOMPLETE`로 표시한다.

## Refresh와 Content Gap

- 노출 50 이상이며 CTR 2% 미만인 URL은 제목·Meta Description·첫 화면 검토
  후보로 표시한다. 이는 자동 수정 기준이 아니라 검토 큐다.
- 노출 30 이상, 클릭 0, 평균 순위 8위 이하 질의는 Content Gap 후보로 표시한다.
- 같은 검색 의도의 기존 글이 있으면 신규 글보다 해당 글 보강을 우선한다.
- Refresh는 원문 사실 재검증, 변경일 기록, Reviewer 재승인과 Publisher의
  명시적 update 권한 없이는 공개 글을 변경하지 않는다.
