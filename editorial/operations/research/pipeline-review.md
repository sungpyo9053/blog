# 글 파이프라인 점검: 스타일 규칙이 자동으로 지켜지는가 (11/28, 개발 담당, 읽기 전용 점검)

목표: "네이버 파워블로거 수준" 규칙(editorial/guide/ko-life-style-v1.md, en-style-v1.md, research/style-v1-rules.md)이 사람 손을 거치지 않아도 지켜지게 하는 것.
결론부터: **지금은 공개 전에 막는 자동 장치가 없다.** 규칙을 지키는 장치는 사람이 해야 하는 일과 하나(매일 출근 때 48시간 안 공개 글 점검)뿐이다. 세션이 멈추면(10/20~24, 11/08~13에 실제로 멈춤) 옛 틀 그대로 공개된다.

## 1. 지금 흐름 (실측)

| 단계 | KO 생활 글 | EN ROS 글 | 러너 자동 글(피지컬 AI KO + EN판) |
|---|---|---|---|
| 글감·조사 | Claude 세션이 직접: `editorial/life/<날짜-slug>/research.md`, `evidence/`, `tools/txt.py` | Claude 세션: `editorial/en/<날짜-slug>/evidence/` | `run_evidence_deep_article.py --prepare-only` (02:02·14:02 타이머) → Research/Writer/Reviewer 에이전트, `english_edition.write_english` |
| 본문 | 직접 쓴 `ko.html` + `meta.json`. 일부 글은 `tools/build.py`가 `ko.template.html`/`ko.src.html`에서 `ko.html`을 다시 만든다 | 직접 쓴 `article.html` + `meta.json` | `publish.md` → 품질 게이트(`editorial_gate`, 99점 리뷰) |
| 예약 | `~/huntlab-ops/sched_life.sh <폴더>`: im-not-ai shim(`route_hint` 출력만 하고 막지 않음) → 러너 `/tmp/newpost.py`로 WP `future` → 렌더 검사 → `make_info_cards.py`(대표 카드 자동) → `wp_id.txt` | `~/huntlab-ops/sched_en.sh <폴더> <시각>`: WP `hunt_en future` → 렌더 검사 → 대표 카드 → `wp_id.txt` | `schedule_editorial_queue.py`(5분 타이머, **지금 꺼져 있음**, 12/02 재개 예정) → 10:00 칸 + EN판 |
| 공개 | WP 코어 cron `publish_future_post` + 백업 타이머 `huntlab-wordpress-future`(1분마다 `publish-due-future.php`). **두 경로 모두 본문 검사 없음** | 같음 | 같음 |
| 공개 후 | IndexNow는 mu-plugin이 공개 순간 자동. 표 그림은 퇴근 때 수동 `glance_new.sh ko/en`(export → `make_glance_figures.py` → `glance_insert.php`, 첫 H2 앞). 섹션 카드 `make_summary_cards.py`는 cards.json을 손으로 써야 하는 수동 | 같음 | 같음 |
| 공개 뒤 수정 | `~/huntlab-ops/imp.php`(WP 본문 직접 치환). **로컬 ko.html에는 다시 반영 안 함** | 같음 | 큐 행은 sha 검사로 수정 시 실패 |

현재 재고(11/28): KO 예약 85편(12/02~12/25, 공개 멈춤 중), EN 예약 75편(매일 10:00 공개 중).

## 2. 실측: 지금 예약 글이 규칙을 통과하는가

- KO 로컬 `ko.html` 242편 전부 `audit_content_repetition.py --files`에서 FLAG(30초 핵심 요약·자주 묻는 질문·같이 보면 좋은 글·FAQ 7개·자료 확인일·첫 문장 틀).
  - 고친 #1916·#2070·#1919·#1925도 로컬은 FLAG다 → 고친 내용은 WP에만 있고 로컬은 옛 틀. 로컬 파일로 검사하면 틀린 결과가 나온다.
