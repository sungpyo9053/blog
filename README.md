# HuntLab Blog Content Pipeline

검색 주제 기획부터 리서치, 글쓰기, 이미지 제작, 검수, WordPress 발행과
발행 후 Search Console·GA4 분석까지 수행하는 콘텐츠 운영 시스템입니다.

## 구성

- `agents/`: Planner, Researcher, Writer, Image Maker, Assembler, Reviewer,
  Publisher, Analytics Optimizer 역할별 지침
- `guides/`: 문체, Google SEO, 이미지, 발행, 분석·수익화 정책
- `publisher/`: WordPress REST API 검증·업로드·발행 모듈
- `scripts/run_daily_pipeline.py`: TOP2 실행 Harness
- `tests/`: 단계 간 계약과 Publisher 회귀 테스트
- `output/runs/[run_id]/[topic_id]/`: 격리된 실행 산출물(Git 제외)

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

`Tech`, `AI`, `Economy`, `Society`, `Politics`, `Hot Issue`, `Build Log`를
편집 범위로 사용하지만 카테고리별 후보 수나 TOP2 할당량을 강제하지 않습니다.
TOP2는 검색 수요, 공식 출처, HuntLab 적합성, 독창성과 실제 해결 가치를
기준으로 선정하므로 기술 주제 두 개만 선택할 수 있습니다. 비기술 후보는
해당 카테고리의 강화된 출처 규칙과 동일한 품질 기준을 통과할 때만 경쟁합니다.

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
- `deploy/huntlab-daily-pipeline.timer`: 매일 02:00 KST
- `deploy/huntlab-daily-retry.service`
- `deploy/huntlab-daily-retry.timer`: 매일 12:00 KST 실패 점검
- `deploy/huntlab-analytics-optimizer.service`
- `deploy/huntlab-analytics-optimizer.timer`: 매일 01:00 KST

서버 시간대는 `Asia/Seoul`로 설정합니다. Playwright를 처음 설치한 뒤에는
다음 명령으로 Chromium 런타임을 준비합니다.

```bash
.venv/bin/playwright install --with-deps chromium
```

12시 재시도는 당일 실패 실행을 점검하고 안전하게 재개할 수 있는 경우만
처리합니다. 정상 발행된 글을 다시 발행하지 않습니다.

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
분석 결과만으로 추가 발행이나 기존 글 Update를 실행하지 않습니다. 인증이
없거나 데이터가 부족하면 `INCOMPLETE` 또는 데이터 없음으로 기록하고 성과를
추정하지 않습니다.

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
