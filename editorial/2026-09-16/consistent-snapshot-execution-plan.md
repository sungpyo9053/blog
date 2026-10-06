# 일관 WordPress snapshot 실행 계획 — root 승인 전 미실행

읽기 전용 환경 조회만 했다. 아래 stop·lock·dump·tar·manifest는 제안이며 실행하지
않았다. round2 편집/발행과 겹치지 않도록 root가 작업창을 독점해야 한다.

## 현재 확인한 쓰기 경로와 공간

- WordPress 호스트 `43.203.28.225`, Apache prefork + **mod_php**. PHP-FPM 서비스는
  없다. 조회 당시 Apache parent 1개/worker 5개와 MariaDB가 동작했고 별도 PHP CLI
  프로세스는 없었다. 자동화 호스트는 별도이므로 그쪽 Publisher/배포도 동결 대상이다.
- Apache ExecStop은 `apachectl graceful-stop`, TimeoutStop 90초, Restart on-abort,
  KillMode mixed. `systemctl stop`을 무기한 무해한 drain이라고 간주하면 안 된다.
- WordPress 서버에 cron daemon/crontab 명령·사용자 crontab spool은 없었다.
  `/etc/cron.d/php`는 존재하고 phpsessionclean timer가 활성이다. WordPress WP-Cron은
  웹 요청에서 실행될 수 있으므로 웹 PHP를 중단해야 한다. 다른 systemd timer는
  apt/dpkg/man-db/tmpfiles/e2scrub/fstrim/certbot이며 WordPress 전용 CLI timer는 없었다.
- DB 48테이블 모두 InnoDB. config는 `/var/www/wp-config.php`, 웹루트 밖에 있다.
- 원격 여유 **34,180MiB**. 웹루트 사용량579MiB, uploads102MiB/plugins360MiB/themes25MiB.
  실제 일반파일 28,799개, 513,510,405 bytes. 이미 압축된 확장자 파일만
  159,897,287 bytes이며 나머지353,613,118 bytes다. symlink/special-file은 별도
  manifest 항목으로 기록해야 한다.

## 무중단 대안 판단

DB global read lock은 DB 쓰기를 막을 뿐, PHP가 파일을 먼저 만들고 DB 쓰기에서
대기하는 상황을 막지 않는다. 따라서 FTWRL + tar만으로 무중단 일관성을 주장할
수 없다. 동일 볼륨의 조정된 스토리지 snapshot/LVM 또는 모든 작성자를 막는 검증된
쓰기 전용 게이트가 현재 확인되지 않았다. 첫 snapshot에서는 **짧은 Apache 정지
창**이 가장 명확하다. 독자 GET까지 유지하려면 별도 검증된 정적 캐시/유지보수
서빙 구성이 필요하고 이것은 별도 변경이므로 이번 제안에 몰래 추가하지 않는다.

## 승인 후 정확한 절차

1. **창 확보**: root가 콘텐츠 수정·플러그인/테마 배포·관리자 작업을 일시 중지한다.
   자동화 호스트의 Publisher 관련 서비스가 비활성인지 실제 MainPID/cgroup을
   확인하고 예정 타이머를 기록한다. 실행 중 Publisher를 강제 종료하지 않는다.
   새 입력/외부 작성자가 있으면 snapshot을 미룬다. round2 쓰기도 창 밖으로 둔다.
2. **원상 상태 기록**: Apache 및 관련 타이머의 active/enabled, 현재 코드/설정 파일
   SHA, WP counts, source free space를 기록한다. root만 읽을 수 있는 새로운
   snapshot 폴더를 mode0700으로 생성하고 산출물0600/umask077을 사용한다.
3. **PHP drain**: `apachectl graceful-stop`을 호출하고 모든 해당 Apache 프로세스가
   종료됐는지 실제 PID/cgroup으로 확인한다. 새로운 요청은 이때부터 연결 실패할
   수 있어 명시적 downtime이다. 잔존 worker/독립 PHP/업로더가 하나라도 있으면
   dump로 넘어가지 않는다. 30초 drain 예산을 넘으면 snapshot 실패로 처리하고
   root가 요청 상태를 확인해 복구한다. `systemctl stop`의 90초 강제 kill에 맡겨
   진행하지 않는다. graceful-stop이 끝난 서비스만 나중에 start한다.
4. **동일 세션 global read lock**: root unix-socket MariaDB client를 자식 프로세스로
   열고 stdin을 유지한다. 해당 연결에서 `FLUSH TABLES WITH READ LOCK;` 뒤
   `SELECT CONNECTION_ID(), 'SNAPSHOT_LOCK_HELD';` 응답을 확인한다. 그 client를
   종료하거나 명령별로 재접속하지 않는다. 일반 client credential을 명령 인자에
   넣지 않는다. 10초 내 lock 획득이 확인되지 않으면 client를 종료하고 중단한다.
