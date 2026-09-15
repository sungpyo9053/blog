# 99점 개선 사이클 — 발행 신뢰성과 실제 운영 검증

검토자: quality_cycle_pipeline (AI). 원격은 읽기만 수행했다. 관측 서버 HEAD는
`170c6ba70c419501171ae741b318a2fb6f4ac38d`이며 아래 수정은 로컬에서만 검증했다.
자기 작성 코드의 최종 독립 승인은 root 검토가 필요하다. 점수를 올리기 위해
새로운 평가 기준이나 장기 관측 결과를 만들어내지 않았다.

## 실제 04시 브리핑 / 07시 카카오

- 04시 실행 `20260915T190000Z-f9f05f973b`의 manifest는 `complete=true`,
  `analysis_complete=true`, `publications_complete=true`다. 모드는 `briefing_only`이고
  심층글 expected/published count 0은 이 모드의 정상 결과다.
- manifest 생성은 04:10:38 KST, SHA-256은
  `baca59064939ed3a2ec372c9de2d73264efeab878f325777321ce520786ea1d2`.
- 공개 REST에서 briefing ID **750**, status `publish`, 생성/수정
  `2026-09-15T19:10:38Z` 확인. [당일 공개 브리핑](https://huntlab.app/briefing/2026-09-16/)
  HTTP 200이며 당일 날짜·핵심 신호·키워드·확인 타임라인·실제 AWS Organizations
  제목이 렌더링돼 있다. 저장된 REST content는 88자 렌더링 지시문이므로 그 길이를
  실제 본문 분량으로 평가하지 않았다.
- `huntlab-daily-pipeline.service`는 04:10:40 KST 종료, ExecMainStatus 0이다.
  타이머 활성만으로 완료라고 주장하지 않고 manifest/공개 결과와 대조했다.
- `output/kakao-reports/2026-09-16-07.json`은 07:00:01 KST, `status=sent`, slot 07.
  내용은 당일 브리핑 발행 완료와 위 공개 URL이며 실제 공개 상태와 일치한다.
  SHA-256: `56f971bdf2756d335fa217f733139fb72e949e381ac81ee436a04c04f5d8378f`.
- 카카오 서비스는 07:00:03 KST 종료, ExecMainStatus 0. 발송 코드는 MCP 응답의
  성공 문구를 확인한 뒤 sent를 저장한다. 이는 발송 확인이지 사용자가 메시지를
  읽었다는 증거는 아니다. 추가 메시지 전송·재시도는 수행하지 않았다.
- 기본 urllib 요청은 공개 REST에서 403이었으나 운영 보고 코드와 동일한 명시적
  User-Agent의 GET은 성공했다. 실패를 지우지 않고 클라이언트 차이로 구분한다.

## 수정 전 실패로 재현한 결함 2개

1. **경쟁 실행이 가짜 unknown 실행을 생성**: 실제 PipelineLock 소유자가 있는
   상태에서 다른 `--apply` CLI가 잠금 거부되면 기존 main의 예외 처리가 별도
   result.json을 unknown으로 만들었다. Publisher에 도달하지 않은 이 기록이 이후
   전체 발행을 차단할 수 있다. 회귀 테스트는 수정 전 실제 실패했다.
   수정은 잠금 아래 새 실행을 소유한 경우에만 실패 결과를 기록하는 것이다.
   잠금 거부·기존 run 재호출·읽기 전용 감사 실패는 다른 실행 기록을 변경하지 않는다.
2. **PID 파일 초기화 경쟁**: 첫 실행이 O_EXCL로 lock 파일을 만든 직후 JSON 기록을
   멈추면, 두 번째 실행이 빈 파일을 stale로 오인해 지우고 동시에 획득했다.
   스레드 barrier로 정확한 창을 고정한 테스트가 수정 전 실패했다.
   수정은 삭제하지 않는 `.guard` sidecar의 비차단 flock을 실행 수명 동안 유지해
   초기화와 stale 회수를 직렬화하는 것이다. PID 파일은 구버전 실행의 실제 생존
   확인을 위해 유지한다. malformed/비양수 PID는 stale로 추정하지 않고 차단한다.

운영 주의: `.guard`는 비어 있어도 정상인 영구 동기화 inode이며 실행 중 삭제하면
안 된다. malformed PID 파일은 자동 회수하지 않고 운영자가 실제 프로세스 상태를
확인해야 한다. 새 코드 배포는 구버전 잠금 코드가 병렬로 시작하는 혼합 버전 창을
피해야 한다. 이번 검토에서 서버 잠금 삭제·서비스 중지·기동은 하지 않았다.

독립 감사가 추가로 발견한 P2도 보강했다: owner PID JSON이 `[]`로 훼손되면
release가 AttributeError로 끝나 guard descriptor가 남는 경우다. release의 finally에서
guard를 해제하고 PID를 양의 int/dict로 엄격히 검사한다. 문자열·bool·소수·null은
stale로 변환하지 않는다. 손상 기록 보존·반복 release·legacy alive/dead PID·PID 기록
실패 시 두 descriptor 해제 회귀를 추가했다. fork된 자식의 descriptor 상속이나
임의 OS/분산파일시스템까지 안전하다고 검증 범위를 확대하지 않는다.

## 장애 주입 검증 범위

| 경계 | 이번 검증 | 결과 |
| --- | --- | --- |
| POST 성공 뒤 응답 소실 | mock 서버 반영 후 TimeoutError | 한 번만 호출, unknown 보존, 자동 다음 실행 차단 |
| 성공 후 confirmed progress 저장 실패 | OSError 주입 | 기존 unknown 보존, 다음 발행 차단 |
| 성공 후 publication receipt 저장 실패 | OSError 주입 | confirmed progress 1 유지, 당일 한도 차단 |
| 감사 GET 실패 후 read-only CLI resume | 예외 주입 | Publisher 미호출, 기존 progress 보존, 실행 result 추가 없음 |
| PID 파일 쓰기 중 경쟁 | 실제 스레드 barrier | contender 차단, owner 보존 |
| 실제 프로세스 경쟁·사망 | 별도 Python 프로세스와 flock, SIGKILL | 생존 중 차단, 종료 뒤 PID 회수 및 재획득 |

응답 소실·디스크 오류는 **로컬 모의 주입**이며 운영 WordPress에 POST를 보내거나
운영 디스크를 고장 낸 것이 아니다. 기존 readonly resume 성공·하루 1건·unknown
격리·epoch hash 변조 차단 테스트도 유지했다. 실패를 0으로 바꾸어 통과시키지 않았다.

## 고정 발행 신뢰성 27/30의 남은 증거를 다루는 방법

현재 확인 가능한 항목은 오늘의 실제 브리핑/보고 완료, 중복 위험 실패 주입,
독립 코드 검토, 운영 배포 SHA와 서버 회귀다. 앞의 두 항목은 이번에 검증했으나
새 코드의 독립 승인·배포·서버 회귀는 아직 root 절차가 남아 있다. 따라서 로컬
테스트 숫자만으로 30/30 또는 전체 99점으로 변경하지 않는다.

장기간 무인 실행 성공률, 실제 외부 장애 빈도, 사용자 열람·광고 성과는 시간이
필요한 별도 관측이다. 하루의 실행 결과나 과거 기록을 변조해 이 항목을 채울 수
없다. 현재 검증할 수 있는 사고 경계와 장기 성과를 분리해 점수를 결정해야 한다.
