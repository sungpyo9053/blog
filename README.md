# Hunt News Content Pipeline

복잡한 변화가 내 생활에 어떤 영향을 주는지 쉽게 설명하는 `Hunt News`의
검색 주제 기획부터 리서치, 글쓰기, 이미지 제작, 검수, WordPress 발행과
발행 후 Search Console·GA4 분석까지 수행하는 콘텐츠 운영 시스템입니다.

공개 사이트는 [huntlab.app](https://huntlab.app/)을 유지하며 기존 URL, 글,
미디어와 검색 색인을 보존합니다.

## 구성

- `agents/`: Planner, Researcher, Writer, Image Maker, Assembler, Reviewer,
  Publisher, Analytics Optimizer 역할별 지침
- `guides/`: 문체, Google SEO, 이미지, 발행, 분석·수익화 정책
- `publisher/`: WordPress REST API 검증·업로드·발행 모듈
- `scripts/run_daily_pipeline.py`: TOP2 실행 Harness
- `tests/`: 단계 간 계약과 Publisher 회귀 테스트
- `output/runs/[run_id]/[topic_id]/`: 격리된 실행 산출물(Git 제외)
- `output/runs/[run_id]/news-worthiness-shadow.json`: legacy TOP2와 비교하는 비발행 Shadow 랭킹 산출물

## Workflow

1. Topic Planner → 카테고리 할당 없이 후보 35개 이상, TOP10, TOP2
2. Research Agent → `research.md`
3. Writer Agent → `draft.md`
4. Image Maker Agent → 대표 이미지와 본문 이미지
5. Assembler Agent → `final.md`, `final.html`
6. Reviewer Agent → `publish.md`, 승인 SHA-256
7. Publisher Agent → WordPress 공개 발행과 감사 로그

Publisher만 외부 변경 권한을 가집니다. 승인 해시, run/topic/source 식별자,
카테고리·태그와 대표 이미지 계약이 모두 일치해야 공개 발행합니다.

### Topic Planner 선정 원칙

`생활`, `경제`, `부동산`, `사회`, `정치`, `문화·엔터`, `IT`를 활성 편집 범위로
사용하지만 카테고리별 후보 수나 TOP2 할당량을 강제하지 않습니다.
TOP2는 검색 수요, 공식 출처, HuntLab 적합성, 독창성과 실제 해결 가치를
기준으로 선정합니다. Harness는 실행 직전 공개 WordPress 카테고리 분포도 읽어
한 카테고리가 전체의 60%를 넘으면 그 카테고리의 균형 가산점을 제거합니다.
저대표 분야는 다른 품질 조건을 모두 통과한 경우에만 균형 점수를 우대하며,
카테고리 비율 때문에 약한 후보를 강제 발행하지 않습니다.
Google Trends 한국 RSS 수집기는 매시간 급상승 검색어, 대략적인
검색량, 발생 시각과 관련 기사를 48시간 캐시에 누적합니다. Planner는 이를 주력
시의성 신호로 사용하지만 관련 기사 자체를 사실 근거로 간주하지 않으며, 공식 원문
하나 또는 독립 출처 두 개 이상을 다시 확인합니다. 같은 검색 의도가 Search Console의
실제 HuntLab 검색어와 연결되면 적합성 가산점을 최대 1점만 적용합니다.

Whereispost 수집기는 2시간마다 소량의 키워드를 정상 브라우저
화면으로 조회해 PC·모바일 검색량, 총 검색량, 문서 수와 경쟁 비율을 캐시에 누적합니다.
광고 잠금이나 인증 실패가 발생하면 우회하지 않고 마지막 정상 캐시를 보존합니다.
Planner는 이 캐시를 장기 수요 참고값으로만 사용하며 캐시가 없거나 100회 미만이어도
공식 원문, 시의성, 생활 영향과 비중복 검색 의도가 충분하면 TOP2로 선정할 수 있습니다.

Planner는 Velog 공개 트렌딩과 기술 태그에서 반복되는 기술·언어·시스템
아키텍처 관심사를 한국 개발자 수요의 보조 신호로 참고합니다. 제목이나 구성을
복제하지 않으며 Search Console, 검색 의도, 공식 1차 자료와 HuntLab에서 직접
검증 가능한 고유 가치가 함께 확인될 때만 후보 평가에 반영합니다. Velog 접근이
실패하거나 반복 신호가 없더라도 일일 파이프라인은 중단하지 않습니다.

모든 새 글은 기존 WordPress `한눈에 보기` 자동 목차를 유지하면서 도입 직후에
별도의 `핵심 요약`을 둡니다. `무엇`, `왜`, `어떻게`를 근거가 확인되는 짧은
세 항목으로 작성하며 하나라도 빠지거나 본문에 없는 주장이면 Reviewer가
발행을 거부합니다.

WordPress 태그는 게시물당 재사용 가능한 3~4개만 허용합니다. 기존 태그를
우선하고 한 글에서만 쓰일 검색어 변형을 새 태그로 만들지 않습니다.

## 일일 실행

```bash
./.venv/bin/python scripts/run_daily_pipeline.py
```

추가 키워드는 선택적으로 전달할 수 있습니다.

```bash
./.venv/bin/python scripts/run_daily_pipeline.py --keywords "AWS,FastAPI"
```

외부 호출과 WordPress 변경 없이 Planner 계약, TOP2 파싱과 단계별 명령을
검증할 수 있습니다.

```bash
./.venv/bin/python scripts/run_daily_pipeline.py --dry-run
```

## 실패 실행 재개

완료된 단계는 재사용하고 TOP2 중 실패한 순위만 재개할 수 있습니다.

```bash
./.venv/bin/python scripts/run_daily_pipeline.py \
  --resume-run-id 20260728T170005Z-764b58d29d \
  --start-rank 2 \
  --limit 1
```

Reviewer가 `REJECTED`한 글은 자동 우회하지 않습니다. 사실·검색 의도 문제를
수정한 뒤 같은 run을 재개해야 하며, 이미 발행된 다른 순위 글은 변경하지
않습니다.

## Ubuntu 운영

다음 systemd unit을 사용합니다.

- `deploy/huntlab-daily-pipeline.service`
- `deploy/huntlab-daily-pipeline.timer`: 매일 02:00 KST, Trends·Search Console·Whereispost 캐시 참고
- `deploy/huntlab-google-trends-collector.service`
- `deploy/huntlab-google-trends-collector.timer`: 매시간 10분, 한국 급상승 RSS 누적
- `deploy/huntlab-whereispost-collector.service`
- `deploy/huntlab-whereispost-collector.timer`: 00:30부터 2시간 간격, 회당 3개 누적 수집
- `deploy/huntlab-daily-retry.service`
- `deploy/huntlab-daily-retry.timer`: 매일 17:00 KST 실패 점검
- `deploy/huntlab-analytics-optimizer.service`
- `deploy/huntlab-analytics-optimizer.timer`: 매일 01:00 KST
- `deploy/huntlab-news-worthiness-report.timer`: 2026-09-04 05:00 KST에 14일 Shadow 비교 리포트 1회 생성

서버 시간대는 `Asia/Seoul`로 설정합니다. Playwright를 처음 설치한 뒤에는
다음 명령으로 Chromium 런타임을 준비합니다.

```bash
.venv/bin/playwright install --with-deps chromium
```

17시 재시도는 당일 실패 실행을 점검하고 안전하게 재개할 수 있는 경우만
처리합니다. 정상 발행된 글을 다시 발행하지 않습니다.
뉴스·수집 타이머는 `Persistent=false`로 운영해 서버 재시작이나 타이머 재배포가
편집 창을 놓친 기사를 임의의 늦은 시간에 즉시 발행하지 않도록 합니다.
TOP2는 주제별 격리 디렉터리에서 준비 단계를 두 작업자로 병렬 실행합니다.
Humanize 상태 기록과 WordPress Publisher는 잠금으로 직렬화해 공유 상태 유실과
동시 발행 충돌을 막습니다. 필요하면 `--topic-workers 1`로 안전하게 직렬 실행할
수 있습니다.

Analytics Optimizer는 Search Console 데이터 지연과 API 호출 비용을 고려해
매일 01:00 KST에 한 번 실행합니다. 생성된 최신 리포트는 같은 날 02:00
Topic Planner가 읽습니다.

## Analytics·SEO Lifecycle

```bash
./.venv/bin/python scripts/run_analytics_optimizer.py
```

Search Console·GA4 읽기 전용 인증으로 `output/analytics/latest.md`를 만들고,
같은 실행에서 공개 `robots.txt`, Sitemap, `ads.txt`, 빈 카테고리, 깨진 내부 링크,
일반 작성자명과 대표 이미지·ALT도 읽기 전용으로 점검합니다.
정규 Harness가 해당 파일 경로를 다음 Planner와 Writer 프롬프트에 명시적으로
주입합니다. Agent가 분석 파일을 임의로 탐색하거나 Analytics Optimizer가
Daily Pipeline을 직접 호출하지 않습니다.
같은 보고서를 `output/analytics/YYYY-MM-DD.md`에도 저장해 일별 비교 기록을
보존하며, `latest.md`는 항상 다음 파이프라인이 읽을 최신 보고서로 유지합니다.
새 글은 발행 약 24시간, 72시간과 7일 뒤에 URL Inspection 읽기 검사를 한 번씩
받습니다. 하루 10개 점검 슬롯은 신규 체크포인트 6개와 검색 노출이 없는 성숙 글
회복 점검 4개로 우선 배분하고, 한쪽 큐가 비면 다른 쪽이 남는 슬롯을 사용합니다.
완료된 체크포인트는
`output/analytics/index-recovery-state.json`에 저장하고, 일시적인 API 실패는
완료로 기록하지 않아 다음 01:00 실행에서 재시도합니다. 검색 노출이 없는 성숙
글은 같은 10개만 반복하지 않고 7일 재검사 간격으로 순환하며, verdict·coverage·
indexing state·canonical·sitemap을 함께 저장합니다. 회복 대상의 관련 내부링크
출처 후보는 `output/analytics/index-recovery-queue.json`, 노출 30 이상·CTR 2%
미만·평균 순위 5~20위 글의 단일변수 실험 후보는
`output/analytics/ctr-experiment-queue.json`에 저장합니다. 두 큐는 검토용이며
공개 글을 자동 수정하지 않습니다. 일반 블로그 글을
Indexing API로 제출하지 않으며, 색인되지 않은 글에는 검토된 관련 글에서
문맥상 맞는 내부 링크 한 개만 추가할 수 있습니다.
분석 결과만으로 추가 발행이나 기존 글 Update를 실행하지 않습니다. 인증이
없거나 데이터가 부족하면 `INCOMPLETE` 또는 데이터 없음으로 기록하고 성과를
추정하지 않습니다.

홈은 히어로 바로 다음에 최신 글을 먼저 보여주고, 읽기 가이드와 분야별 탐색은
글 목록 뒤에 배치합니다. 모바일 히어로는 첫 최신 글이 더 빨리 보이도록 압축합니다.
GA4의 기본 참여 세션과 별도로 화면이 보이는 상태에서 30초 이상 머물고 본문의
25% 이상을 읽은 경우 `huntlab_engaged_read`를 한 번 기록하고, 본문이나 관련 글의
내부 링크 클릭은 `huntlab_internal_click`로 기록해 페이지뷰 → 실독 → 다음 글 이동
퍼널을 교차 확인합니다. 공개 전수 감사는 CDN 제한을 피하도록 요청 시작 간격, 지수
백오프와 제한된 동시성을 적용하며 일부 Sitemap을 읽지 못하면 `INCOMPLETE`로
실패시킵니다. AIOSEO JSON-LD의 Article 작성자·발행자와 WebSite
발행자는 `Hunt News 편집팀` Organization으로 통일합니다.

Topic Planner는 Keyword Cannibalization, 내부 링크 후보, Topic Cluster와
Pillar 후보를 기록합니다. Reviewer는 공개 URL, 앵커 문맥, 대표 이미지와
실제 경험 근거를 검증합니다.

AI 보조 사용, 주제별 근거 기준, 검수 방식과 발행 후 보강 원칙은
`guides/editorial-policy.md`에 공개 가능한 편집 정책으로 정리되어 있습니다.
하루 발행량보다 품질 게이트를 우선하며 기준 미달 글은 발행하지 않습니다.

## macOS Remote 유지

`deploy/com.huntlab.keepawake.plist`는 ChatGPT Remote 사용 중 Mac의 화면,
시스템과 디스크 절전을 막는 선택 설정입니다. 전원 연결 상태에서 사용하고,
덮개를 닫을 때의 잠자기는 별도 동작임에 유의합니다.

## 검증

```bash
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python -m py_compile scripts/*.py publisher/*.py
git diff --check
```

실행 산출물과 인증정보는 Git에 커밋하지 않습니다.