- EN 로컬 `article.html` 109편 전부 `style_score EN` 80점 미만(64~73점). 109/109편에 `fixed_heading:FAQ`·`faq_exactly_5`, 23편에 `Short answer` 첫 문장. 이 중 75편이 이미 WP 예약돼 매일 1편씩 공개된다.

## 3. 자동으로 안 지켜지는 곳 (빈틈)

| # | 빈틈 | 근거 | 영향 |
|---|---|---|---|
| G1 | **공개 직전 검사가 없다.** WP 코어 cron과 `publish-due-future.php` 둘 다 본문을 보지 않고 공개한다. 점검은 출근 때 사람이 하는 일과뿐이고, 검사 대상 본문을 꺼내는 스크립트도 없다(plan 0-c "본문 export"는 손으로) | deploy/huntlab-publish-due-future.php, revenue-200-plan.md "공개 전 스타일 점검 일과" | 세션이 하루만 멈춰도 KO 4편·EN 1편이 옛 틀로 공개된다. EN은 지금도 매일 그렇다 |
| G2 | **예약 전 검사가 없다.** `sched_life.sh`·`sched_en.sh`에 lint가 없다. shim은 `route_hint`만 출력한다. 지침에는 "신호 0이어야 예약"이라고 써 있지만 코드가 막지 않는다 | ~/huntlab-ops/sched_life.sh 9~10행, sched_en.sh | 새 글을 옛 글 복사로 쓰면 그대로 예약된다(로컬 242편 전부 옛 틀이라 복사 원본이 전부 옛 틀) |
| G3 | **점수 기준이 코드에 없다.** `style_score.py`는 점수와 상관없이 항상 exit 0이고 파일 이름만(`article.html`) 출력해서 여러 편을 돌리면 어느 글인지 모른다. KO는 주제 글자(A~D)가 필요해 자동 예약 스크립트에 끼우기 어렵다 | scripts/style_score.py main() | "EN ≥80" 규칙을 스크립트로 강제할 수 없다 |
| G4 | **러너 EN판 지시문에 스타일 지침이 없다.** `english_edition._prompt`는 en-style-v1.md를 언급하지 않고, 재시도 게이트도 측정값 블록만 본다. 연구 단계 지시문(agents/researcher.md 156·307행)은 "FAQ 후보 최소 3개"를 요구해 "FAQ 0개 허용" 규칙과 충돌한다 | scripts/english_edition.py 12~36·58~69행, agents/researcher.md | 12/02 러너 예약 재개 뒤 EN판은 FAQ·고정 소제목 틀로 나올 수 있다 |
| G5 | **옛 틀을 다시 만드는 곳.** ① `tools/build.py` 4편이 옛 틀 원본(`ko.template.html`/`ko.src.html`, 각 6곳)에서 ko.html을 다시 만든다 ② 고친 글의 로컬 ko.html이 옛 틀이라 다시 예약·복원·복사하면 옛 틀이 돌아온다 ③ 내부 링크 스크립트 `rel1120b.php`는 "같이 보면 좋은 글" H2 글자를 찾아 링크를 넣고, `rel1073.php` 방식은 그 H2를 새로 만든다 → 소제목을 바꾼 글에는 링크가 조용히 빠지거나, 옛 H2가 다시 생긴다 ④ `backfill_internal_links.py`는 "함께 읽으면 좋은 글" 고정 H2를 넣는데 lint 목록(FIXED_HEADINGS)에 없다 ⑤ 크론 SSOT 지시문 WORK-START에 "공식 출처·확인일·직접 계산"이라고 쓰여 있어 "자료 확인일" 상자를 다시 넣게 만든다 | 각 파일, revenue-200-plan.md WORK-START | 고친 글이 다음 수정 때 되돌아간다 |
| G6 | **그림 단계가 수동이다.** 표 그림 `glance_new.sh`는 퇴근 세션에서만 돌고(KO는 공개 뒤에만), 섹션 카드는 cards.json을 손으로 써야 한다. 그림은 규칙 5번에서 필수가 아니라서 공개를 막을 일은 아니다. 대표 카드는 예약 때 자동이다 | glance_new.sh, make_summary_cards.py | 세션이 멈추면 그림이 빠질 뿐 틀이 생기지는 않는다(낮음) |
| G7 | (잠복) 옛 일반 콘텐츠 유형은 `## 20초 핵심 요약`을 강제한다(run_daily_pipeline.py 914~925·1647~1675행, agents/writer.md 105행). 지금 러너는 evidence_deep_article·foundation_concept만 만들어 이 분기를 타지 않는다 | run_evidence_deep_article.py 214행 | 지금 영향 없음. 옛 TOP2 경로를 되살릴 때만 문제 |

