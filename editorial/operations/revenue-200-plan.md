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
- MIDDAY `37 10 * * *`: [HuntLab $200 MIDDAY] 10:00 KO+EN 공개 확인(공개 REST)·schedule 서비스 정상 확인. GSC 색인 요청 최대 10건: 러너 URL Inspection으로 미색인 목록 → gsc-index-requests.md에 14일 내 요청 없는 최신 글 우선. 로그인된 GSC 창이 front window인지, Enter 전 Chrome frontmost인지 확인. 기록·커밋, 카톡 보고(로그아웃이면 로그인 요청).
- DAILY `17 21 * * *`: [HuntLab $200 DAILY] GitHub/Discourse 정확히 맞는 열린 이슈 1건 이하 답글(코드·로그 확인, disclosure, Discourse AI 표기), 그날 공개 글 네이버 요약 1편(원문 복사·쿠팡 링크 금지), 그날 평가(수익 기준 등급 + 다음 날 일정)를 카톡 보고. 다음 날 특별 작업이 있으면 YYYY-MM-DD-plan.md 작성.
- WEEKLY `7 10 * * 1`: [HuntLab $200 WEEKLY] 09:30 goal_report 결과 + GSC 색인 수로 마일스톤 판정, 미달 시 '미달 시 조치' 반영·주간 기록 추가, 쿠팡 실측 장비 글 1편 진행(측정 서버는 끝나면 반드시 삭제), 카톡 보고. 마지막에 CronList에서 [HuntLab $200 MORNING/MIDDAY/DAILY/WEEKLY]를 지우고 이 절의 cron식·내용으로 재등록(7일 만료 방지).
- 마일스톤 판정 일회성: 10/24 21:43, 11/30 21:43, 12/31 21:43 (이후 것은 12/31 판정 때 등록).
- 세션(터미널)이 꺼지면 크론도 사라진다. 서버 타이머(goal_report 월 09:30)는 계속 돈다.

## 주간 기록
- 10/12 (1주차): 방문 41·조회 71·검색유입 13, 구글 클릭 0·노출 4 → 10/24 목표 70의 58%(전주 34→41). 구글 색인 3/46 → 13/48 (10/11 GSC 수동 요청 효과로 보임). 마일스톤 기한 전이라 레버 유지. 쿠팡 2편: MoveIt 2 RAM 실측 스크립트 준비(experiments/colcon-ram-moveit2-real-build, Nav2와 같은 방법, 조건 default 16/8/4g + seq 8/4g) — AWS 로그인 만료로 측정 서버 생성은 사용자 `aws login` 대기. GSC 2차 요청은 구글 로그인 만료로 대기.
- SEO 점검(10/12): KO 글 title·description·canonical·BlogPosting 스키마·hreflang 정상, 사이트맵 인덱스에 hunt_en 포함(11편). 고친 것: #935 자동 잘린 요약 → 직접 쓴 요약. 10/12 밤 추가 수정: 영어판 og:locale en_US(huntlab-english.php aioseo_facebook_tags 필터), 영어판 스키마 BlogPosting(AIOSEO aioseo_options_dynamic의 postTypes.hunt_en을 post 설정으로 복사, 백업 WP호스트 /tmp/aioseo_dyn_backup_20261012.json).
- 10/13 실수익(사용자 콘솔 확인): 애드센스 $0.00, 쿠팡 0원. 이후 평가·주간 보고는 추정 RPM 대신 editorial/operations/revenue-actual.tsv의 실제 값을 쓴다.
