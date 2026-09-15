# 기존 공개 글 5편 실행 안내 정정 — 독립 Reviewer 판정

status: APPROVED
manifest_sha256: b59136aab9ae9cac4444ecb9dfe60a8ba99dca1d3783892dfc649fec7a1a12f2

승인 대상은 같은 디렉터리의 `content-corrections.json`과 그 manifest가 가리키는
정확한 after HTML이다. 작성자와 분리된 **AI Reviewer** 검토이며 사람의 본문 검수가
아니다. 2026-09-16에 명시된 위임 운영 정책을 적용했다. 새 글 발행, 주제 승인,
제목·slug 변경, AdSense 승인 또는 신규 글 전체 파이프라인 실행을 승인하는 문서가 아니다.

## 승인한 기존 대상과 정확한 본문

| existing_post_id | 기존 제목 | 기존 slug | Category ID | after HTML SHA-256 |
| --- | --- | --- | --- | --- |
| 50 | Retry-After 날짜값에서 재시도가 멈춘 이유와 파서 수정 | wordpress-rest-api-retry | 309 | 2d8b814d2dbc2731b80ad4af7d15969c7a78ab4c5aea3de8254e3af4bfa05363 |
| 290 | WordPress REST API Fake Client 테스트: 실제 게시물 없이 발행 계약 검증하기 | wordpress-rest-api-fake-client-test | 310 | 98f76d786c3b74655035c6a00e45cc69cc3d0e33843b146c615904714d6bf3e1 |
| 373 | Topic Planner topics.md 누락 재시도: 빈 성공을 실패로 바꾸는 산출물 계약 | topic-planner-topics-md-retry | 310 | bca128292894e752d30f826b07b21d31a22bfe2a6f67bf82d568445754bb4295 |
| 698 | HTTP 200인데 WordPress REST 발행이 실패한 이유 | wordpress-rest-html-200-validation | 309 | 25c5c646dece6da0eac833772dc6454e50877f39c93f4cd1a7fc53794a8d04b7 |
| 699 | noindex 글이 sitemap에 남는 배포 불일치 잡기 | wordpress-noindex-sitemap-consistency | 311 | 29b600790d5cb20636e54d454f402a8470605bb3b0f850adae61944278affa45 |

309는 REST API 발행, 310은 자동화·테스트, 311은 WordPress 운영이다.
ID·제목·slug·카테고리·태그·대표 이미지·발행 날짜·작성자·excerpt·meta는 보존하고
본문만 갱신한다. 본문 승인 뒤 manifest 또는 HTML 한 바이트라도 바뀌면 재검토한다.

## 검토와 보정 과정

- 최초 제안은 익명 REST의 `content.rendered`였으므로 승인하지 않았다.
  최종 before는 인증 GET의 `content.raw`와 정확히 일치한다. 각 대상의 ID, 제목,
  slug와 before/after SHA도 독립 확인했다. Publisher는 적용 직전 다시 조회해야 한다.
- 최초 5편의 긴 공통 설치 문단은 최종 상태에서 글끼리 중복될 우려가 있어 수정 요청했다.
  최종본은 글별 준비 설명으로 줄였고, 공통 명령은 코드로 구분했다.
- 373의 역사 콘솔 전체와 같은 코드가 두 번 표시되던 제안을 반려하고, 현재 복사 실행
  블록 한 개와 짧은 출력으로 정리하도록 요청했다. 과거 Linux/Python 환경과 캡처는
  역사 자료임을 밝혔으며, 현재 명령·출력의 9월 16일 재실행과 혼동하지 않는다.
- 새 경험·장애·수익·성과를 만들지 않았다. 50의 POST 중복과 30초 상한 한계,
  290의 Fake Client와 실제 REST 차이, 373의 실제 Planner 미실행 범위,
  698/699의 통제된 fixture와 실제 운영·색인 결과의 차이를 유지했다.
- 제목과 본문 검색 의도는 그대로다. 새 H1·불필요한 FAQ·새 광고 문구를 추가하지 않았다.
  기존 이미지·메타 설명을 교체하거나 새 캡처를 실제 실행 화면으로 가장하지 않는다.

## 독립 검증 결과

전체 본문 inventory는 `2026-09-15T17:07:05.231122+00:00` 수집본이며
`complete=true`, `full_content=true`, 공개 9/초안 113, 고유 ID 122개다.
최종 5개 본문을 **같은 inventory에 모두 반영한 예상 최종 상태**로 비교했다.
각 검사에서 자신의 existing_post_id만 제외했으며 5개 모두 180자 이상 동일 산문,
챗봇 잔재 및 inventory 유효성 검사 실패가 없었다. 이는 122편의 품질을 모두
재승인했다는 뜻이 아니며 검색 의도는 아래와 같이 별도 판단했다.

- 50: Retry-After 날짜 파서의 입력 해석 오류.
- 290: Fake Client 경계에서 validation 실패와 정상 payload 대조.
- 373: 산출물 누락의 최대 두 번 호출과 실패 처리.
- 698: HTML 200과 JSON 글 응답의 판별, 유효한 양의 정수 ID.
- 699: robots/canonical과 sitemap URL 집합의 일관성.

준비 명령과 실행 안내를 기존 문제 해결 글에 보강하는 것이므로 별도 신규 검색 의도를
만들지 않는다. 706과 겹치는 발행 불확실 상태 보강은 이번 5편 승인 범위 밖이다.

Reviewer가 직접 실행한 명령:

```bash
.venv/bin/python -m unittest tests.test_wordpress_retry tests.test_huntlab_wp_diagnostics tests.test_publisher.PublisherTests.test_validation_failure_does_not_call_wordpress tests.test_publisher.PublisherTests.test_successful_draft_uses_draft_status_and_audit_log
```

Python 3.12.9에서 총 10개 통과, 종료 코드 0. 373 after HTML에서 현재 heredoc을
그대로 추출하여 `bash -eu`로 실행한 결과도 종료 코드 0이며 다음 출력과 일치했다.

```text
missing_twice: status=FAIL calls=2 artifact=False error=missing after retry
created_on_retry: status=PASS calls=2 artifact=True retry_prompt=True
bounded_contract: status=PASS max_calls=2 third_call=False exit_contract=PipelineError
```

5개 after HTML의 HTTPS 본문 링크는 중복 제거 25개 모두 GET 최종 HTTP 200이었다.
698의 수정 후 고정 커밋 `deff84730558152c9290a9ef36af325adaf002dd` 진단기·회귀
테스트 링크도 포함한다. 가용성 검사와 코드/주장 대조는 구분했다.

## Publisher 실행 조건

`scripts/apply_editorial_corrections.py`의 기본 dry-run으로 전체 사전검사를 통과한 뒤
명시적 apply를 수행한다. 전체 before 백업을 먼저 보존하고 body만 REST 갱신한다.
POST 자동 재시도는 0회이며 응답 유실은 GET read-back으로 확인한다. 결과가 불명확하면
같은 요청을 재발송하지 말고 durable attempt와 서버 상태를 대조한다. 다른 편집자가
동시에 본문을 변경하지 않게 한다. REST에는 이 구현이 사용하는 원자적 비교 갱신이 없다.

공개 반영 뒤 실제 HTML·canonical·카테고리·링크 및 sitemap 검증은 아직 Publisher의
후속 책임이다. 이 문서 작성 시 Reviewer의 WordPress 쓰기는 0회다.
