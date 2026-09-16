# 피지컬 AI 첫 기초 글 — 전체 중복 검토와 Writer 입력 승인

- 검토일: 2026-09-16 KST
- 검토 주체: `physical_editorial` (Research 작성자 및 후속 Writer와 별도 역할)
- 후보 판정: **READY_FOR_WRITER** — 기초 해설의 작성 입력으로 승인.
- 발행 판정: **HOLD** — 최종 본문·독립 품질 검수·Publisher 계약은 아직 없다.
- 콘텐츠 점수: **NOT_EVALUATED**. 후보 승인·산술 검산·목록 수집은 99점의 증거가 아니다.

## 인증된 WordPress 전체 조회

저장소의 기존 `scripts/snapshot_topic_inventory.py`와 로컬 인증 설정을 사용했다.
외부 요청은 WordPress REST `GET`, `context=edit`, `status=publish`/`draft`,
`per_page=100` 페이지 순회였다. 게시물·초안·서버 코드를 수정하지 않았다.
인증값과 비공개 원문은 이 보고서에 쓰지 않는다. inventory 본문은 기존 도구의
비밀정보 정제 함수를 거쳐 로컬 output에만 저장했다.

| 관측 | 최초 수집 | 독립 재조회 |
| --- | --- | --- |
| 수집 시각 UTC | 2026-09-16T09:32:34.443374+00:00 | 2026-09-16T09:33:37.289665+00:00 |
| 수집 시각 KST | 2026-09-16 18:32:34 | 2026-09-16 18:33:37 |
| publish | 10 | 10 |
| draft | 113 | 113 |
| 고유 게시물 합계 | 123 | 123 |
| 전체 본문/빈 본문 | 123 / 0 | 123 / 0 |
| full_content / complete | true / true | true / true |

두 조회의 `posts` 전체 객체 배열은 정확히 같았다. 수집 시각이 달라 전체 JSON
파일 해시는 다르며, REST 조회는 DB 트랜잭션 스냅샷이 아니다. 시각별 독립 재조회
일치로 이번 비교 중 변경을 관측하지 않았다는 범위만 확인한다. pending/private/
future/trash나 page·미디어를 전체 글 목록인 것처럼 합산하지 않았다.
검토 대상 정책인 공개 post와 draft post 전체를 비교했다.

- 최초: `output/physical-ai-transition/inventory-latest.json`
- 최초 SHA-256: `c0907ee278c53fa2523f78b376833eafa68735c2215e7e06eb3e5c749d443a1a`
- 보관본: `output/physical-ai-transition/inventory/20260916T093234462037Z.json`
- 재조회: `output/physical-ai-transition/inventory-confirmation.json`
- 재조회 SHA-256: `d7369025309dc7c12ccdbeaaa755426500b14f5708ea72ff7764b7408c60151e`
- 보관본: `output/physical-ai-transition/inventory/20260916T093337313498Z.json`
- 정제된 전체 본문 합계: 2,061,175 UTF-8 bytes.

## 비교 방법과 결론

123개 전체의 제목·요약·상태를 검토하고 전체 본문을 대상으로 피지컬 AI/로봇/
관측/행동/피드백/센서/강화학습 및 관련 영문 용어를 검색했다. 단순 키워드 빈도를
중복 판정으로 쓰지 않고 근접 글의 본문에서 대상 독자·질문·해결 결과를 대조했다.
모든 본문을 수동 정독했다는 주장이 아니라 **전체 수집·전체 텍스트 검색·전체 제목/
요약 검토·근접 본문 의미 비교**의 기록이다. `robots.txt`는 물리 로봇과 무관한
검색엔진 설정 언급이므로 구분했다.

