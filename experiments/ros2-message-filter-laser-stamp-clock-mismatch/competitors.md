# 경쟁 글 대비 차별점: ros2-message-filter-laser-stamp-clock-mismatch

검색어: `"Message Filter dropping message" frame laser "for reason" ROS 2`, `Message Filter dropping message use_sim_time timestamp tf slam_toolbox`, `"Message Filter dropping message" "earlier than all the data in the transform cache"`, 한국어 `Message Filter dropping message 해결 slam_toolbox tf use_sim_time`, `"Message Filter dropping message" 블로그 원인 tf`, `ROS2 메시지 필터 드롭 "Message Filter dropping message" 라이다 tf 타임스탬프`. 한국어 검색 결과는 모두 영어 포럼·이슈였고, 한국어 전용 해설 글은 찾지 못했다.

1. Robotics Stack Exchange 103632 — https://robotics.stackexchange.com/questions/103632/message-filter-dropping-message-frame-laser-at-time (원문 페이지 403. 내용은 [Stack Exchange API](https://api.stackexchange.com/2.3/questions/103632?site=robotics&filter=withbody)와 answers 엔드포인트로 읽음, 2023-08-22 작성, 채택 답변 없음)
   - 다루는 것: RPLidar + slam_toolbox. 로그는 `frame 'laser' at time 1692328002.091 for reason 'discarding message because the queue is full'`이다. 답변 1(3점)은 base→laser tf가 없어서 대기열이 넘친다고 보고 slam_toolbox 설정의 base_frame을 확인하라고 한다. 답변 2(1점)는 queue_size 개념을 설명하고 `ros2 topic echo`로 마지막 스탬프와 드롭된 스탬프를 비교하라고 권한다.
   - 빠진 것: 비교한 차이를 어떻게 해석하는지(크기·부호), tf 쪽 스탬프와 비교해야 한다는 점, 같은 queue-full 사유가 미래 스탬프 대기에서도 생긴다는 점이 없다.
   - 이 글이 더할 것: 1692328002.091은 시스템 시계 범위(2023-08-18 UTC)다. tf 스탬프도 같은 범위면 시계 문제가 아니므로 답변 1의 tf 트리 점검으로 가고, tf가 작은 sim 값이면 레이저만 시스템 시계라는 판정 흐름을 준다(질문자 사례의 원인을 단정하지는 않음).
2. The Construct 포럼 18510 — https://get-help.theconstruct.ai/t/another-explanation-for-the-error-info-1647531775-937463391-rviz-message-filter-dropping-message-frame-camera-bot-base-link-at-time-2936-389-for-a-reason-the-time-stamp-on-the-message-is-earlier-than-all-the-data-in-the-transform-cache/18510 (2022-08-01)
   - 다루는 것: 시스템 시각(약 1659319692)과 시뮬레이션 시각(약 2930)의 기준점이 달라 RViz가 메시지를 버린다는 설명이다. `get_clock().now()`를 로그로 찍어 비교하라고 권하며, 답글은 use_sim_time을 언급한다.
   - 빠진 것: 비교 대상이 tf 스탬프가 아니라 노드 now()다. 로그 대괄호 시각이 시스템 시각이라는 구분, 부호로 방향을 가리는 규칙, 반대 방향(레이저가 시스템 시각)에서는 사유가 'queue is full'로 바뀐다는 점, 사유 문구가 timeout에서도 나온다는 점이 없다.
   - 이 글이 더할 것: 두 방향을 같은 뺄셈의 부호로 구분하는 판정표와, 각 방향이 어떤 사유 문구로 이어지는지 geometry2 소스 줄 링크로 연결한 설명.
3. ros2/rviz#1615 — https://github.com/ros2/rviz/issues/1615 (Jazzy, 2025-10-26, open)
   - 다루는 것: 실물 로봇에서 `frame 'laser' at time 1761521468.848 for reason 'discarding message because the queue is full'`이 대량으로 찍힌다. 유지보수자는 "sim-time 또는 clock 관련일 수 있다"고 했고, 다른 답변은 RViz가 모르는 frame id이면 이 로그가 쏟아지니 tf 트리를 고치라고 하며 임시 static transform을 제시했다.
   - 빠진 것: 시계 문제와 tf 트리 문제를 가르는 확인 절차가 없다.
   - 이 글이 더할 것: 메시지 스탬프(대괄호 1761521469.862 vs at time 1761521468.848 → 둘 다 시스템 시계 범위)와 tf 스탬프의 차이로 시계 가설을 먼저 배제하는 절차.
4. SteveMacenski/slam_toolbox#491 — https://github.com/SteveMacenski/slam_toolbox/issues/491 (Foxy, 2022-04-27, closed)
   - 다루는 것: 실물 SICK 스캐너 드라이버를 그대로 두고 slam_toolbox만 `use_sim_time:=true`로 실행한 사례다. 로그는 `frame 'scan' at time 1651063566.627 for reason 'Unknown'`이고, 유지보수자는 "real odometry가 필요"라고만 답했다.
   - 빠진 것: 실물 장비 환경에서 use_sim_time:=true를 준 설정과 시계 규칙의 관계를 설명하지 않는다.
   - 이 글이 더할 것: "어떤 노드에 use_sim_time을 켤지는 /clock을 발행하는 시뮬레이터·bag 재생이 있을 때의 문제"라는 설계 문서 근거와, 노드별 `ros2 param get` 대조 절차. 이 사례의 원인을 단정하지는 않는다.
5. turtlebot/turtlebot4#611 — https://github.com/turtlebot/turtlebot4/issues/611 (Humble, 2025-06-25, closed)
   - 다루는 것: `frame 'rplidar_link' at time 1750840092.509 for reason 'the timestamp on the message is earlier than all the data in the transform cache'`가 찍힌다. 유지보수자는 Pi·Create3·원격 PC 간 시간 불일치를 의심하고 NTP(chrony) 설정을 안내했다.
   - 빠진 것: 같은 SystemTime끼리라도 컴퓨터가 다르면 차이가 생긴다는 점과 sim/system 혼동을 구분하는 기준이 없다.
   - 이 글이 더할 것: 차이의 규모로 "다른 기계의 시스템 시계 어긋남(수 초~수 시간)"과 "sim/system 혼동(수십억 초)"을 나누는 기준.

보조 참고(경쟁 글로 세지 않음): ros2/ros2#1653(Humble+Gazebo. 대괄호 1741356033 vs at time 3.960, odom 스탬프 68.7, 사유 queue full, 해결 미기재로 종결)은 "대괄호 시각을 빼면 오진한다"는 실제 예시로 쓸 수 있다.
