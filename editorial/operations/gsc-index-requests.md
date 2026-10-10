# GSC 색인 생성 요청 기록 (하루 약 10건 한도, API 불가 → 사용자 Chrome UI 자동 조작)

방법: Chrome(로그인됨)에서 GSC 홈의 aria-label "huntlab.app에 있는 모든 URL 검사" 입력 → System Events key code 36(실제 Enter, Chrome frontmost 확인 필수) → "색인 생성 요청" 버튼 JS click → 본문에 "색인 생성 요청됨" 확인.
우선순위: URL is unknown / Discovered-not-indexed 중 최신·검색수요 큰 글. 이미 요청한 URL은 2주 내 재요청 안 함.

## 2026-10-11 (10건)
- ros2-colcon-build-ram-how-many-gb-nav2-measured
- ros2-local-setup-vs-setup-bash-fresh-terminal-package-count
- en/ros2-local-setup-bash-vs-setup-bash-ros2-command-not-found
- tf-frame-offset-transform-direction-double-error
- ros2-real-time-factor-vs-real-time-computing-deadline
- colcon-build-slow-overlay-colcon-ignore-symlink-install-order
- colcon-build-executor-sequential-memory-budget
- ros2-liveliness-lease-duration-vs-deadline-topic-stall
- ros2-message-filter-laser-stamp-clock-mismatch
- ros-camera-optical-frame-axis-mapping-check
- (사이트맵) hunt_en-sitemap.xml 제출 — 기존엔 sitemap.xml만 제출, EN 사이트맵은 인덱스에 미포함

## 상태 기준선 (10/11 URL Inspection API): 46편 중 PASS 3
