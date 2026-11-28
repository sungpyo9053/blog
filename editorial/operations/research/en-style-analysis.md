# EN 문제 해결 글 문체·이미지 분석 + EN 스타일 가이드 v1

- 작성: 2026-11-28, Market Researcher
- 수집 방법: WebSearch, WebFetch, curl(--max-time 30)만 사용. 브라우저·로그인·게시 없음.
- 수치 측정: 페이지 HTML이나 공식 API 원문을 받아 스크립트로 셌다. 코드 블록은 빼고 영어 단어 수와 문장 수를 셌으며, 표 셀과 목록 때문에 오차가 있는 근사치다.
- 표기: 확인하지 못한 내용은 「unverified」로 적었다. 인용은 출처 페이지마다 한 문장까지만 넣었다.
- 주의: WebSearch는 Google이 아니다(미국 기준 검색 엔진). 아래의 "검색 상위"는 이 엔진 결과이며, Google 순위가 같은지는 「unverified」다.

---

## 0. 우리 글 3편 (비교 기준)

| 항목 | O1 rate.sleep | O2 colcon RAM | O3 generator already executing |
|---|---|---|---|
| URL | https://huntlab.app/en/ros-2-rclpy-rate-sleep-blocks-forever-fix/ | https://huntlab.app/en/colcon-build-how-much-ram-nav2-16gb-8gb-4gb-measured/ | https://huntlab.app/en/rclpy-generator-already-executing-multithreadedexecutor-callback-groups/ |
| 제목 | "ROS 2 rclpy rate.sleep() Blocks Forever: Why and How to Fix" (증상 문구 포함) | "How Much RAM Does colcon build Need? Nav2 Built at 16, 8 and 4GB" (질문형, 오류 문자열은 없음) | 오류 문자열을 따옴표로 그대로 넣은 긴 제목 |
| 첫 3문장 | "Short answer:" 한 문장 → 캡션 → 1인칭 실험 서술 | 증상과 오류 문자열 → "how much RAM" 질문 → "I built … five times" | 코드(오류 출력)가 먼저 나오고 → "Short answer:" → 해결 코드 |
| 단어 수(코드 제외) | 약 2,676 | 약 862 | 약 2,687 |
| 평균 문장 길이 | 17.5단어 | 18.1단어 | 22.6단어 |
| 인칭 | I(측정) + you(독자) + 명령형(해결) | 같음 | 같음 |
| 코드 블록 | 6 | 1 | 3 (앞부분에 몰려 있음) |
| 버전 표기 | rclpy Jazzy 7.1.12, 소스 줄 번호 | ros:jazzy digest, Nav2 커밋 해시 | 배포판 3개와 패키지 버전, 이미지 digest, 측정일 |
| 근거 제시 방식 | 8개 케이스 × 5회 측정 표, 감시 타이머 수치 | cgroup memory.peak 표 | 성공/전체 횟수(10/10 형식), 중앙값 ms |
| 헤딩 | 라벨형과 질문형이 섞임 | 라벨형, 조건형("If you have …") | 증상·라벨형 |
| TL;DR | 있음(Short answer) | 있음(H2 Short answer) | 있음(Short answer + 증상 표) |
| FAQ | H3 5개 | H3 5개 | H3 5개 |
| 마무리 | Limits → Reproduce → Sources → 푸터 | Reproduce → 관련 글 → 푸터 | Version notes → Not tested → FAQ → 측정 환경 → 푸터 |
| 이미지 | 2장: 제목 카드(alt=제목), 표 이미지(캡션 고정) | 2장, 같은 구성 | 2장, 같은 구성. 카드 alt가 `"ValueError`에서 끊겨 있음(따옴표 이스케이프 버그) |