5. **lock 동안 수집**: 같은 parent 작업의 별도 client로
   `mariadb-dump --single-transaction --skip-lock-tables --quick`를 실행한다.
   48개 테이블/뷰·트리거·이벤트·프로시저 존재 여부를 기록하고 해당 객체도 보존한다.
   웹루트 **전체** 및 상위 config, 재현에 필요한 Apache/PHP 설정을 별도 archive로
   수집한다. archive가 포함하지 않은 원본 경로에서 독립 manifest를 생성해 파일
   경로/종류/크기/SHA/mode/uid/gid/symlink target을 고정한다. secret 파일 원문은
   manifest에 넣지 않는다. PHP session/tmp/cache는 snapshot 범위를 명확히 적고,
   단순 예산 절감을 위해 활성 플러그인이나 uploads 파일을 제외하지 않는다.
6. **결과 검증**: dump/tar/hash subprocess가 모두 종료0, tar 목록 완결,
   manifest와 수집파일 집합 일치, lock connection 살아있음, snapshot 이전/이후
   승인 범위 파일·DB 지표가 변하지 않았음을 확인한다. 잠금 세션이 중간에 끊겼거나
   파일 변경 경고가 발생하면 snapshot은 불일관 후보로 격리하고 사용하지 않는다.
7. **finally 복구**: 같은 DB client에서 `UNLOCK TABLES` 후 종료한다. 신호/오류 시에도
   stdin 닫기/프로세스 종료로 연결을 반드시 해제한다. MariaDB 서비스 자체는
   stop/restart하지 않는다. Apache가 처음 active였으면 `systemctl start apache2`
   후 MainPID/HTTP/PHP를 확인한다. 처음 inactive였던 서비스를 임의로 켜지 않는다.
   자동화 타이머도 원래 상태로만 복귀시킨다. failed snapshot 때문에 DB/파일을
   production에 복원하는 행동은 하지 않는다.
8. **창 종료 후 전송**: snapshot SHA를 고정한 뒤 서비스를 정상화하고 전송/추출/
   Docker 복구 검증은 오프라인으로 진행한다. 추출·Docker 시간까지 downtime에
   포함하지 않는다. 성공 snapshot과 실패한 partial은 구분해 보존한다.

## 예상 시간·250MB 예산

관측 파일 수/크기 기준 예상값일 뿐, 압축 벤치마크를 실행한 값은 아니다.
drain 0–30초, DB lock/dump 1–10초, 약514MB 파일 읽기·압축·독립hash 30–120초를
가정하면 **약1–3분 downtime**을 계획해야 한다. 디스크/CPU 부하에 따라 길어질
수 있어 승인된 wall-clock watchdog과 중단 경계를 root가 정한다. DB lock 120초
예산을 초과하면 partial을 실패로 남기고 즉시 unlock/서비스 복귀한다. 초과를
무시하고 장시간 운영을 묶지 않는다.

250MiB 전송 산출물 예산은 **가능성이 있으나 보장 불가**다. 이미 압축된 파일
160MB를 제외한 약354MB가 대략4:1로 줄고 DB·manifest까지 작아야 충족한다.
낮은 gzip 레벨의 압축률을 미리 가정해 승인하지 않는다. 승인된 실행에서 산출물
크기를 계측하고 총250MiB를 넘으면 업로드하지 말고 root에 알린다. 예산을 맞추려고
소스 일부를 삭제·누락하거나 전체 snapshot으로 이름 붙이지 않는다. 원격 공간은
충분하므로 원격 완결 snapshot을 먼저 보존한 후 전송 예산 확대를 검토할 수 있다.
250MiB는 압축 전송 예산이며 로컬 Docker 이미지·추출514MB·DB·실행로그 예산과
별개다. 로컬 여유5.2GiB는 이미지 준비 후 다시 확인해야 한다.

## 민감정보와 사고 복구

원본 SQL/config는 애플리케이션 비밀과 개인정보를 포함할 수 있다. HTTPS/SSH 전송,
개인 소유0700/0600 보관, Git 제외, stdout/보고서에 값 출력 금지. 원본 config와
unsanitized DB는 웹 컨테이너에 mount하지 않는다. root가 격리 복사본에서 자격증명
제거와 local URL 치환을 검토한 뒤 내부망 Docker 계획을 실행한다.

lock 해제/Apache start가 실패하면 즉시 중단 상태와 현재 MainPID/HTTP를 보고한다.
자동 재시작 루프로 감추지 않는다. parent/SSH 연결이 끊어지는 경우를 대비해
snapshot 작업은 root가 검토한 서버측 finally/짧은 watchdog으로 복구하도록 설계해야
하며, 클라이언트 연결이 살아있을 것이라는 가정에 의존하지 않는다.
