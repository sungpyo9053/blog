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

## 2026-10-13 (1건, 2번째에서 할당량 — 24시간 롤링으로 보임)
- ros2-distro-choice-iron-humble-remaining-support-months
- 미완(10/14 우선): en/ros-2-humble-vs-jazzy-vs-iron-which-distro-before-eol, en/colcon-build-slow-overlay-colcon-ignore-symlink-install-measured, en/ros2-transient-local-late-joiner-lifespan, ros2-sim-time-zero-uninitialized-first-dt-spike, ros2-transient-local-late-joiner-sample-age-lifespan, ros2-qos-deadline-period-compatibility, ros2-sim-time-real-time-factor-latency-budget, ros-pose-covariance-row-major-index, gaussian-policy-action-bound-margin (+ 2026-10-13-plan.md 6~10번)
- 교훈: 10/12 오후 요청 뒤 다음 날 오전엔 1건만 통과. 하루 요청 수를 줄이고 10:37 고정 시각에 몰아서 하는 게 할당량에 맞다.

## 2026-10-12 (5건, 6번째에서 일일 할당량 도달)
- ros2-docker-discovery-range-static-peers-combinations
- en/ros2-nodes-cant-see-each-other-ros-automatic-discovery-range
- en/ros2-tf-frame-offset-doubled-static-transform-publisher
- en/ros2-liveliness-vs-deadline-detect-stopped-sensor-topic
- en/ros2-message-filter-dropping-message-clock-mismatch
- 미완(10/13 우선): ros2-distro-choice-iron-humble-remaining-support-months, en/ros-2-humble-vs-jazzy-vs-iron-which-distro-before-eol, en/colcon-build-slow-overlay-colcon-ignore-symlink-install-measured (Enter 미반영 타임아웃), en/ros2-transient-local-late-joiner-lifespan, ros2-sim-time-zero-uninitialized-first-dt-spike (할당량)
- 상태 (10/12 09:00 URL Inspection): 48편 중 PASS 13
- 교훈: 일일 할당량이 약 5~10건으로 보임(10/11 10건 성공, 10/12 5건 후 할당량). 입력 직후 Enter는 무시될 수 있어 5초 대기·재입력 후 Enter.

## 상태 기준선 (10/11 URL Inspection API): 46편 중 PASS 3
