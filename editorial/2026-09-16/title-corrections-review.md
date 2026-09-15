# 독자 증상 중심 제목 정정 — 독립 Reviewer 승인

status: APPROVED
manifest_sha256: 3c063f01c17b2ebb347d72f48add6ebfe9c6dc49a0a17532dbe1ff9f6005bb34

작성자와 분리된 AI Reviewer의 승인이다. 사람의 검수나 신규 글 발행 승인이 아니다.
승인 대상은 `content-title-corrections.json`의 기존 ID 706, 373이며 정확한 제목과
본문 해시에 한정한다. WordPress 쓰기는 이번 Reviewer 작업에서 0회였다.

## 승인 범위

| ID | 기존 제목 | 승인 new_title | 유지 slug | after HTML SHA-256 |
| --- | --- | --- | --- | --- |
| 706 | READY가 없으면 발행하지 않는 Evidence-first 기술 글 파이프라인 | 자동발행은 성공했는데 글이 없다면: 미발행과 실패 구분하기 | evidence-first-ready-publishing-pipeline | 1c9c56f19195475807edd3b6ab0a74885977ca3bf400e1a3a8476eb3ece78261 |
| 373 | Topic Planner topics.md 누락 재시도: 빈 성공을 실패로 바꾸는 산출물 계약 | AI 작업이 끝났는데 결과 파일이 없다면: 재시도와 중단 기준 | topic-planner-topics-md-retry | 3ee825d6d541af6754f763e023fbc3ac36c252e91118274963618cb31c9abf22 |

두 글 모두 대표 Category는 자동화·테스트, ID 310이다. ID·slug·날짜·작성자·카테고리·
태그·대표 이미지·excerpt·meta는 보존한다. 제목 정정은 publisher-guide의 9월 16일
명시된 기존/새 제목 승인 규칙을 적용한다. 706은 제목만 바꾸고 본문은 byte-identical,
373은 제목과 첫 문단만 바꾼다. 제목·manifest·본문이 바뀌면 재승인한다.

## 독자 가치와 정확성

706의 새 제목은 첫 문단의 ‘예약 작업 성공 로그와 실제 공개 글 부재’를 예고한다.
본문은 READY 용어를 먼저 알아야 읽을 수 있는 구조에서 벗어나 미발행, 발행 전 실패,
발행 후 감사 실패와 unknown을 구분한다. 실제 글이 이미 있으면 다시 생성하지 말라는
행동도 제공한다. 성공률·복구 보장이나 새 AI 발행 전체 E2E를 암시하는 제목이 아니다.

373의 새 제목과 첫 문단은 완료 로그만으로 필요한 파일의 존재를 보장할 수 없다는
문제를 먼저 설명한다. 한 번 재시도 후 다시 없으면 중단한다는 제한과 내용 검사의
분리를 도입에서 제시한다. Topic Planner/topics.md는 이 사례의 실제 구현 이름으로
설명되며, 모든 AI 실패를 한 번에 복구한다는 뜻이 아니다. 둘째 문단부터의 역사
환경, fake runner 범위, timeout·동시 실행·부분 쓰기 한계는 그대로 유지됐다.

두 제목은 기존 글의 동일한 검색 의도를 더 쉽게 설명한다. 706은 외부 WordPress
게시 상태 판별, 373은 작업 결과 파일의 부재 판별로 구분된다. 문장 표면에 비슷한
‘없다면’이 있지만 답해야 할 대상과 후속 행동이 달라 별도 글을 합치거나 추가로
생성할 이유가 없다. 본문과 다른 유입 키워드·수치·경험을 추가하지 않았다.

## 직접 확인한 근거

- Reviewer/style/SEO/선택된 Evidence-first 유형/Publisher 정책을 확인했다.
- `title-reader-research.md`, before/after 두 본문 전체와 diff를 대조했다.
  706 본문 변경은 없고, 373은 첫 문단 한 개만 다르다. 두 글 모두 링크와 코드 블록이
  before와 완전히 동일하다. 따라서 앞선 승인에서 확인한 고정 근거 링크와 실행 범위를
  새 실험이나 새 운영 결과로 바꾸지 않는다.
- 인증 REST GET으로 현재 기존 제목·slug·raw 본문이 manifest before와 정확히 일치함을
  재확인했다. 실제 Category ID도 둘 다 310이었다.
- `2026-09-15T17:32:17.229159+00:00` 수집한 공개 9/초안 113, 고유 ID 122개
  complete/full_content inventory에 두 최종 제목과 본문을 함께 반영해 비교했다.
  자신의 기존 ID만 제외했으며 새 제목 중복 ID가 없고, 두 글 모두 전체 본문 게이트를
  통과했다. 긴 동일 산문·챗봇 잔재·불완전 inventory 오류가 없었다.
- 373 after HTML의 현재 bash heredoc을 그대로 추출해 `bash -eu`로 직접 실행했다.
  종료 코드 0이며 아래 출력이 본문과 일치했다. 실제 Planner나 WordPress 발행이 아닌
  임시 디렉터리의 fake runner 실행이다.

```text
missing_twice: status=FAIL calls=2 artifact=False error=missing after retry
created_on_retry: status=PASS calls=2 artifact=True retry_prompt=True
bounded_contract: status=PASS max_calls=2 third_call=False exit_contract=PipelineError
```

- 갱신된 updater의 14개 테스트도 통과했다. 이 테스트는 실제 WordPress 적용 확인을
  대신하지 않는다.

## Publisher 후속 조건

별도 영수증 디렉터리에서 dry-run을 먼저 수행한다. 기존 제목·ID·slug·raw를 다시
확인하고 전체 원본을 백업한 뒤 승인 new_title과 허용된 본문만 갱신한다. 응답을
잃으면 GET으로 대조하고 무조건 재전송하지 않는다. 실제 제목·본문·보호 메타데이터
REST 재조회와 공개 H1/title/canonical/본문 확인까지 완료해야 적용 성공이다.
