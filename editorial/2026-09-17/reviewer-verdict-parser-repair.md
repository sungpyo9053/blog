# Reviewer 판독 오류 수정

대상 실행: `20260917T010004Z-703edfdfd8`.

## 원인

검수 문서의 독립된 `- verdict: **APPROVED**`를 기존 파서가 인식하지 못했다.
실서버에서 원본 문서를 `validate_publish_contract()`에 입력하여
`Reviewer의 명시적 APPROVED 상태가 없습니다` 오류를 재현했다.
Reviewer 종료는 발행 성공이 아니며, 당시 실행은 실패로 보존한다.

## 수정과 검증

- 짝이 맞는 Markdown 강조/코드 표기의 정확한 APPROVED·REJECTED 값만 판독한다.
- 조건부 표현·본문의 단순 언급·깨진 표기는 승인하지 않는다.
- 서로 충돌하는 명시적 결정은 등장 순서와 무관하게 차단한다.
- Reviewer 지침에 한 줄의 표준 결정 형식을 명시했다.
- 로컬 전체 테스트636개 통과(skip2), 서버636개 통과(skip6).
- 배포 코드: `e995c1419fe19b3a7691a65284f14eaeb6685e99`.
- 동일한 원본 문서로 서버의 승인·해시·품질 계약 검증 통과:
  `f50ea8582c94fca58fcb87f364dd551e83879d6a009e972bc3a5157ceb6f874b`.

## 운영 확인

별도 에이전트의 인증 REST 조회는 전체124건(공개10·초안114)에서 대상 제목·slug·source_id
매치0건을 확인했다. Publisher 실행 이벤트와 감사 결과 파일도 없었다.
`publisher_started`는 전체 topic_runner 이전에 기록되어 실제 Publisher 호출을 뜻하지 않았다.
불명확한 쓰기 상태는 원본 실패 파일을 수정하지 않고 별도 근거·해시 결합 reconciliation으로
정리했다. 독립 검수자는 `/root/publication_readiness`이며 실행 디렉터리의 private 증거 두 개를
receipt에 결합했다. read_reconciliation 검증 통과, 당일 published_today=0,
원본 result/progress 해시 불변 및 failed=true 유지를 확인했다.
WordPress 쓰기·재발행·타이머 변경은 하지 않았다.
이 기록의 테스트 통과를 실제 공개 발행 성공으로 해석하지 않는다.