## 4. 제안: 가장 작은 변경 (기존 스크립트 재사용, 짧은 diff 순)

우선순위는 효과 순이다. C1·C2가 "자동으로 지켜짐"의 핵심이고, 나머지는 막힌 곳 정리다.

### C1. 공개 직전 보류 (G1 해결) — 서버 변경, 사용자 승인 필요
러너의 기존 15분 타이머(`huntlab-operations-watchdog`)에 한 줄을 더해 **1시간 안에 공개될 예약 글**을 검사한다. 걸리면 `pending`(검토 대기)으로 돌리고 카톡을 보낸다. 규칙은 기존 함수(`template_flags`, `score_en`)를 그대로 써서 규칙이 두 군데로 갈라지지 않는다. 비교용 글은 ko81-queue.md의 "비교용" 행을 읽어 빼므로 실험이 깨지지 않는다.
PHP(WP 공개 경로)를 고치지 않는 이유: 공개 경로가 코어 cron과 타이머 둘이라 PHP에서 막으려면 코어 훅을 갈아 끼워야 하고, 규칙을 PHP로 한 번 더 써야 한다.

새 파일 `scripts/hold_unstyled_future.py`(약 30줄):
```python
EXEMPT = {int(i) for i in re.findall(r"^\| \d+ \| (\d+) \|[^|]*\|[^|]*\| 비교용", KO81.read_text(), re.M)}
for kind in ("posts", "hunt_en"):
    for p in client.request("GET", f"{kind}?status=future&context=edit&orderby=date&order=asc&per_page=20&_fields=id,date_gmt,content"):
        if parse(p["date_gmt"]) - now > timedelta(hours=1) or p["id"] in EXEMPT: continue
        raw = p["content"]["raw"]
        bad = template_flags(raw) if kind == "posts" else ([] if score_en(raw)["total"] >= 80 else score_en(raw)["flags"] or ["score<80"])
        if bad and apply:
            client.request("POST", f"{kind}/{p['id']}", payload={"status": "pending"}); send(f"[공개 보류] #{p['id']} {' '.join(bad[:3])}", os.environ["MCPORTER_BIN"])
```
`deploy/huntlab-operations-watchdog.service`:
```diff
+ExecStart=-/home/ubuntu/apps/huntlab-blog/.venv/bin/python scripts/hold_unstyled_future.py --apply
  ExecStart=/home/ubuntu/apps/huntlab-blog/.venv/bin/python scripts/operations_watchdog.py --apply
```
(`-`를 붙여 보류 스크립트가 실패해도 감시는 돈다.) 고친 뒤 되살리기: `wp post update <id> --post_status=future --post_date=<원래 시각>`.
- 위험: **EN 75편이 모두 80점 미만이라 켜는 즉시 EN 매일 공개가 멈춘다.** 12/02 KO 재개 때도 "고침" 대상인데 아직 안 고친 글은 모두 보류된다(규칙대로지만 하루 공개 수가 줄 수 있음). 러너 10시 큐 글을 보류하면 `schedule_editorial_queue.py`가 `scheduled_post_state_changed`로 시끄럽게 실패한다(조용히 넘어가지 않으니 수용 가능).
- 권장 도입 순서: KO는 바로 `--apply`, EN은 처음 1~2주 `--warn-en`(카톡만, 보류 안 함)으로 두고 EN 고치는 속도(하루 1편)가 공개 속도를 따라잡으면 보류로 바꾼다. 결정은 사용자.
- 서버: 러너 서비스 파일과 새 스크립트 배포 → **사용자 승인 필요**(이미 받은 "글 생성 지시문 변경" 승인 범위가 아님).
- 테스트 `tests/test_hold_unstyled_future.py`: ① 옛 틀 KO 본문 + 30분 뒤 → 보류 ② 같은 본문 + 비교용 ID → 통과 ③ 3시간 뒤 → 건너뜀 ④ ko81 표 한 줄에서 비교용 ID를 뽑는지. WordPressClient는 가짜 객체로.