| 근접 기존 글 | 기존 검색 의도 | 새 글과의 구분 |
| --- | --- | --- |
| draft 611, 휴머노이드 정부 투자와 개발팀 준비 | 정책 발표 뒤 부품·시험·인터페이스·권리 자료와 투자/조달 준비 판단 | 센서/상태/명령 단어가 있으나 뜻·피드백 계산·학습과 구별을 가르치는 글이 아니다. 예산·안전 표준·조달 수치를 새 기초 글로 옮기지 않는다 |
| draft 651, 2027 AI 예산과 지원사업 준비 | GPU/AIDC/피지컬AI 지원사업의 준비 및 비용·계약 보류 | 독자는 신청/사업팀이며 기초 작동 원리의 질문과 다르다. 예산 주제로 확장하지 않는다 |
| draft 629, NVIDIA AI 인프라 | GPU 외 네트워크·스토리지·비용·처리량을 비교 | Physical AI가 발표 링크에 있어도 관측/행동/피드백 기초 해설이 아니다 |
| draft 257/274/388, agent 도구 timeout·평가·예산 | 소프트웨어 작업의 부작용·재시도·실행 수명주기 | 작업 상태의 운영 검증과 물리 관측/행동의 개념 학습은 별개. 에이전트 운영 글을 재사용하지 않는다 |
| draft 316/431, 추천 피드백 | 추천 학습/랭킹의 상호작용 데이터와 평가 | 이 글의 고정 규칙 피드백과 정책 학습 구분을 대신 설명하지 않는다 |
| 공개 10개 운영 아카이브 | REST 응답·재시도·발행·백업·색인 등 운영 문제 | 기초 학습 결과와 직접 일치하는 글 없음. 관련 없는 내부 링크를 억지로 연결하지 않는다 |

**판정:** 이 스냅샷에서 '관측과 상태, 행동과 결과, 피드백과 학습을 자체 1차원
계산 예제로 구분'하는 동일 검색 의도의 글/초안을 찾지 못했다. 정책 기사나 운영
글을 보강하는 것보다 별도의 입문 글이 독자 질문과 완결성에 맞다. 주제 확장 또는
발행 전 inventory 변화가 있으면 재검토한다.

## Research 전달 승인과 제한

검토한 원본은 `editorial/2026-09-16/physical-ai-foundations-research.md`이며,
SHA-256은 `9b66d681454afb7fd9769ae10ffb2da5767785fb11991307684d18ec6c9766b9`다.
원본의 `INSUFFICIENT` 및 당시 중복 미확인 기록은 역사적 상태로 보존한다.
Writer용 사본에는 이 보고서로 **중복 검토 미완료 조건을 해소했다는 부록**을
붙일 수 있다. 원본이 과거부터 READY였던 것으로 바꾸지 않는다.

Research에는 주장별 1차 자료와 확인 범위, 자체 이동 예제의 가정·수치·유리수
검산·편향 반례, 이해 확인 질문 및 한계가 있다. 기초 해설의 Writer 입력에는
충분하다. 이 검토는 모든 외부 자료의 사실을 새로 재조사하거나 최종 독립 사실
검수를 끝냈다는 뜻이 아니다. 최종 Reviewer는 출처·수식·문체·범위·가치를 다시 확인한다.

## Writer 입력 메타데이터

- title: 피지컬 AI 작동 원리: 관측·행동·피드백을 숫자로 이해하기
- primary_keyword: 피지컬 AI 작동 원리
- category: 피지컬 AI 기초
- tags: 피지컬 AI, 로봇 기초, 피드백 제어
- content_type: foundation_concept
- publish_mode: draft (작성 산출물의 모드 지정일 뿐 WordPress Draft 생성 허가는 아님)
- type_guide: `guides/content-types/foundation-concept.md`
- target_reader: 변수·조건문·사칙연산은 알지만 로봇/제어 용어를 처음 접하는 개발자
- reader_outcome: 관측/상태/행동을 분류하고 다음 위치를 계산하며 관측상 성공이 실제 성공과 다를 수 있음을 설명
- original_value: 한 가지 자체 이동 규칙과 센서 편향 반례로 피드백·학습·성공 판정의 차이를 연결
- excluded_scope: 실물 구동, 물리 엔진/모델 성능, 구매 추천, 안전 제어법, 지원사업, 최신 최고 모델 주장
- source_id/discovery: 사용자 지정 기초 학습 경로. DEV.to 특정 글을 발굴했다고 꾸미지 않음
- duplicate_inventory: 위 최초 snapshot 및 동일 확인 snapshot
- internal_links: 현재 관련 공개 기초 글 없음. 가짜 후속 링크를 만들지 않음

이 승인에는 기존 사건 miner의 READY 플래그를 꾸며 만드는 행위, 최종 품질 JSON
작성, 자동 발행, WordPress 수정/초안 생성 권한이 포함되지 않는다. foundation 계약을
지원하는 작성 경로로 전달하고, 같은 하루 한도·독립 Reviewer·Publisher 원칙을 유지한다.
