# 독자 문제 해결 가치 검토 — 706 / 2026-09-16

## 편집 판단

706은 초안 보관보다 **기존 글 보강**이 적합하다. 고유 근거는 후보 없음·점검·발행 실패·발행 후 공개 검사 실패를 서로 다르게 처리한 실제 커밋과 테스트다. 다만 원래 글은 내부 용어와 체크포인트의 세 역사 순서를 먼저 나열해, 글이 왜 없거나 왜 재발행하면 안 되는지 찾는 독자의 행동을 늦췄다.

- 대상: WordPress 자동발행을 운영하며 예약 성공 로그와 게시물 결과가 맞지 않는 개발자/운영자.
- 실제 검색 증상: 작업은 성공했는데 새 글이 없거나, 글이 있는데 마지막 검사만 실패해 재실행할지 모르는 상황.
- 읽은 뒤 행동: 실행 상태를 분류하고 공개 slug 조회로 기존 ID부터 찾는다. 빈 응답을 무생성 증거로 해석하지 않고 관리자 초안/예약/기록을 대조한다. 자신의 발행 경계에 여섯 격리 테스트를 옮긴다.
- 고유 증거: `deff84730558152c9290a9ef36af325adaf002dd`의 후보 소비 위치·공개 감사·확인된 쓰기의 일일 한도 분리와 공개 테스트. 신규 미배포 수정은 본문 근거에 넣지 않았다.
- 신규 글보다 기존 706이 적합한 이유: 동일한 발행 제어 문제와 같은 함수/테스트를 다루므로 새 검색 의도를 만드는 변경이 아니다.

현재 ID/제목/slug는 유지한다. 별도 제목 수정 제안은 **“자동발행은 성공했는데 글이 없다면: 미발행과 실패 구분하기”**다. READY라는 내부 상태명보다 독자의 증상이 먼저 보인다. 이 제안은 본 manifest의 변경 대상이 아니며 독립 검토와 제목 변경 지원을 거쳐야 한다.

## 실제 검증

1. 인증된 GET의 `content.raw` 스냅샷으로 before를 고정했다. 공개 필터링 본문으로 원문을 대체하지 않았다. 생성물은 `content-value-corrections.json`, `post-706.value.before.html`, `post-706.value.after.html`이다.
2. 본문의 읽기 전용 curl을 실제 실행: 공개 posts 컬렉션에서 해당 slug 조회 → JSON 배열, ID 706/status publish/예상 slug/공개 URL. 인증 정보 없음, GET만 수행, WordPress 쓰기 없음.
3. 로컬 저장소의 고정 SHA에서 scripts/publisher/tests를 임시 폴더로 추출하고 기존 Python 3.12.9에서 지정 여섯 테스트를 실행: 모두 통과, 0.028초, exit 0.
4. 독자 설치 마찰을 줄이기 위해 **새 가상환경**에서 Markdown/PyYAML 두 패키지만 설치해 같은 여섯 테스트 재실행: 모두 통과, 0.030초, exit 0. 본문에는 이 두 번째 결과를 사용했다. GitHub clone 네트워크 경로는 새 가상환경 실험에 포함하지 않았고 그 한계를 명시했다.
5. 테스트는 mock 발행기와 임시 파일시스템을 사용한다. 실제 AI→검수→발행 전체 실행이나 실제 WordPress 쓰기 안전성을 실증했다고 주장하지 않는다.

선택한 여섯 테스트:

```text
test_no_topic_is_success_and_never_calls_publisher
test_ready_dry_run_does_not_advance_global_checkpoint
test_publisher_failure_does_not_consume_candidate_checkpoint
test_public_audit_failure_after_publish_consumes_candidate_checkpoint
test_failed_run_with_confirmed_wordpress_write_counts_toward_daily_limit
test_second_ready_candidate_on_same_day_is_not_published
```

모두 `tests.test_evidence_deep_article.EvidenceDeepArticleTests` 소속이다. 원래 역사 로그의 11개/0.029초는 그대로 역사 기록으로 분리한다.

## 공개 전 검토 항목

- 쓰기 unknown인 경우 자동 보류는 독자에게 권하는 안전한 운영 판단이지, 현재 모든 불확실성을 코드가 해결했다는 주장으로 읽혀서는 안 된다.
- 공개 slug 조회의 빈 배열은 private/draft/future 또는 바뀐 slug를 배제하지 못한다. 관리자 추가 대조를 삭제하지 않는다.
- 현재 운영 정책을 새 실행 성과처럼 쓰지 않는다. 9월 15일 고정 코드는 설명/격리 테스트를 위한 것이며 구버전 운영 배포를 권하는 명령이 아니다.
- 제목과 slug는 이번 body-only 수정에서 유지한다.
- 373은 이미 승인된 다섯 편 수정과 충돌하지 않도록 건드리지 않았다. 후속 판단 시 ‘Planner가 성공했다고 했는데 파일이 없다’라는 독자 증상과 산출물 검사 예제를 앞세우는 방향이 적합하다. 706과 달리 파일 생성 계약 자체가 의도라 별도 글 가치는 있다.

## 다음 준비 안내 보정

운영자의 별도 새환경 검사에서 698/699는 외부 패키지 없이 표준 라이브러리만으로 두 실험과 진단 테스트를 통과했다. 현재 다섯 편의 승인·적용 중 원문은 바꾸지 않는다. 적용 완료 후 새 raw 스냅샷을 받아 해당 두 글의 운영용 전체 requirements 설치 안내를 제거하는 별도 좁은 수정이 적합하다.
