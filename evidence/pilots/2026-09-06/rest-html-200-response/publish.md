---
title: HTTP 200인데 WordPress REST 발행이 실패한 이유
slug: wordpress-rest-html-200-validation
category: 기술 해설
tags:
  - WordPress
  - REST API
  - 자동발행
  - 회귀 테스트
publish_mode: publish
run_id: evidence-lab-20260906-rest-html-200
topic_id: rest-html-200-response
source_id: demand-evidence-lab-v1
meta_description: WordPress REST 응답의 HTTP 상태만 확인하면 로그인 HTML을 성공으로 오인할 수 있다. Content-Type과 생성된 글 ID를 함께 검증하는 방법을 통제 실험으로 확인했다.
excerpt: HTTP 200만 확인한 자동발행 검사는 로그인 HTML도 성공으로 오인합니다. Content-Type, JSON 본문, 생성된 글 ID를 함께 검사하는 계약을 통제 fixture로 검증했습니다.
content_type: verified_case
problem_group: REST API 발행
verification_method: controlled_comparison
evidence_date: '2026-09-06'
evidence_badges:
  - 직접 재현
  - 회귀 테스트
  - 공개 코드
evidence_url: https://github.com/sungpyo9053/blog/tree/601ac6386f7ad20168ef450e47ca6c1a71daea9e/evidence/lab-fixtures
asset_url: https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/scripts/huntlab_wp_diagnostics.py
monetization_intent: troubleshooting
conversion_goal: diagnostic_script_use
recommended_cta: GitHub에서 진단 스크립트 실행하기
affiliate_disclosure: 없음
---

WordPress 자동발행에서 `HTTP 200`은 요청이 원하는 결과를 만들었다는 증거가 아니다. 프록시나 인증 계층이 로그인 HTML을 200으로 반환해도 상태 코드만 보는 Publisher는 성공으로 기록할 수 있다. 이 글은 실제 운영 장애 회고가 아니라, 그 오판 조건을 격리된 fixture에서 만든 통제 실험이다.

## 실패 조건을 먼저 고정했다

입력은 세 가지다. 상태는 200, `Content-Type`은 `text/html`, 본문은 로그인 페이지 형태의 HTML이다. 운영 WordPress에는 요청하지 않았다.

```bash
.venv/bin/python scripts/huntlab_wp_diagnostics.py rest-response \
  --status 200 \
  --content-type 'text/html; charset=UTF-8' \
  --body evidence/lab-fixtures/rest-html-200.html
```

상태 코드만 보는 이전 판단은 이 입력을 성공으로 통과시킨다. 강화한 진단기는 다음처럼 종료 코드 1과 구체적인 이유를 돌려줬다.

```text
passed=false
reason=unexpected_content_type
status=200
content_type=text/html
body_bytes=99
```

핵심은 “200이 아니면 실패”가 아니라 “이 API 호출에서 기대한 응답 계약인가”다.

## 생성 요청의 성공 계약

게시물 생성 호출이라면 최소한 다음 세 조건을 함께 확인해야 한다.

1. 허용한 HTTP 상태인가.
2. 응답의 media type이 `application/json`인가.
3. JSON을 파싱했을 때 생성된 게시물의 정수 ID가 기대값과 일치하는가.

진단 코드의 결정 지점은 다음처럼 작다.

```python
media_type = content_type.split(";", 1)[0].strip().lower()
if media_type != "application/json":
    return failed("unexpected_content_type")

payload = json.loads(body)
if payload.get("id") != expected_id:
    return failed("post_identity_mismatch")
```

전체 구현과 fixture는 [고정 커밋의 진단 스크립트](https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/scripts/huntlab_wp_diagnostics.py)와 [테스트](https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/tests/test_huntlab_wp_diagnostics.py)에서 확인할 수 있다.

## 같은 검사기에 정상 응답을 넣었다

비교 입력은 201, JSON content type, `id=742`인 최소 응답이다.

```bash
.venv/bin/python scripts/huntlab_wp_diagnostics.py rest-response \
  --status 201 \
  --content-type 'application/json; charset=UTF-8' \
  --body evidence/lab-fixtures/rest-post-201.json \
  --expected-id 742
```

결과는 종료 코드 0이었다.

```text
passed=true
reason=validated_json_post_identity
status=201
content_type=application/json
post_id=742
```

실패와 성공은 같은 Python 3.12.9 환경, 같은 검사기, 고정된 입력 파일로 비교했다. 이 실험 중 네트워크 쓰기와 WordPress 쓰기는 각각 0회였다.

## 회귀 테스트가 막는 오판

`test_html_login_page_with_200_exposes_status_only_false_positive`는 200 HTML이 거절되는지 검사한다. `test_json_post_identity_passes_same_response_contract`는 JSON 응답의 ID까지 일치할 때만 통과하는지 검사한다. 네 개 진단 회귀 테스트를 실행한 결과는 모두 통과였다.

```bash
.venv/bin/python -m unittest tests.test_huntlab_wp_diagnostics -v
```

검사 결과와 입력 파일 SHA는 [Evidence Lab 실행기](https://github.com/sungpyo9053/blog/blob/601ac6386f7ad20168ef450e47ca6c1a71daea9e/scripts/run_evidence_lab.py)가 기록한다. 따라서 나중에 fixture가 바뀌면 같은 결과라고 주장할 수 없다.

## 이 검사를 적용하면 안 되는 경우

읽기 API는 정상 상태가 200일 수 있고, 삭제 API는 204처럼 본문이 없는 성공을 사용할 수 있다. 모든 REST 호출에 201과 `id`를 강제하면 또 다른 오판이 된다. 호출 종류별로 허용 상태와 필수 응답 필드를 선언해야 한다.

또 이 fixture는 프록시 제품 하나의 실제 동작을 재현한 것이 아니다. 확인한 범위는 “HTML 200을 상태 코드만으로 성공 처리하는 클라이언트 결함”이다. 특정 플러그인이나 호스팅 서비스가 원인이라고 확대하지 않는다.

## 발행 후 검증 체크리스트

- 요청 종류별 허용 상태를 분리한다.
- 응답 media type을 파싱한 뒤 JSON만 디코딩한다.
- 생성·수정 대상의 ID와 slug를 read-back으로 대조한다.
- JSON 파싱 실패를 성공으로 기록하지 않는다.
- 실패 시 재시도 가능 여부와 중복 생성 위험을 별도로 판단한다.

[진단 스크립트와 재현 fixture 보기](https://github.com/sungpyo9053/blog/tree/601ac6386f7ad20168ef450e47ca6c1a71daea9e/evidence/lab-fixtures)
