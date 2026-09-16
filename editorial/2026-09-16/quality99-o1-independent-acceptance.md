# O1 독립 인수 검토 — 2026-09-16

판정: **O1 PASS — 격리된 공개 WordPress 복원 및 시험 환경 종료 확인 완료.** 자연 예약 실행의 발행-P2와 O1을 반영하면 기존 고정 기준상 **97/100**이다. 남은 항목은 U1·U2·발행-P3이며, 99점이나 AdSense 승인 확률을 뜻하지 않는다.

검토자는 전용 엔진과 입력 진단기 일부를 작성했다. 따라서 전체 작업과 무관한 외부 감사자는 아니다. 다른 실행자가 수행한 DB 복원·정제·WordPress/HTTP 인수 영수증을 읽기 전용으로 대조했으며, 이번 인수 검토 중 HTTP 요청·컨테이너 변경을 수행하지 않았다.

## 고정 O1 기준과 실제 증거

- 일관 백업: 17:05:29–17:06:44 KST. 아카이브 34,085항목 전수 검증, 웹루트 일반 파일 28,799개 추출·재읽기 해시 일치. 원본 SQL/config를 운영 DB에 복원하지 않았다.
- DB: 원본 SQL을 빈 시험 DB에 한 번 import. 원본 48테이블 모두 InnoDB, 테이블 집합·공개10/초안113/첨부375 대조 통과. 원본 theme/plugin 파일과 Kadence·활성 플러그인16개 등 주요 설정을 비교했다. 안전 승인 마커 1테이블은 시험 전용이다.
- 정제: 정확한 5개 옵션 원문 보존, 승인된 자격증명/식별정보 정리 및 loopback URL 치환만 적용. 정제 후 본문·첨부·중요 설정 기준값 대조 통과. 원본 SQL은 변경하지 않았다.
- WordPress7.0.4/PHP8.2.33 실제 시작. 최종 내부 HTTP 검사는 17:50:30–17:50:40 KST에 홈·글·분류·REST, 원문 제목/H2/대표 문단 대조를 통과했다.
- 미디어: 첨부375개의 고유 파일 참조2,025개 해시 일치·누락0. 대표 원본/생성 이미지2개를 실제 HTTP 바이트 대조 및 디코딩했다. 모든 미디어를 HTTP로 요청했다고 주장하지 않는다.
- 격리: 공개 포트 없이 network none, DB TCP off·전용 Unix 소켓, readonly root·capability 제거. 실제 외부 연결 차단, 메일 false, cron veto, Action Scheduler guard 검사 통과. 안전 검사 종료 이후 및 최종 HTTP 이후 별도 큐 검사도 기준값과 일치했다.
- 최종 자원 관측 17:51:06 KST: DB116.3MiB, WordPress117.4MiB, 각각256MiB 상한, 네트워크 I/O0.
- 종료 영수증 직접 대조: 17:53:54–17:53:57 KST에 정확한 시험 WordPress/DB 컨테이너가 exit0·OOM false로 종료됐고, 전용 daemon/slice도 중지됐다. 남은 전용 프로세스0·소켓 없음, 삭제0이며 DB 볼륨·백업·증거는 보존했다. 규칙 해시/forwarding은 수정된 시작 기준값과 일치했다. 운영 타이머는 active다.
- 17:54:24 KST 원본 서버 재확인: Apache/MariaDB active, 임시 gate 없음·옛 잠금 연결0·공개 HTTPS200. 원본과 전송본의 SQL/아카이브/manifest SHA가 최초 값과 일치했다. 종료 후 가용 디스크 약64GB·메모리 약3.1GiB였다.

## 실패·복구와 판정 한계

최초 테이블 비교의 정렬 차이, 정상 평문을 JSON으로 읽은 실행기 오류, 96MiB CLI 번역 로딩 메모리 실패는 원래 영수증을 보존했다. DB import·정제를 반복하지 않았다. 마지막 안전성 검사만 Apache를 멈춘 상태에서 CLI128MiB로 실행해 통과했으며, 컨테이너256MiB·CPU0.35·전체 slice1GiB 제한은 유지했다. **Apache PHP 설정은96MiB 그대로**이고 그 설정에서 최종 HTTP 검사를 다시 통과했다. CLI96MiB 안전 검사 성공으로 바꾸어 기록하지 않는다.

최초 방화벽 비교는 원본 기준값 미보존으로 차이가 트래픽 카운터뿐이었음을 사후 입증하지 못한다. 수정된 재기동 검사는 시간 주석·카운터를 제외한 규칙과 forwarding 전후 일치를 확인했다. 호스트 방화벽을 덮어써 맞추지 않았다.

백업 전체 실행74.6초는 연속 측정한 외부403 지속시간이 아니다. 백업 시작부터 최종 HTTP 완료까지 약45분12초에는 환경 준비·조사·수정이 포함되므로 운영 장애의 복구시간/RTO로 제시하지 않는다.

실행자는 최종 WordPress 로그에 Universally API key 미설정 알림 1건을 보고했다. 외부 연동은 의도적으로 제외했으며, 이를 DB 오류나 외부 연동 정상 복원 증거로 해석하지 않는다.

이번 PASS 범위는 **격리된 공개 WordPress 복원**이다. 원본 config의 비밀값과 Host 의존 동작은 시험용 안전 설정으로 대체했고 uid/gid는 보존하지 않았다. phpMyAdmin·관리자 쓰기·메일/외부 연동·예약 실행·DNS/TLS·운영 reverse proxy·브라우저 레이아웃/JavaScript·실제 장애 전환·장기 운영은 동등성 검증 대상이 아니다. 전체 인프라 복원 성공이라고 부르지 않는다.

근거: [고정 인수 기준](quality99-acceptance.md), [자연 예약 검증](natural-schedule-verification.md), [스냅샷 독립 검증](consistent-snapshot-verification.md), [복원 검증 보고](isolated-recovery-verification.md). 비공개 실행 영수증 SAFETY-128-RESULT·FINAL-HTTP-RESULT·FINAL-RESOURCE-STATS·CLOSURE-RESULT 및 종료 후 DB/큐·미디어 검사 원본을 직접 대조했다. 원시 SQL/config와 민감값은 이 문서에 포함하지 않았다.
