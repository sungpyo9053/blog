# WordPress 복원 시험 — 검색 의도와 근거 사전 조사

- status: INSUFFICIENT
- 조사일: 2026-09-16 KST
- 제안 주제: WordPress 복원 테스트: DB만 복원한 상태와 uploads를 포함한 상태 비교
- 판정: 기존 글과 구분 가능한 독자 문제는 있으나, 아직 실행 근거가 없어 Writer/Publisher에 넘기지 않는다.
- WordPress 쓰기: 이 조사에서는 0회. 앞선 698·699 업데이트와 별도 작업이다.

## 기존 글·초안 전체 비교

인증 GET 스냅샷 `output/editorial-stdlib-20260916/inventory-after.json`은
2026-09-15T17:26:46.872004+00:00 수집, 공개 9편·초안 113편,
complete/full_content=true다. 122개 제목 전체와 전체 본문의 백업·복원·backup·restore
관련 부분을 비교했다. HTML 이미지 URL의 uploads 문자열은 관련성 판단에서 제외했다.

가장 가까운 공개 글 96은 **내부 링크 변경 전 특정 글의 original_content를 JSON에
보관하고 POST를 통제하는 작업**이다. 복원 기능 자체는 없다고 명시한다. 제안 주제는
**사이트 DB를 새 인스턴스에 import해도 미디어 파일은 복원되지 않는 조건과 전체
backup set의 복원 완료 기준**이므로 대상·실행 방법·완료 결과가 다르다.

초안 16은 Lightsail 구축과 HTTPS 설정이 주의도다. 후반에 DB와 업로드 백업 및
복원 시험 필요성을 짧게 언급하지만, 실제 복원 명령·측정·DB-only 대조 실험은 없다.
공개 132는 REST 전체 목록 수집, 초안 305는 색인 조사 전 콘텐츠 변경 백업으로
역시 별도 의도다. 나머지 관련 언급은 다른 제품의 백업, 롤백 또는 관련 글 링크다.

따라서 **동일 검색 의도의 기존 글은 현재 검토 범위에서 발견하지 못했다**.
이는 완성 원고의 중복 검수 통과 판정은 아니다. 원고 작성 후 당시 최신 122편 이상
전체 본문과 다시 비교해야 하며, 96의 JSON 백업 설명을 재서술하지 않는다.

## 독자가 해결할 문제와 SEO 범위

- Primary Keyword: 워드프레스 백업 복원 테스트
- Secondary Keywords: WordPress DB 복원 이미지 누락, uploads 백업, MariaDB SQL 복원
- Related Keywords: 복원 검증 체크리스트, DB 파일 일관성, 격리 복구 시험
- 검색 의도: 백업 파일의 존재가 아니라 새 환경에서 글·첨부파일이 실제로 되살아나는지 확인한다.
- 완료 조건: DB import 종료 코드뿐 아니라 레코드 식별자와 수, 파일 존재 및 해시, 로컬 HTTP 이미지 응답을 확인한다.
- 수요 근거: 공식 WordPress 문서가 DB와 파일 혼동을 별도 FAQ로 다룬다. 검색량·한국어 순위·트래픽 수치는 확인하지 않았고 제시하지 않는다.
- 경쟁 범위: 이번에는 공식 문서만 조사했다. 상위 수익형 블로그의 순위나 수익은 조사하지 않았다.
- FAQ 후보: DB를 복원했는데 이미지가 없는 이유는? uploads만 있으면 완전한 백업인가? 운영 사이트를 건드리지 않고 복원을 어떻게 확인하나?

## 공식 문서에서 확인한 범위

