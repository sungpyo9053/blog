# 월 $200 달성 계획 (2026-10-11 수립)

## 출발점 (10/11 실측)
- GA4 지난 4주 방문: 주 17 → 17 → 34 (조회 31 → 61). 하루 약 5명.
- 구글: 28일 노출 800·클릭 6, 최근 7일 노출 5·클릭 0. 46편 중 색인 3편.
- $200/월 = 애드센스만이면 RPM $3 가정 시 월 약 6.7만 조회(현재의 약 250배).

## 판단
애드센스 단독으로는 빨라야 2027년 중반이다. 그래서 세 가지를 합쳐 목표로 간다:
애드센스(트래픽) + 쿠팡 장비 글(실측 기준) + 영어 유료 가이드($19~29, 월 7~10부면 $150~200).
날짜 약속은 하지 않고, 마일스톤마다 판정해 계속할지 바꿀지 정한다.

## 마일스톤 (scripts/goal_report.py MILESTONES와 같게 유지)
| 기한 | 주간 방문 목표 | 미달 시 조치 |
|---|---:|---|
| 10/24 | 70 (하루 10) | 1~2명/일이면 주제 재논의 (2주 유입 실험 판정) |
| 11/30 | 210 (하루 30) | 색인률 50% 미만이면 글 생산 줄이고 기존 글 보강·내부링크로 전환 |
| 12/31 | 700 (하루 100) | 애드센스 실제 RPM 확인, 가이드 출시 여부 결정 |
| 2027-03-31 | 2,100 (하루 300) | 월 $50 미만이면 전략 재평가 |
| 2027-06-30 | 7,000 (하루 1,000) | 월 $200 판정 |

## 반복 실행 (자동)
- 매일 10:00 공개 / 02:00·14:00 글감 준비 (서버, 기존)
- 매일 21:17 Claude: GSC 색인 요청 최대 10건(미색인 우선) + GitHub/Discourse 적합 이슈 1건 이하 + 네이버 요약 1편
- 매주 월 09:30 서버: goal_report.py 카톡 (방문·조회·검색유입·구글 클릭·추정 월수익 vs 마일스톤)
- 매주 월 10:07 Claude: 주간 보고 해석, 다음 주 레버 조정, 쿠팡 실측 장비 글 1편 준비(MoveIt 2 RAM → SSD 용량 → 라즈베리파이 5)
- 가이드 사전신청 1명 생기면 가이드 본문 작성 시작

## 사용자 몫 (막히면 카톡으로 요청)
- 애드센스·쿠팡 실제 수익 숫자는 콘솔 접근이 필요 (API 승인 시 자동화)
- 가이드 결제 플랫폼 계정·가격

## Claude 세션 크론 (SSOT — WEEKLY가 매주 이 절대로 전부 재등록)
- MORNING `43 7 * * *`: [HuntLab $200 MORNING] 러너 실패 유닛, 02:00 prepare 결과(sudo tail logs/systemd-editorial-prepare.out.log), 예약 글 수(posts·hunt_en status=future). 버그면 고치고(품질 반려는 우회 금지) push 전 prepare inactive 확인. 그날 계획 문서(editorial/operations/YYYY-MM-DD-plan.md)가 있으면 아침 항목도 수행. 카톡 보고.
- MIDDAY `37 10 * * *`: [HuntLab $200 MIDDAY] 10:00 KO+EN 공개 확인(공개 REST)·schedule 서비스 정상 확인. 사이트맵은 러너 huntlab-sitemap-submit.timer(10:20)가 API로 자동 제출하니 결과만 확인(journalctl). URL 단위 색인 요청은 API가 없어(Indexing API는 채용·라이브 전용, 금지) GSC 웹에서만 되므로 그날 공개된 EN 1편 + KO 1편만 요청(백로그 일괄 요청 중단). 로그인된 GSC 창이 front window인지, Enter 전 Chrome frontmost인지 확인. 기록·커밋, 카톡 보고(로그아웃이면 로그인 요청).
- DAILY `17 21 * * *`: [HuntLab $200 DAILY] (1) 커뮤니티 배포 1건: 실측 글(우선 MoveIt·Nav2 RAM 영어판) 1편을 Reddit r/ROS → ROS Discourse(AI 사용 표기 필수) → 국내 ROS 커뮤니티 순으로 하루 1곳. 각 커뮤니티 자기홍보 규칙을 먼저 읽고, 글 본문에 측정 숫자와 결론을 직접 써서 링크 없이도 읽히게 하고 끝에 (disclosure: my blog). 같은 글을 같은 곳에 두 번 올리지 않는다. Chrome에 로그인돼 있지 않으면 카톡으로 로그인 요청. 기록은 editorial/operations/distribution-log.md. (2) GitHub/Discourse 정확히 맞는 열린 이슈 1건 이하 답글(코드·로그 확인, disclosure, Discourse AI 표기). (3) 그날 공개 글 네이버 요약 1편(원문 복사·쿠팡 링크 금지). (4) 평가: 상승/보합/하락을 실수익(revenue-actual.tsv)과 방문자(GA4 activeUsers, 세션 아님)로만 매기고 다음 날 일정과 함께 카톡 보고. 다음 날 특별 작업이 있으면 YYYY-MM-DD-plan.md 작성.
- COMMUNITY `23 * * * *`(매시 스캔): [HuntLab $200 COMMUNITY] distribution-log.md에서 오늘(KST) 답글 수를 세어 3개면 즉시 종료. 아니면 Reddit(u/Wooden_One_4001: r/ROS, r/robotics)과 ROS Discourse(sungpyo9053, AI 사용 표기 필수)에서 최근 질문(r/ROS new, r/robotics ROS 검색, Discourse latest) 중 이전 스캔 이후 새로 올라온 것만 보고, 우리 실측·글로 정확히 답할 수 있는 것에 답글(하루 합계 최대 3개, 같은 시간에 1개). 맞는 게 없으면 아무것도 쓰지 않고 카톡도 보내지 않는다. 답은 본문에 숫자·명령까지 다 쓰고, 링크는 질문과 정확히 같은 글일 때만(답글 10개 중 링크 1개 이하, Reddit 9:1 원칙). 자기 글 게시는 하루 1개 이하(DAILY 몫). 같은 질문·스레드에 두 번 쓰지 않는다. 글이 숨겨지거나 삭제·경고를 받으면 그날 중단하고 카톡 보고. 기록은 distribution-log.md(날짜·곳·주소·링크 여부·반응). 로그아웃이면 카톡으로 로그인 요청.
- WEEKLY `7 10 * * 1`: [HuntLab $200 WEEKLY] 09:30 goal_report 결과 + GSC 색인 수로 마일스톤 판정, 미달 시 '미달 시 조치' 반영·주간 기록 추가, 쿠팡 실측 장비 글 1편 진행(측정 서버는 끝나면 반드시 삭제), 카톡 보고. 마지막에 CronList에서 [HuntLab $200 MORNING/MIDDAY/DAILY/WEEKLY]를 지우고 이 절의 cron식·내용으로 재등록(7일 만료 방지).
- 마일스톤 판정 일회성: 10/24 21:43, 11/30 21:43, 12/31 21:43 (이후 것은 12/31 판정 때 등록).
- 세션(터미널)이 꺼지면 크론도 사라진다. 서버 타이머(goal_report 월 09:30)는 계속 돈다.