### C2. 예약 전 검사 (G2·G3 해결) — 로컬, 서버 아님
`scripts/style_score.py` main:
```diff
-    for f in files:
+    low = 0
+    for f in files:
         r = score(topic, Path(f).read_text(encoding="utf-8"))
+        low += topic == "EN" and r["total"] < 80
-        print(f"... {Path(f).name} ...")
+        print(f"... {f} ...")
-    return 0
+    return 1 if low else 0
```
`~/huntlab-ops/sched_life.sh`의 `wp_id.txt` 검사 바로 아래:
```bash
(cd $HOME/blog && .venv/bin/python scripts/audit_content_repetition.py --files $L/ko.html) || { echo "HOLD: style lint"; exit 1; }
```
`~/huntlab-ops/sched_en.sh` 같은 위치:
```bash
(cd $HOME/blog && .venv/bin/python -m scripts.style_score EN $L/article.html) || { echo "HOLD: EN style <80"; exit 1; }
```
- 위험: 낮음. 옛 틀 글을 새로 예약하려 하면 막힌다(의도한 동작). 비교용 글은 이미 예약돼 있어 다시 예약할 일이 없다.
- 서버: 아님(맥 쪽 스크립트).
- 테스트: `tests/test_style_score.py` — 옛 틀 EN(FAQ 5개 + "Short answer") 파일로 `main(["EN", f]) == 1`, 깨끗한 파일로 `== 0`.
- 참고: KO에 style_score 점수 기준을 넣지 않는 이유 — 주제 글자(A~D)가 meta.json에 없고, 말투는 판결상 선택 실험이라 점수로 막으면 안 된다. KO는 신호 0(template_flags)만 막는다.

### C3. 러너 EN판 지시문 + 게이트 (G4 해결) — 러너 코드, 승인 범위 안("글 생성 지시문 변경")
`scripts/english_edition.py`:
```diff
  def _prompt(...):
-        "Do not write anything else."
+        "Follow editorial/guide/en-style-v1.md: headings from this post's symptoms (no 'Short answer', 'FAQ', "
+        "'Reproduce it' headings), FAQ only for real extra questions (0-4), no 'Short answer:' opener. "
+        "Do not write anything else."
  ...
-            problems = check_measured_section(article.read_text(encoding="utf-8"), topic_dir)
+            text = article.read_text(encoding="utf-8")
+            problems = check_measured_section(text, topic_dir) + score_en(text)["flags"]
```
`agents/researcher.md` 156·307행: "FAQ 후보 최소 3개" → "본문이 답하지 않는 질문만, 0개 허용".
- 위험: 낮음~중간. 재시도는 기존 1회 구조 그대로라 두 번째도 걸리면 그 EN판은 `article.rejected.html`로 빠진다(KO판 예약은 그대로, EN판만 안 나감).
- 서버: 러너가 git pull로 받음(push 전 prepare inactive 규칙 따름).
- 테스트: `tests/test_english_edition.py`에 가짜 runner가 첫 번째엔 `<h2>FAQ</h2>`를 쓰고 두 번째엔 깨끗한 본문을 쓰게 해서, 두 번째 prompt에 `fixed_heading:FAQ`가 들어가는지 확인.

