# 전체 WordPress 복구 검증: 사전 진단과 승인용 계획

상태: **계획만 작성, 실행 보류**. 신규 snapshot·Docker image pull/build·network·container·volume을 만들지 않았다. 서버 변경도 없다.

## 실제 읽기 전용 진단

- 기존 `output/recovery-lab-20260916`: DB 48 tables, 원본 첨부파일 373개 SHA 일치. 기록에 `php_execution=false`, `whole_site_restore_verified=false`가 명시돼 있다. 이것은 전체 사이트 복구 증명이 아니다.
- 기존 원격 복구 자료는 자동화 서버가 아니라 **WordPress 서버 43.203.28.225**의 `/var/backups/huntlab/20260916-recovery`에 있다. DB 9,431,475 bytes, uploads archive 97,892,291 bytes. 로컬 transfer SHA와 함께 보존한다.
- 현재 웹루트 `/var/www/html`은 579MB. **실제 config는 한 단계 위 `/var/www/wp-config.php`**에 있어 웹루트만 tar하면 빠진다. config 값은 출력하지 않았고 복구 시 새 격리용 config로 대체해야 한다.
- 실제 WordPress 7.0.4, PHP 8.2.33, MariaDB 10.11.18, DB 48개 테이블 모두 InnoDB. 테마는 Kadence, permalink는 `/%postname%/`.
- active plugins 15개: AIOSEO, broken-link-checker, Duplicator, MonsterInsights, HuntLab TOC/brand/category/warm-editorial, Jetpack, OptinMonster, Universally, UserFeedback, WP Mail SMTP, WPConsent, WPForms. MU plugins는 performance와 AdSense verification 2개; object-cache/advanced-cache/db/sunrise drop-in은 현재 없다.
- PHP mysqli/PDO, curl, GD, mbstring, intl 대신 현재 출력된 확장 목록의 실제 보유 여부를 기준으로 호환 이미지를 정해야 한다. PHP 8.3 CLI만으로 Apache/PHP 8.2 웹 동작을 검증했다고 해서는 안 된다.
- 로컬 Docker 29.4.3, x86_64, 메모리 약 3.8GiB. 기존 실행 컨테이너 2개 및 모든 중지 컨테이너를 보존한다. cached MariaDB 10.11은 있으나 적합한 PHP 8.2 Apache/WordPress 이미지는 없다.
- **디스크 여유 5.2GiB, 사용률 98%**. 기존 자료 203MB 외 추가 이미지·전체 복사·DB·브라우저 캐시 비용을 계산하고 여유 하한을 정하기 전 실행하지 않는다. 다른 프로젝트 이미지/컨테이너 prune 금지.

## 실행 승인 전에 해결할 경계

1. DB transaction snapshot과 파일 tar를 따로 읽는 것만으로 동일 시점 일관성을 보증할 수 없다. root가 짧은 변경 동결 범위를 승인해야 한다: 자동 발행, 관리자 수정, 업로드/삭제, 플러그인 작업, cron 및 외부 작성자를 포함한다. 불가능하면 스토리지/DB 조정 snapshot 또는 비일관 snapshot임을 명시하고 full-DR 통과로 판정하지 않는다.
2. 이미지 확보/공간 예산, 포트 충돌, 자원 상한과 정확한 격리용 이름을 승인한다. 운영 자격증명이 담긴 원본 archive는 mode 0600/디렉터리 0700으로 로컬 보관하되 컨테이너에 mount하지 않는다.
3. WordPress DB에는 SMTP·OAuth·API 설정이 있다. 먼저 격리 DB만 `--network none` 상태로 복구한 후 허용된 설정 변경 목록으로 자격증명을 제거하고 cron/메일 큐를 비활성화한다. 원본 dump는 수정하지 않으며 변경 전후 값 대신 키 이름·해시·건수만 기록한다.

## 승인 후 실행 순서 (아직 미실행)