WordPress는 일반적인 사이트 복원에 DB와 파일이 모두 필요하다고 설명한다.
파일에는 코어·테마·플러그인·uploads·설정이 포함되며 DB dump와 파일을 대응하는
한 세트로 관리하라고 안내한다. 따라서 **DB+uploads 실험도 전체 사이트 복구와
동의어는 아니다**. 테마·플러그인·설정·서버 호환성은 별도 조건으로 남는다.
[WordPress Backups](https://developer.wordpress.org/advanced-administration/security/backup/)

DB 백업 절차가 글·댓글·설정을 저장해도 테마·플러그인·업로드 파일 자체는
저장하지 않는다는 경계가 DB 전용 문서에도 명시되어 있다.
[Backing Up Your Database](https://developer.wordpress.org/advanced-administration/security/backup/database/)

MariaDB 논리 dump는 `mariadb` 클라이언트로 import한다. `--single-transaction`은
InnoDB의 일관된 snapshot에 관한 조건이며 파일 복사를 원자적으로 만들지 않는다.
MyISAM·MEMORY에는 같은 보장이 없고 dump 중 DDL도 제한해야 한다. 실험에서
10.11을 선택했다는 사실과 다른 서버/클라이언트 조합 호환성은 구분해야 한다.
[MariaDB mariadb-dump](https://mariadb.com/docs/server/clients-and-utilities/backup-restore-and-import-clients/mariadb-dump)

위 공식 문서는 실제 원문을 열어 확인했다. 문서만으로 HuntLab 복원 성공을 주장할 수 없다.

## 고유 가치와 근거

- original_contribution: 실제 운영 개편의 롤백 산출물과 재해 복구용 백업을 구분하고, DB-only와 DB+파일 복원에서 성공 판정이 달라지는 조건을 실행 결과로 보여줄 계획.
- verification_mode: not_directly_tested
- evidence: 현재는 공식 문서와 오케스트레이터가 전달한 운영 점검 정보뿐이다. 직접 복원 결과·명령 출력·커밋 증거는 아직 없다.
- limitations: 실제 복원 실패, 이미지 HTTP 상태, 복원 소요 시간, 데이터 보존 수를 아직 측정하지 않았다. READY가 아니다.

운영 점검 전달값은 기존 개편 롤백 백업이 DB 약 9MB와 플러그인 약 0.5MB였고
업로드 파일 약 102MB는 그 세트에 없었다는 것이다. **이 조사자가 서버에서 재검증한
값은 아니며 공개 원고에 그대로 채택하지 않는다.** 해당 백업은 개편 롤백 목적이므로
그 자체를 장애나 누락 버그라고 단정하지 않는다. 완전한 복구를 입증하지 못한 운영
과제를 발견한 것으로만 취급한다.

## 작업 기록 및 READY 전에 필요한 증거

- evidence_origin: 현재 docs_only. 실제 운영 개선 기록과 새로 설계한 대조 실험의 출처는 나눠 적는다.
- work_trigger: 전체 품질 개선에서 변경 롤백 백업과 전체 사이트 복원 검증이 다른 보장이라는 점을 확인했다는 운영 점검 전달.
- actual_sequence: Publisher 2편 검증 완료 → 최신 전체 목록 의도 비교 → 공식 DB/파일 복원 경계 확인. 실제 복원은 아직 실행하지 않았다.
- friction_or_surprise: 실제 실험에서 관측한 실패나 예상 밖 결과는 아직 없다.
- decision_log: 검색 의도는 독립 후보로 유지하되 발행 보류. 점수나 글 수를 채우려고 복원 경험을 만들지 않는다.
- unfinished_edge: 재해 복구용 백업 세트의 실물, 격리 복원 결과, 원래 상태와의 대조가 필요하다.

다음은 **실행 제안**이지 관측 결과가 아니다.

1. 먼저 운영 개선 목적을 기록하고 DB·파일 세트의 범위/시각/해시/일관성 조건을 남긴다. 서버 비밀설정과 DB 개인정보는 공개 저장소에 넣지 않는다.
2. 운영 DB를 직접 덮어쓰지 않고 격리된 MariaDB/WordPress 환경에서 시작한다. 복제한 운영 플러그인은 외부 메일·웹훅·예약 작업을 실행할 수 있으므로 네트워크 격리와 비활성화가 선행되어야 한다.
3. DB-only 대조군에서 데이터 import 자체의 성공과 파일 누락 여부를 독립 판정한다. 실제 복구에서 관측하지 않은 장애를 과거 운영 장애처럼 쓰지 않는다.
4. 같은 DB와 환경에 대응하는 파일을 추가한 실험군을 비교한다. 글·첨부 ID/수, 파일 해시, HTTP 본문과 이미지 응답, 종료 코드를 기록한다. DB 테이블 몇 개만 확인한 실험을 전체 WordPress 복원이라고 부르지 않는다.
5. 검증 코드의 실제 프로젝트 변경·커밋·회귀 테스트·공개 가능한 로그가 확보되면 Writer보다 먼저 Research/Reviewer가 READY 조건을 재평가한다. 실패 원문과 한계도 보존한다.

## 수익화와 공개 제한

- monetization_intent: 정보 제공
- conversion_goal: 독자의 격리 복원 검증 완료
- commercial_keywords: 없음
- recommended_cta: 공식 백업 체크리스트를 확인하고 자신의 세트 범위를 점검한다.
- affiliate_disclosure: 이 조사에 제휴·협찬 자료 없음. 새 원고에서도 확인되지 않은 계약을 추정하지 않는다.

공개 금지: SQL 원문/자격증명/사용자 이메일/쿠키/비밀환경/사설 인프라 식별자.
공개 가능 후보: 비식별 합계, 파일 해시 검증 결과, 합성 fixture, 종료 코드, 정제한
실행기와 테스트. 캡처 근거는 실제 실행 전에는 만들지 않는다.

## Writer 전달 전 필수 입력 체크리스트

2026-09-16 추가 준비. 아래는 결과를 채우기 위한 빈칸이 아니라, 원문 근거가
도착해야 다음 단계로 넘어갈 수 있는 조건이다. 현재 INSUFFICIENT 판정을 유지한다.

- Harness가 만든 주제 디렉터리와 `planner-context.json`: `content_type=evidence_deep_article`, `evidence_candidate`, `evidence_contract`, 대표 카테고리·태그, publish_mode 필요.
- `problem_origin`, 한 문장 `editorial_thesis`, `chosen_focus`, `rejected_angle`, `structure_mode`, `reader_outcome` 필요. 주제는 **복원한 DB의 미디어 참조와 uploads 파일 대조**로 좁힌다. 전체 사이트 재해 복구를 약속하지 않는다.
- 같은 폴더의 최종 `research.md` 및 Harness 생성 `recent-style-context.json` 필요. 현재 이 사전 조사 파일만으로 Writer 초안을 시작하지 않는다.
- 실제 feature diff와 고정 공개 commit URL, 새 validator의 정확한 파일명·명령 인터페이스·입출력 스키마·실패 종료 상태 필요.
- 실제 백업 생성 및 격리 DB import의 명령, UTC/KST 시각, 종료 상태, MariaDB 서버/클라이언트 버전 및 이미지 digest 필요. 버전 태그만으로 실행 이미지를 특정하지 않는다.
- 운영과 격리 환경의 구분: DB 컨테이너 network-none, WordPress/PHP 미실행, 운영 DB 무변경 여부를 실제 로그로 확인한다. 이 조건이면 관리자 로그인·테마 렌더링·이미지 HTTP 복원을 검증했다고 쓰지 않는다.
- 원본과 복원본의 DB 참조 수·식별자/집계 해시, 복원 파일 목록 및 SHA 비교 방법 필요. 공개 자료에서는 개인 파일명과 원문 DB를 제거한다.
- DB-only와 DB+uploads를 같은 DB snapshot·같은 validator로 비교한 결과 필요. 누락 이미지 수·정상 파일 수는 실제 출력만 사용한다.
- validator 실패 모드 테스트 필요: 존재하지만 다른 바이트, 누락 경로, 중복/잘못된 입력, 상위 경로 탈출·심볼릭 링크, 원본/복원 시점 차이 중 구현이 지원하는 범위와 미지원 범위를 분리한다.
- 새로운 독자가 공개 저장소의 고정 버전에서 실행 가능한 합성 fixture 명령과 예상 종료 코드 필요. 운영 SQL/파일을 공개해야만 재현 가능한 구조이면 공개 예제를 별도로 설계한다.
- 공개 가능한 실제 명령·출력 5~20줄과 캡처 후보 1개, 회귀 테스트의 실제 개수·명령·결과, Reviewer의 독립 재실행이 필요.
- 최종 본문을 당시 최신 공개·초안 전체와 비교하고 독립 Reviewer가 HTML SHA 및 evidence commit을 승인해야 한다.

## 최소 독자 가이드 전개안

결과 확인 후에만 아래 흐름에서 필요한 부분을 골라 쓴다. 소제목과 수치를 미리
확정하지 않으며 이전 글의 전형적인 실패-성공 상자를 반복하지 않는다.

1. **해결할 질문:** DB import가 끝난 뒤 미디어 참조에 대응하는 파일도 있는가. 첫 화면에서 확인한 것과 미확인인 전체 사이트 복구를 짧게 구분한다.
2. **먼저 실행할 안전한 예제:** 공개 fixture와 Python 환경 준비, 실행 명령, 실제 정상/실패 종료 상태. 운영 인증이나 파일을 요구하지 않는 경로부터 제시한다.
3. **왜 DB 숫자만으로 끝낼 수 없었나:** 실제 DB-only 대조 결과와 파일을 포함한 대조 결과를 필요한 값만 비교한다. 원래 롤백용 백업을 오류라고 재해석하지 않는다.
4. **구현을 자신의 백업에 적용할 지점:** DB 참조 manifest와 파일 해시 manifest가 어느 입력에서 만들어지는지, validator가 무엇을 판정하고 무엇을 판정하지 않는지 보여준다.
5. **통과 후 남는 검사:** 테마·플러그인·설정·PHP 실행·HTTP 이미지·업로드 시점 정합성 등 실제로 확인하지 않은 다음 단계를 한곳에 모은다. 모든 문단에 면책을 반복하지 않는다.

`feature_build`는 요구사항·구현 diff·핵심 테스트·완성 결과·미지원 범위가 맞을 때
검토할 수 있다. 새 대조 실험만으로 `operations_incident`나 과거 장애 회고로
바꾸지 않는다. 단순히 파일 수가 같다는 출력만 있으면 내용을 확인하는 도구라고
과장하지 않으며 독자에게 가치가 부족하면 새 글 대신 운영 개선으로 마친다.