## 주간 기록
- 10/12 (1주차): 방문 41·조회 71·검색유입 13, 구글 클릭 0·노출 4 → 10/24 목표 70의 58%(전주 34→41). 구글 색인 3/46 → 13/48 (10/11 GSC 수동 요청 효과로 보임). 마일스톤 기한 전이라 레버 유지. 쿠팡 2편: MoveIt 2 RAM 실측 스크립트 준비(experiments/colcon-ram-moveit2-real-build, Nav2와 같은 방법, 조건 default 16/8/4g + seq 8/4g) — AWS 로그인 만료로 측정 서버 생성은 사용자 `aws login` 대기. GSC 2차 요청은 구글 로그인 만료로 대기.
- SEO 점검(10/12): KO 글 title·description·canonical·BlogPosting 스키마·hreflang 정상, 사이트맵 인덱스에 hunt_en 포함(11편). 고친 것: #935 자동 잘린 요약 → 직접 쓴 요약. 10/12 밤 추가 수정: 영어판 og:locale en_US(huntlab-english.php aioseo_facebook_tags 필터), 영어판 스키마 BlogPosting(AIOSEO aioseo_options_dynamic의 postTypes.hunt_en을 post 설정으로 복사, 백업 WP호스트 /tmp/aioseo_dyn_backup_20261012.json).
- 10/13 실수익(사용자 콘솔 확인): 애드센스 $0.00, 쿠팡 0원. 이후 평가·주간 보고는 추정 RPM 대신 editorial/operations/revenue-actual.tsv의 실제 값을 쓴다.
- 10/13 방향 수정: 방문 지표를 세션→방문자(activeUsers)로 바꾸니 지난 7일 방문자 19, 검색 유입 2, 수익 $0. 구글 노출을 기다리는 것만으로는 부족해 DAILY에 커뮤니티 배포(하루 1곳)를 추가했다. 10/20까지 하루 방문자 10명 미만이면 주제 재선정을 사용자와 논의.
- 10/13 진단: 9/1 이후 GSC 노출 1838·클릭 12는 거의 전부 삭제(410)된 옛 일반 글(멜론 849노출 등)에서 나옴. EN 12편(최고 10일)은 노출 3, KO ROS는 ~0. 목표 지표를 영어 검색 유입으로 정함(사용자: "영어라도 검색해서 오는 사람 있으면 되지"). 조치: GSC 요청은 EN 우선, 커뮤니티 배포는 EN 링크(백링크 효과), 주간 지표에 EN 노출 추가. 10/20 판정: EN 노출 3 → 수십 이상인지.
- 10/13 사용자 지시: 커뮤니티(Reddit·Discourse)를 매일 집중. 계정 정지 시 채널을 잃으므로 답글 위주(최대 3개/일)+자기 글 1개/일로 운영.
- 10/13 네이버 노출 점검: 3개 검색어 모두 네이버 블로그 탭 1위(1호·3호). 구글과 달리 색인 병목 없음 → 네이버 요약 계속.