1. 동결 시각·실행자·출처 revision을 기록한다. 모든 InnoDB DB를 single transaction dump하고 웹루트 전체(core/themes/plugins/MU/uploads/.htaccess), 웹루트 밖 config 및 Apache/PHP 설정을 함께 보존한다. DB와 파일 수집이 동일 동결 창 안에 끝났음을 확인하고 독립 source manifest, 파일 SHA/크기, DB row counts, snapshot 해시를 작성한다. snapshot 종료 후 승인된 원상 복귀만 수행한다.
2. checksum으로 전송을 검증한다. 압축을 풀기 전 절대경로·`..`·특수파일·탈출 symlink를 검사하고 작업 전용 하위 폴더에만 추출한다. production config/SMTP/API 값은 실행 복사본에 들어가지 않도록 새 config와 안전화한 DB를 준비한다.
3. 예: `huntlab-dr-<unique>`라는 별도 Compose project/network/volume을 사용한다. **Docker internal network**, DB published port 없음, WP HTTP는 **127.0.0.1의 사전 확인한 빈 포트만** bind한다. 다른 네트워크 연결, Docker socket/호스트 홈/운영 파일 mount, privileged, host networking 금지. 메모리/CPU/PID 상한을 둔다.
4. 첫 PHP bootstrap 전에 `DISABLE_WP_CRON`, 자동 업데이트·파일 편집 금지, `WP_HTTP_BLOCK_EXTERNAL`, 빈 외부 허용 목록, 별도 salts와 DB credentials를 설정한다. MU safety plugin으로 `pre_http_request`와 `pre_wp_mail`을 차단한다. PHP sendmail을 무해한 sink로 설정하고 SMTP/API credentials를 제거한다. direct curl/socket은 WP filter를 우회하므로 internal network의 실제 egress 실패 검사도 선행한다. 내부 host/service 및 host gateway 접근도 최소화하고 DB 외 목적지 차단을 확인한다.
5. 브라우저는 컨테이너 egress 제한과 별개다. 로컬 브라우저 네트워크도 loopback만 허용하여 Google/광고/분석/원본 사이트 요청을 차단한다. 사이트 URL 치환은 serialized 값을 보존하는 도구로 격리 DB에만 수행하고 production host가 남은 리다이렉트/이미지/REST를 검출한다. 활성 플러그인 목록을 임의로 줄여 통과시키지 않는다. 격리 때문에 실패하는 통합 기능은 제외 사유로 기록한다.
6. MariaDB 건강·48개 이상 실제 snapshot table/row counts·WP/PHP 버전·필수 확장·테마·플러그인·설정 보존을 검증한다. 그 다음 PHP 실제 페이지: 홈, 카테고리, 대표 글/최신 글, 브리핑 CPT, REST, permalink, sitemap. 상태 200만 아니라 제목·본문 기준 문장·메타·내부 링크·카테고리·위젯 렌더링과 PHP fatal/warning을 검사한다.
7. 첨부 원본 **및 `_wp_attachment_metadata`가 참조하는 모든 generated size/srcset**를 DB 기준으로 열거한다. 경로 탈출·missing·SHA·MIME·실제 이미지 decode, HTTP 응답과 페이지 내 실제 로딩을 검사한다. 단순 uploads 파일 개수만 비교하지 않는다. DB reference와 source filesystem manifest가 각각 독립 기준이어야 한다.
8. cron·메일·외부HTTP를 시도하는 안전한 fixture에서 차단/무발송 증거를 남긴다. live 외부 전송을 허용해 통과시키지 않는다. 최종 보고서는 실제 통과한 로컬 페이지/설정/미디어와 미검증 SMTP·외부통합·DNS/TLS·실서버 복귀를 분리한다.

## 종료·판정

별도 project label로 정확히 생성한 자원만 정리하거나 승인된 기한까지 보관한다. 전체 Docker prune/down-all 또는 기존 컨테이너 삭제 금지. 백업 원본과 검증 결과는 보존한다. 성공해도 명칭은 **격리된 WordPress 애플리케이션 복구 검증**이며 DNS/TLS/클라우드 네트워크/실제 장애 전환·RTO/RPO 검증까지 포함한 완전 재해복구로 과장하지 않는다.