이미지는 실제로 열어 확인했다. 카드는 베이지 배경에 제목 글자만 있는 1600×900 그래픽이다. glance 이미지는 본문 측정 표를 그림으로 렌더링한 것인데, O1 것은 마지막 행이 "max"에서 잘려 있다(https://huntlab.app/wp-content/uploads/2026/10/glance-925.webp). 터미널 스크린샷, 다이어그램, rqt_graph, 차트는 세 글 모두 0장이다.

---

## 1. 레퍼런스 소스 5곳 측정

### 소스 1. 공식 문서: docs.ros.org (Jazzy)

- 렌더링된 페이지는 Anubis 봇 차단 때문에 curl과 WebFetch 모두 막혔다. 그래서 같은 내용의 공식 원본(ros2/ros2_documentation, jazzy 브랜치의 .rst)으로 측정했다.
  - Using Callback Groups: https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html (원본 https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/How-To-Guides/Using-callback-groups.rst)
  - Installation troubleshooting: https://docs.ros.org/en/jazzy/How-To-Guides/Installation-Troubleshooting.html
  - About Executors: https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html
- 제목: 오류 문자열이 아닌 주제 라벨이다("Using Callback Groups", "Installation troubleshooting"). 하위 헤딩에는 증상명이 들어간다("Out of memory", "Segmentation fault when using pyenv", "Avoiding deadlocks").
- 첫 3문장: 범위와 전제를 먼저 말한다. 인용: "This page is meant as a guide on how to use callback groups efficiently."(Using-callback-groups). 바로 답부터 주는 구조는 아니다.
- 평균 문장 길이: 24.0단어(callback groups), 24.5단어(troubleshooting). 우리 글보다 길다.
- 인칭: 3인칭 서술과 "one"이 주로 쓰인다. troubleshooting 문서는 you가 33회, we가 4회 나오고 I는 0회다.
- 코드: callback groups 문서는 code-block 약 30개로 밀도가 높고, "The problem → Solution" 단계마다 console 출력을 보여 준다(402행 "we get the following outputs").
- 버전: URL의 배포판 경로(/en/jazzy/)로 표시한다. 본문에서 패키지 버전은 거의 말하지 않는다.
- 근거: 재현 데모 코드와 터미널 출력을 보여 준다. 측정 수치는 없다.
- TL;DR·FAQ: 없다. "In short:" 목록이 요약 역할을 한다. 마무리는 해결 코드 조합 나열로 끝나고 결론 문단은 없다.
- 이미지: Using-callback-groups 0장, Installation-Troubleshooting 0장, About-Executors 다이어그램 2장(executors_basic_principle.png, executors_scheduling_semantics.png). `.. image::`에 alt 지정이 없고 캡션도 없다.

### 소스 2. Q&A: robotics.stackexchange.com (구 answers.ros.org 이관분)

- 측정 페이지(Stack Exchange API로 본문 수집):
  - https://robotics.stackexchange.com/questions/103990 "how to use the rate.sleep function properly" (조회 3,119)
  - https://robotics.stackexchange.com/questions/97883 "c++: fatal MoveIt 2 error: Killed signal terminated program cc1plus compilation"
  - https://robotics.stackexchange.com/questions/99009 "Spinning multiple nodes across multiple threads"
- 검색 노출: answers.ros.org 원본 URL이 세 오류 쿼리 모두에서 WebSearch 상위를 차지했다(예: https://answers.ros.org/question/377848/ , https://answers.ros.org/question/391031/).
- 제목: 질문자가 쓴 오류 문자열이 그대로 들어간다(97883).
- 첫 문장: 진단을 바로 내린다. 인용: "This is a classic gcc error, it happens when the system runs out of memory."(97883 채택 답변)
- 길이: 답변이 짧다. 58단어(99009), 111단어(97883), 219단어(103990). 문장 수가 적고 목록이 많아 평균 문장 길이는 신뢰하기 어렵다(28~55단어로 나오지만 목록 결합 때문에 부풀려진 값).
- 인칭: "I would do it", "you're re-creating" 같은 1·2인칭 대화체다.
- 코드: 답변당 1~2개이고, 진단 한 줄 바로 뒤에 놓인다.
- 버전: 질문 쪽에만 있고, 답변에서는 거의 언급하지 않는다(97883은 "ROS2:"/"ROS1" 라벨로만 구분).
- 근거: 측정 없이 경험과 경력으로 말한다. "Originally posted by … with karma" 같은 메타 정보가 신뢰 신호 역할을 한다.
- 헤딩·FAQ·TL;DR: 없다.
- 이미지: 본문 이미지 0장. 이관 표시용 로고(alt "Rosanswers logo")만 있다.

### 소스 3. 독립 블로그: Rico's Nerd Cluster (ricojia.github.io)

- 선정 이유: "generator already executing"과 rate.sleep 두 쿼리의 WebSearch 결과에 연속으로 나온 개인 블로그다.
- 측정 페이지:
  - https://ricojia.github.io/2024/11/27/robotics-ROS2-ros2-rclpy-executor-callback-model
  - https://ricojia.github.io/2024/11/25/robotics-ROS2-ros2-executor-callback-model
- 참고: 처음 계획한 Articulated Robotics(https://articulatedrobotics.xyz/tutorials/docker/devices-docker)는 받은 HTML에 본문이 없어 측정하지 못했다(JS 렌더링으로 추정, 「unverified」). The Construct 블로그 글은 검색에서 찾지 못했다.
- 제목: "[ROS2 Foundation] Ros2 Rclpy Executor Callback Model". 개념 라벨이고, 오류 문자열은 H3에만 있다("ValueError: generator already executing").
- 첫 문장: 정의부터 말한다. 인용: "rclpy.executors.MultiThreadedExecutor is implemented entirely in Python, not as a direct wrapper around the C++ rclcpp::executors::MultiThreadedExecutor."
- 평균 문장 길이: 29.5단어 / 28.3단어(마침표 없는 메모 문장이 많아 근사치).
- 인칭: we/you 혼용, 메모체.
- 코드: 11개 안팎으로 매우 많다(Rouge 테이블 때문에 pre가 3배로 잡혀 33개로 나옴). rclpy 소스 발췌가 중심이다.
- 버전: 거의 없다. 배포판 명시도 없다.
- 근거: 소스 코드 인용과 GitHub 이슈 링크. 측정은 없다.
- 헤딩: 라벨형. "Issues" 아래에 오류 문자열을 H3로 둔다.
- TL;DR·FAQ·결론: 없다.
- 이미지: 11/27 글 0장. 11/25 글은 스크린샷 1장(postimg.cc 외부 호스팅, alt="" 빈 값, 캡션 없음).

### 소스 4. GitHub 이슈 스레드

- 측정 페이지(GitHub API로 본문과 댓글 수집):
  - https://github.com/ros2/rclpy/issues/1313 "Incompatibility with calling spin_until_future_complete while in callback" (closed, 댓글 11)
  - https://github.com/ros2/rclpy/issues/1181 "Service client sometimes deadlock …" (closed, PR #1188로 해결)
  - https://github.com/moveit/moveit2_tutorials/issues/899 "High RAM usage during colcon build" (closed)
- 제목: 증상 서술형. 오류 문자열은 본문 코드 펜스 안에 둔다.
- 첫 부분: 템플릿 필드(OS, Installation type, Version or commit hash, DDS)가 먼저 나온다. 환경 정보가 서론보다 앞선다.
- 길이: 이슈 본문 143~481단어, 댓글 5~80단어.
- 인칭: I/we 대화체.
- 코드: 본문에 펜스 1~7개. 로그와 트레이스백 원문을 그대로 붙인다.
- 버전: 커밋 해시까지 적는다(1313: rolling 43198cb…, 899: 20be397…).
- 근거: 재현 절차("Steps to reproduce"), 기대 동작과 실제 동작, 로그.
- 해결 문장: 메인테이너의 한 줄 결론. 인용: "Use coroutines instead."(1313, sloretz)
- 이미지: 세 스레드 모두 0장.

### 소스 5 (추가 요청). dev.to

- 반응 수 확인: dev.to 공개 API(`/api/articles?tag=ros2|ros|robotics&top=3650`, `/api/articles/{user}/{slug}`)로 직접 셌다. ROS 2 문제 해결 글 가운데 반응이 높은 글은 찾지 못했다. 태그 상위 글(반응 65, 62, 55 …)은 에세이, AI 데모, 뉴스였다(예: https://dev.to/javz/why-learning-basic-robotics-made-me-a-better-software-engineer-in-the-age-of-ai-fdh).
- 검색 노출 확인: 오류 문자열로 WebSearch(Google 아님)를 돌려 dev.to가 나오는지 봤다. 측정 대상은 다음과 같다.

| 글 | 반응/댓글 | 검색 노출 | 단어 | 평균 문장 | 코드 | 이미지 |
|---|---|---|---|---|---|---|
| https://dev.to/tsadarsh/xmlrpcclientfault-fault-1-class-rclpyrclpypybind11invalidhandlecannot-use-destroyable-because-destruction-was-3f35 (2022) | 3/0 | 오류 문자열 쿼리 1위 | 54 | 11.8 | 1 (트레이스백 원문) | 0 |
| https://dev.to/admantium/radu-realsense-d435-installation-troubles-with-ros2-72 (2022) | 6/0 | "realsense d435 ros2 installation problems" 1위 | 921 | 16.4 | 13 | 2 (rqt_graph, RViz 빈 화면 스크린샷, alt 빈 값, 캡션 없음) |
| https://dev.to/vmodal_ai/nvidia-jetson-ros-2-lidar-building-an-autonomous-navigation-system-1lb1 (2026-11) | 0/0 | 미확인 | 1,021 | 15.6 | 25 | 0 |

- 제목: tsadarsh 글은 오류 문자열 전체가 제목이다. admantium 글은 시리즈명과 증상("Installation Troubles").
- 첫 문장: tsadarsh는 환경과 명령을 먼저 말한다. 인용: "After sourcing `. /opt/ros/humble/setup.bash` and running `ros2 topic list`, I got the following error:". admantium은 1인칭 여정 서사로 시작하며 실패를 그대로 인정한다("ultimately failed").
- 버전: admantium은 "Ubuntu 20.04 LTS, ros2-foxy, ros2-realsense v3.2.2 && librealsense-v2.48.0" 형태로 본문 앞부분에 적는다.
- 헤딩: tsadarsh는 "## Solution" 하나뿐이다. admantium은 시도 순서형(First Approach / Second Approach / Conclusion).
- 대량 생산형 패턴: vmodal_ai 계정은 같은 형식("Building … with …")의 글을 2026-11-22~26 닷새 사이 15편 올렸고 반응은 모두 0이다(API `/api/articles?username=vmodal_ai`). Jetson 글은 "Step 1"부터 "Step 15"까지 번호 헤딩, "What You Will Build"와 "Prerequisites" 목록, 실제 장치 출력이 없는 범용 문제 해결("ROS 2 command not found", "Package not found")로 이뤄져 있다. 인용: "Learn how LiDAR data flows through ROS 2 and into localization, mapping, obstacle avoidance, and navigation."

**판정: dev.to는 문체 모델로 부분적으로만 적합하다.**
1. 도메인 권위 효과가 있다. 반응 3개에 54단어짜리 글이 오류 문자열 쿼리 1위였다. 순위가 글의 품질보다 dev.to 도메인과 제목의 오류 문자열 완전 일치에서 왔을 가능성이 크다(인과는 「unverified」). 우리 도메인(huntlab.app)이 같은 형식을 따라 해도 같은 효과는 기대하기 어렵다.
2. 참고할 점은 두 가지다. 하나는 tsadarsh 글처럼 오류 문자열을 원문 그대로 제목에 넣고 환경을 첫 문장에 밝히는 것이다. 다른 하나는 admantium 글처럼 실패를 기록하고 실제 rqt_graph·RViz 화면을 보여 주는 것이다.
3. 피할 점은 vmodal_ai식 "Step N" 번호 헤딩, 범용 문제 해결 목록, 단기간 대량 발행이다. 공식 문서, SE 답변, GitHub 이슈와 비교하면 사실의 출처로서 신뢰도도 낮다. 사실 근거는 공식 문서와 소스 코드에서 가져오고, dev.to는 짧은 제목·첫 문장 형식만 참고하는 것을 권한다.

---

## 2. 비교 요약

| 항목 | 공식 문서 | SE 답변 | 독립 블로그 | GitHub 이슈 | dev.to | 우리 글 |
|---|---|---|---|---|---|---|
| 제목에 오류 문자열 | 하위 헤딩에만 | 있음(질문) | H3에만 | 본문 펜스 | 있음 | 2/3편 |
| 답부터 시작 | 아니오(범위 소개) | 예(1문장 진단) | 아니오(정의) | 아니오(환경 템플릿) | 예/아니오 혼재 | 예(Short answer) |
| 평균 문장(단어) | 24 | 짧은 답변 | 28~30 | 짧은 댓글 | 12~16 | 17.5~22.6 |
| 버전 명시 | URL 배포판 | 약함 | 없음 | 커밋 해시 | 본문 앞부분 | 매우 강함(digest) |
| 측정 수치 | 없음 | 없음 | 없음 | 로그만 | 없음 | 있음(반복 측정) |
| FAQ | 없음 | 없음 | 없음 | 없음 | 없음 | 매번 5개 |
| 이미지 | 개념 글에만 다이어그램 | 0 | 0~1 | 0 | 0~2 (실제 화면) | 매번 2장(제목 카드 + 표 그림) |

신뢰받는 ROS 2 문제 해결 글은 이미지가 거의 없다. 대신 코드, 로그, 터미널 출력이 근거 역할을 한다. 이미지를 쓰는 경우는 개념 다이어그램(공식 문서)이나 실제 도구 화면(rqt_graph, RViz)이다. 정형 FAQ 블록을 두는 소스는 하나도 없었다.

---

## 3. 우리 EN 글의 대량 생산 신호 (3편 상호 비교)

1. **같은 이미지 2장과 같은 캡션.** 세 편 모두 제목 카드(card-NNN.webp, 텍스트만 있는 그래픽)와 표 그림(glance-NNN.webp)을 같은 위치에 두고, 캡션도 "At a glance: the main measured table from this article. Full details below."로 똑같다. 표 그림은 본문 HTML 표와 내용이 겹치고, O1 것은 마지막 행이 잘려 있다.
2. **FAQ 개수가 항상 5개.** H3 질문이 정확히 5개씩이고, 답변이 본문 문장을 거의 그대로 반복한다. O2에서 "A real laptop also spends 3–4GB on the OS, browser and IDE"가 2번, "peaked at 2.7GiB and finished even at 4GB"가 2번 나온다.
3. **같은 뼈대 순서.** "Short answer"(문단 또는 H2) → 측정 → FAQ → "Reproduce it" → 푸터 "ROS 2 troubleshooting guide · How these articles are made"가 세 편 모두 같다. 헤딩 이름도 "Short answer", "FAQ", "Reproduce it"가 그대로 반복된다.
4. **같은 첫 문장 틀.** O1과 O3이 "Short answer: …"로 시작하고 O2는 H2 "Short answer"를 쓴다. 상단 공식이 같다.
5. **카드 alt가 기계적으로 생성됨.** alt가 제목 복사본이고, O3에서는 따옴표 때문에 `"ValueError`로 잘렸다. 사람이 검토하지 않았다는 신호이고, 접근성 결함이기도 하다.
6. 참고로 강점도 분명하다. 세 편 모두 "I didn't measure", "Not tested", "Limits of this measurement"처럼 한계를 적는다(O1 7회, O3 2회, O2 0회). 1인칭 실험 서술, digest와 커밋 해시는 다섯 소스 어디보다 강한 직접 경험 근거다. 문제는 내용이 아니라 겉 틀이 반복된다는 점이다.

### Google 공식 기준과의 연결

- 대량 생산 콘텐츠 남용(spam policies, https://developers.google.com/search/docs/essentials/spam-policies): "Scaled content abuse is when many pages are generated for the primary purpose of manipulating search rankings and not helping users." 우리 글은 측정이라는 고유 가치가 있어 이 정의에 바로 해당하지는 않는다. 다만 같은 틀이 반복되면 페이지끼리 구별이 덜 된다(해당 여부 판단은 「unverified」).
- 유용한 콘텐츠(https://developers.google.com/search/docs/fundamentals/creating-helpful-content): "Is the content mass-produced by or outsourced to a large number of creators, or spread across a large network of sites, so that individual pages or sites don't get as much attention or care?" FAQ 5개 고정, 같은 캡션, 깨진 alt가 "attention or care"가 부족하다는 신호로 읽힐 수 있다.
- 생성형 AI 콘텐츠(https://developers.google.com/search/docs/fundamentals/using-gen-ai-content): AI 사용 자체보다 검토가 핵심이다. 이 페이지는 정확성 검토가 "alternate texts for images"에도 적용된다고 적는다. O3의 깨진 alt가 바로 이 검토 항목에 걸린다.
- 이미지 alt(https://developers.google.com/search/docs/appearance/google-images): "Avoid filling alt attributes with keywords (also known as keyword stuffing) as it results in a negative user experience and may cause your site to be seen as spam."

AI 문장을 사람 글처럼 위장하는 작업은 권하지 않는다. 할 일은 글마다 실제로 달라야 할 부분(증상, 측정, 실패, 한계)이 구조에 드러나게 하는 것이다.

---

## 4. EN 스타일 가이드 v1

전제: 지어낸 경험 금지(Docker에서 실제로 실행한 것만 주장), 텍스트·이미지 복제 금지, 사실은 공식 출처, 기존 제목 변경 금지, AI 사용 고지 줄 없음.

### 글쓰기 규칙 (10)

1. **첫 문단 = 진단 한 문장 + 실제 해결 한 줄.** SE 채택 답변처럼 원인을 먼저 말한다("This is a classic gcc error …" 형식). "Short answer:" 라벨은 고정하지 않고, 라벨 없이 쓰거나 글에 맞게 바꾼다.
2. **두 번째 문장에 환경을 적는다.** GitHub 이슈 템플릿과 dev.to tsadarsh 글처럼 배포판, 이미지, 실행 명령을 앞에 둔다. digest와 전체 버전 목록은 끝의 측정 환경 블록에 둔다.
3. **오류 문자열은 원문 그대로 코드 블록에 넣는다.** 독자가 자기 터미널 출력과 대조할 수 있게 트레이스백이나 로그 몇 줄을 실제 실행 결과에서 붙인다(공식 문서 "we get the following outputs" 방식).
4. **헤딩은 그 글의 증상과 실험에서 만든다.** "Short answer / FAQ / Reproduce it" 공통 뼈대를 모든 글에 쓰지 않는다. 공식 troubleshooting 문서처럼 증상명을 헤딩으로 쓴다.
5. **FAQ는 본문이 다루지 못한 실제 질문이 있을 때만 둔다.** 개수를 고정하지 않고(0~4개), 본문 문장을 반복하는 답은 쓰지 않는다. "Questions this answers"에 실제 SE·이슈 링크를 다는 O3 방식이 더 낫다.
6. **평균 문장 길이는 15~22단어를 유지하되 변화를 둔다.** 진단과 지시는 짧게, 원인 설명은 길게 쓴다. 공식 문서(24단어)보다 짧은 지금의 수준이 적절하다.
7. **인칭: 측정은 I, 해결은 명령형, 독자 상황은 you.** "We"는 쓰지 않는다(1인 측정이므로). 해보지 않은 것은 "I didn't test …"로 쓴다. O2처럼 한계 문장이 0개인 글을 만들지 않는다.
8. **실패와 잘못 짚은 경로를 그대로 적는다.** O3의 "This one cost me a wrong result"와 admantium의 "ultimately failed"는 직접 경험의 가장 강한 증거다. 실제 있었던 실패만 쓴다.
9. **사실 주장에는 공식 출처를 붙인다.** docs.ros.org, rclpy 소스 줄 번호, GitHub 이슈와 PR 번호. 블로그나 dev.to는 사실 근거로 쓰지 않는다.
10. **마무리는 글마다 다르게 쓴다.** 다음 행동 한 줄(예: "If X still happens, check Y")이나 열린 문제(O3 "I didn't find out where the first reply goes")로 끝낸다. 공통 푸터 링크는 사이트 템플릿에 두고, 본문 끝 문장은 반복하지 않는다.
11. **제목은 바꾸지 않는다.** 새 글에서는 오류 문자열을 가능한 한 원문 그대로 제목 앞쪽에 넣는다(SE, dev.to 상위 글의 공통점).

### 이미지 규칙 (5)

1. **이미지는 실제로 실행해서 얻은 것만 쓴다.** 터미널 출력은 이미지보다 텍스트 코드 블록을 먼저 고려한다(복사하고 검색할 수 있어서). 상위 소스 대부분이 이미지 0장이다.
2. **이미지가 꼭 필요한 경우는 텍스트로 대신할 수 없는 화면뿐이다.** 실제로 띄운 rqt_graph, RViz, `docker stats` 그래프, 측정값으로 직접 그린 차트(예: RAM 상한별 최대 사용량)가 여기에 해당한다. 개념 다이어그램은 공식 문서처럼 직접 그린 것만 쓰고, 남의 그림은 쓰지 않는다.
3. **본문 HTML 표를 그림으로 복제하지 않는다.** glance 표 그림은 중복이고 잘림 결함도 있다. 쓰더라도 HTML 표를 정본으로 두고, 그림은 요약 차트로 바꾼다.
4. **alt는 사람이 쓴 설명문으로 만든다.** 무엇을 측정한 화면인지 적고(예: "rqt_graph showing /talker and /listener with no connection on Jazzy"), 제목 복사와 키워드 나열은 피한다. 따옴표를 이스케이프하고, 발행 전에 alt를 확인한다.
5. **캡션은 그 이미지에서 무엇을 봐야 하는지 한 문장으로 쓴다.** 모든 글에 같은 캡션 문구를 쓰지 않는다. 이미지는 관련 문단 바로 옆에 둔다(Google 이미지 가이드도 관련 텍스트 근처에 두라고 권한다: https://developers.google.com/search/docs/appearance/google-images).
6. **제목 카드는 og:image 용도로만 쓴다.** 본문 첫 이미지로 반복 노출할지는 사람이 판단한다(현재 형식이 순위에 미치는 영향은 「unverified」).

---

## 출처 목록

- 우리 글: 위 0절 URL 3개 (?nc=123으로 수집)
- docs.ros.org(Anubis 차단, 원본 rst로 측정): https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html , https://docs.ros.org/en/jazzy/How-To-Guides/Installation-Troubleshooting.html , https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html , https://github.com/ros2/ros2_documentation/tree/jazzy/source
- Robotics SE: https://robotics.stackexchange.com/questions/103990 , https://robotics.stackexchange.com/questions/97883 , https://robotics.stackexchange.com/questions/99009
- 독립 블로그: https://ricojia.github.io/2024/11/27/robotics-ROS2-ros2-rclpy-executor-callback-model , https://ricojia.github.io/2024/11/25/robotics-ROS2-ros2-executor-callback-model
- GitHub: https://github.com/ros2/rclpy/issues/1313 , https://github.com/ros2/rclpy/issues/1181 , https://github.com/moveit/moveit2_tutorials/issues/899
- dev.to: 1절 소스 5 표의 URL 3개 + https://dev.to/api/articles?username=vmodal_ai
- Google: https://developers.google.com/search/docs/essentials/spam-policies , https://developers.google.com/search/docs/fundamentals/creating-helpful-content , https://developers.google.com/search/docs/fundamentals/using-gen-ai-content , https://developers.google.com/search/docs/appearance/google-images
