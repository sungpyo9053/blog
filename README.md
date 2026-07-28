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

1. Topic Planner → 7개 카테고리 후보 35개 이상, TOP10, TOP2
2. Research Agent → `research.md`
3. Writer Agent → `draft.md`
4. Image Maker Agent → 대표 이미지와 본문 이미지
5. Assembler Agent → `final.md`, `final.html`
6. Reviewer Agent → `publish.md`, 승인 SHA-256
7. Publisher Agent → WordPress 공개 발행과 감사 로그

Publisher만 외부 변경 권한을 가집니다. 승인 해시, run/topic/source 식별자,
카테고리·태그와 대표 이미지 계약이 모두 일치해야 공개 발행합니다.

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
- `deploy/huntlab-analytics-optimizer.timer`: 매시간

서버 시간대는 `Asia/Seoul`로 설정합니다. Playwright를 처음 설치한 뒤에는
다음 명령으로 Chromium 런타임을 준비합니다.

```bash
.venv/bin/playwright install --with-deps chromium
```

12시 재시도는 당일 실패 실행을 점검하고 안전하게 재개할 수 있는 경우만
처리합니다. 정상 발행된 글을 다시 발행하지 않습니다.

## Analytics·SEO Lifecycle

```bash
./.venv/bin/python scripts/run_analytics_optimizer.py
```

Search Console·GA4 읽기 전용 인증으로 `output/analytics/latest.md`를 만들고,
저CTR Refresh 후보와 Content Gap 후보를 다음 Planner에 전달합니다.
분석 결과만으로 추가 발행이나 기존 글 Update를 실행하지 않습니다. 인증이
없거나 데이터가 부족하면 `INCOMPLETE` 또는 데이터 없음으로 기록하고 성과를
추정하지 않습니다.

Topic Planner는 Keyword Cannibalization, 내부 링크 후보, Topic Cluster와
Pillar 후보를 기록합니다. Reviewer는 공개 URL, 앵커 문맥, 대표 이미지와
실제 경험 근거를 검증합니다.

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