### C4. 옛 틀 재유입 막기 (G5 해결) — 로컬, 서버 아님
1. 고친 글은 WP 본문을 로컬로 되받기(고치는 일과 끝에 한 줄): `ssh … "wp post get <id> --field=post_content" > editorial/life/<폴더>/ko.html`. 그러면 로컬 lint 결과가 WP와 같아지고 복사 원본도 새 틀이 된다.
2. `tools/build.py`가 있는 4편(고속버스·쿠우쿠우·주택연금·공무원 봉급표)은 원본(`ko.template.html`/`ko.src.html`)을 같이 고치거나, build.py 마지막에 `audit_content_repetition --files ../ko.html` 한 줄을 넣어 옛 틀이면 실패시킨다.
3. `scripts/audit_content_repetition.py` 175행 FIXED_HEADINGS에 `"함께 읽으면 좋은 글"` 추가(backfill_internal_links.py가 넣는 고정 H2).
4. 내부 링크 스크립트(rel1120b.php 방식)는 H2 글자가 아니라 `id="related"`로 찾는다: `#<h2[^>]*id="related"[^>]*>.*?</h2>\s*<ul>\n?#su`. style-v1-rules.md 2번에 "관련 글 소제목 글자는 바꿔도 `id="related"`는 유지" 한 줄 추가.
5. revenue-200-plan.md WORK-START 지시문: "공식 출처·확인일·직접 계산" → "공식 출처(날짜는 그 숫자 문장 안)·우리 계산기 사례, editorial/guide/ko-life-style-v1.md". (승인 범위 안 — 글 생성 지시문)
- 위험: 낮음. 3번은 그 H2가 있는 옛 개발 글도 FLAG로 잡지만, 그 글들은 이미 공개된 글이라 C1(예약 글만 봄)에는 영향 없다.
- 테스트: `tests/test_template_flags.py`에 `<h2>함께 읽으면 좋은 글</h2>` → `fixed_heading:함께 읽으면 좋은 글` 한 줄.

### C5. 그림 단계 (G6) — 그대로 둔다
대표 카드는 이미 예약 때 자동이다. 표 그림·섹션 카드는 규칙상 필수가 아니고, 섹션 카드는 카드마다 다른 숫자·캡션을 사람이 골라야 해서(규칙 5번) 자동으로 만들면 오히려 "같은 캡션" 틀이 다시 생긴다. 바꿀 것은 하나: 출근 점검 일과에 "어제 공개 글 중 hl-glance 없는 글 수"를 넣어 퇴근 세션이 빠진 날을 알 수 있게 한다(코드 변경 0).

### C6. (잠복, G7) — 지금은 손대지 않는다
옛 TOP2 경로를 되살릴 일이 생길 때 `run_daily_pipeline.py`의 `20초 핵심 요약` 강제 분기를 지운다. 지금은 이 분기를 타는 글이 없어서 고치면 오히려 위험만 생긴다.

## 5. 한 줄 요약표

| 변경 | 파일 | 서버/승인 | 막는 빈틈 |
|---|---|---|---|
| C1 공개 1시간 전 보류 | scripts/hold_unstyled_future.py(새), deploy/huntlab-operations-watchdog.service | 러너 서버, **승인 필요** | G1 |
| C2 예약 전 검사 + 점수 exit code | scripts/style_score.py, ~/huntlab-ops/sched_life.sh·sched_en.sh | 로컬 | G2·G3 |
| C3 러너 EN판 지시문·게이트 | scripts/english_edition.py, agents/researcher.md | 러너 pull, 승인 범위 안 | G4 |
| C4 재유입 막기 | 로컬 ko.html 되받기, build.py 4편, audit FIXED_HEADINGS, 링크 스크립트 id 기준, WORK-START 문구 | 로컬(WP 쓰기는 기존 imp.php 경로) | G5 |
| C5·C6 | 없음(일과 한 줄) | — | G6·G7 |

결정이 필요한 것(사용자): C1 서버 배포 승인, 그리고 EN을 처음부터 보류할지 카톡 경고만 할지. EN 보류를 켜면 75편을 고칠 때까지 EN 공개가 멈춘다.
