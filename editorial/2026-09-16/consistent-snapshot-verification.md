# 일관 스냅샷 독립 검증 — 2026-09-16

검증자: `quality_cycle_audit`. 원격 작업은 읽기 전용이었다. 운영 중단·잠금·설정 변경·DB 복원·아카이브 추출은 하지 않았다. 비밀정보나 SQL/config 원문을 출력하지 않았다.

## 판정

**스냅샷 아카이브 무결성 및 운영 복귀 확인 PASS. 전체 WordPress 복원 성공은 아직 미검증이다.**

실행자의 private `result.json`은 `consistent=true`, `service_recovered=true`, `captured=true`, failure/recovery_failure 없음으로 기록되어 있다. 시작 2026-09-16 08:05:29 UTC, 종료 08:06:44 UTC(한국 시각 17:05:29–17:06:44), 실행자가 계산한 전체 경과 상한은 74.6초다. 이 값은 독립적으로 매 순간 외부 가용성을 측정한 정확한 403 지속시간과는 다르다.

실행 중 DB 잠금 유지·작성자 배제·전후 manifest 일치는 실행 스크립트와 영수증에 근거한다. 독립 검증자는 종료 후 서비스 상태 및 저장된 아카이브를 확인했다. 따라서 실행 당시 모든 순간을 별도 관측했다고 주장하지 않는다.

## 종료 후 직접 관측

2026-09-16 08:08 UTC 이후 읽기 전용 SSH 및 공개 HTTPS 조회:

- 잠금 연결 ID `472142`의 `information_schema.PROCESSLIST` 개수 **0**.
- 해당 작업의 임시 Apache gate 파일 **없음**.
- Apache **active/running**, MainPID **159685**: 작업 전 직접 관측한 PID와 동일.
- MariaDB **active/running**, MainPID **3318**: 작업 전 직접 관측한 PID와 동일.
- 공개 `https://huntlab.app/` 응답 **200**.
- `/etc/apache2`, `/etc/php`의 현재 재귀 manifest가 실행 전 기록과 **일치**. 임시 파일 생성/제거로 바뀌는 디렉터리 mtime만 제외했으며 파일 SHA·크기·mode·uid/gid·파일 mtime·symlink target은 비교했다.
- 자동화 호스트의 daily/deep 타이머 **둘 다 active**, 다음 예약 각각 9월 17일 04:00/10:00 KST. 두 발행 서비스는 **inactive**. 타이머가 원래 active였다는 사전 기록은 실행자 기록에 의존하며, 현재 active 및 다음 예약은 독립 조회했다.

## 아카이브와 source manifest 전수 비교

원격 private 아카이브를 Python `tarfile`의 `r|gz` 모드로 읽었다. 파일을 추출하거나 운영 경로에 쓰지 않았다. 각 regular member를 1MiB씩 읽어 SHA-256을 계산하고, source manifest의 기대값과 비교했다.

| 항목 | 결과 |
|---|---:|
| Source manifest 항목 | 34,085 |
| 아카이브 고유 항목 | 34,085 |
| 일반 파일 | 28,993 |
| 디렉터리 | 4,980 |
| 심볼릭 링크 | 112 |
| 실제 해시 계산한 파일 바이트 | 513,764,757 |
| 누락·추가·중복·안전하지 않은 경로 | 0 |
| 파일 SHA·크기·형식 불일치 | 0 |
| uid/gid·mode·초 단위 mtime 불일치 | 0 |
| symlink target 불일치 | 0 |

검증 완료 시각은 **08:08:53 UTC**, 아카이브 전수 비교와 산출물 해시 계산 소요 **6.62초**. tar의 초 단위 mtime은 source manifest의 ns 값을 초 단위로 내림하여 비교했으므로 ns 정밀도 보존을 주장하지 않는다.

SQL 파일은 **9,713,287 bytes**, CREATE TABLE 문 **48개**, dump 완료 표식 존재로 확인했다. 실행 전 테이블 개수도 **48**이다. 이는 구조적 완결성 보조 확인이며 SQL import·데이터 관계·실제 애플리케이션 복구 검증을 대체하지 않는다.

private 보관 디렉터리는 **0700**, 확인한 SQL/archive/manifest/result 파일은 **0600**이다. 아카이브 **239,689,624 bytes**, source manifest **10,443,020 bytes**.

## 산출물 SHA-256

| 파일 | SHA-256 |
|---|---|
| `files.tar.gz` | `e274da8dcb243664ebe8f3116ca1719f97f845a6ca08447d5aa83109d1cd8d13` |
| `wordpress.sql` | `709e21cd6ab3234569755ac7f6e858eb37aaa0ec17191efb2d82cac669e4596c` |
| `source-manifest.json` | `106c3a1ce713d04e9b832437e8c2823e5b51f823ac220b858d62e3403794d563` |
| `result.json` | `471aac3c5de31488edb73b18b69efff3a265901363a51dcbbc197650d5c4c47f` |

## 다음 검증 경계

- 격리 환경의 DB import, PHP/WordPress bootstrap, 대표 HTML·REST·원본/생성 미디어 HTTP 및 파일 관계 검증은 아직 하지 않았다. **O1 전체 복구 점수 가점 근거로 완료 처리하지 않는다.**
- 아카이브에 포함된 이 작업 전용 임시 gate는 복원 단계에서 정확한 경로와 내용으로 식별하여 제외해야 한다. 원래 운영 설정을 임의로 제거하면 안 된다.
- 원본 SQL/config는 비밀정보·개인정보를 포함할 수 있다. 공개 Git·보고서 첨부 금지, 격리 실행 전 자격증명/외부 통신 차단 및 로컬 환경 치환 검토가 필요하다.
- 외부 브라우저 렌더링·DNS/TLS·실제 서버 전환·장기 운영은 이번 아카이브 검사 범위 밖이다.
