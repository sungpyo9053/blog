# Evidence-first Deep Article

`planner-context.json`의 `evidence_candidate`와 `evidence_contract`가 유일한 사건
범위다. 뉴스, RSS, Trends, 검색량은 사건 근거가 아니다. 외부 공식 문서는 실제
관측을 설명하거나 독자 수요를 보조 확인하는 용도로만 사용한다.

## 유형별 필수 증거

- `debugging_log`: 실패 출력, 원인 코드·설정, 수정 diff, 동일 조건 통과, 재발 방지
- `feature_build`: 요구사항, 구현 diff, 핵심 테스트, 완성 결과, 미지원 범위
- `migration`: 변경 전후 버전·동작, 호환성 차이, 회귀 테스트, 롤백 조건
- `benchmark_experiment`: 고정 환경·입력, baseline, 비교 대상, 측정값, 한계
- `architecture_decision`: 실제 문제, 대안, 기준, 채택·기각, 결정 기록, trade-off
- `operations_incident`: 운영 관측, 영향, 대응·복구, 사후 검증, 재발 방지

필수 항목 하나라도 원본 근거와 연결되지 않으면 `INSUFFICIENT` 또는 `REJECTED`다.

## 작성·승인 규칙

- 실제 증거의 시간·인과 순서를 바꾸지 않는다.
- 코드·로그·수치는 원본과 assertion에 정확히 대응시킨다.
- 테스트 fixture를 운영 장애나 사용자 영향으로 표현하지 않는다.
- 미검증 영역, 미지원 범위, 적용하면 안 되는 조건을 명시한다.
- `20초 핵심 요약`, 표, FAQ, 결론을 강제하지 않는다.
- 최근 글의 제목 문형, 도입, H2 순서, 마무리를 복제하지 않는다.
- 공개 가능한 고정 commit·test·log 링크를 근거 가까이에 둔다.
- 가짜 실패, 성과, 사용자 반응, 작성자 경력을 만들지 않는다.

독자는 읽은 뒤 하나 이상의 실행, 선택 또는 회피 행동을 할 수 있어야 한다.
Reviewer는 최종 HTML SHA-256과 evidence commit을 함께 기록하며 한 바이트라도
변경되면 재승인한다.
