# News Worthiness Shadow 운영 규칙

이 문서는 `CandidateEvaluator → Hard Filter → NewsWorthinessScorer →
TopicReranker`의 Shadow 운영 및 production 승격 기준에 대한 운영 SSOT다.
코드는 이 문서를 읽어 자동 승격하지 않으며, production 전환은 운영자의 명시적
승인과 별도 변경으로만 수행한다.

## 불변 경계

- 기존 TopicPlanner TOP2가 유일한 production 선정 결과다.
- Shadow 오류, 누락, 지연은 Writer/Reviewer/Publisher와 02시 발행을 막지 않는다.
- CandidateEvaluator는 Adapter다. Planner에 실제 존재하는 값과 근거만 옮기며
  새로운 점수나 근거를 추론하지 않는다.
- 원점수가 있어도 근거가 없으면 `none × 0.0`으로 effective score를 0으로 만든다.
- 검색 수요는 숫자로 저장된 관측값만 사용한다. Planner의 정성 검색 수요 점수는
  Shadow `search_demand` 계산에 사용하지 않는다.
- outcome은 ranking record를 수정하지 않고 `candidate_id → topic_id → post_id`에
  append-only observation으로 연결한다.

## Shadow 산출물

각 실행의 `output/runs/<run_id>/news-worthiness-shadow.json`에 다음을 저장한다.

- legacy/shadow TOP2, overlap, legacy-only, shadow-only
- Hard Filter 탈락과 사유, evidence 누락
- 후보별 raw/effective feature, evidence, multiplier, score breakdown
- topic decay 적용 내용, 최종 순위
- contract/scorer/weights version과 source snapshot hash

산출물은 공개하거나 발행 입력으로 사용하지 않는다.

## production 승격 Gate

아래 조건을 모두 충족해야 운영자가 승격 검토를 시작할 수 있다.

1. 최근 14일 연속으로 Shadow 일일 실행이 완료되고, legacy 발행을 막은 사례가 0건이다.
2. Hard Filter의 치명적 오탐과 치명적 미탐이 각각 0건이다. 치명적 사례는 근거 계약을
   충족한 후보를 잘못 배제하거나, 고위험·중복·출처 미달 후보를 통과시킨 경우다.
3. TOP10 필수 feature/evidence 누락률이 5% 이하이고, Shadow TOP2에는 필수 근거
   누락이 0건이다.
4. 같은 기간 후보를 Offline Replay했을 때 신뢰·중복·근거 완전성 지표가 legacy보다
   악화되지 않고, 편집자 블라인드 평가의 평균 선정 품질도 legacy보다 낮지 않다.
5. topic decay로 서로 독립적인 중요 주제가 부당하게 탈락한 사례가 0건이다.
6. contract/scorer/weights 버전과 source snapshot hash로 전 결과를 재현할 수 있다.

조건 충족은 자동 전환 권한이 아니다. 운영자가 평가 보고서를 검토하고 production
승격을 명시적으로 승인한 뒤, 별도 코드·설정 변경과 회귀 테스트·배포를 수행한다.

## 즉시 중단 조건

- Shadow가 legacy TOP2 또는 발행 입력을 변경한 경우
- 개인정보·인증정보가 evidence나 artifact에 기록된 경우
- source snapshot으로 점수를 재현할 수 없는 경우
- 고위험 주제의 근거 계약 위반 후보가 Shadow TOP2에 포함된 경우

중단 시에도 legacy 02시 발행 경로는 유지하고 Shadow만 비활성화하거나 수정한다.
