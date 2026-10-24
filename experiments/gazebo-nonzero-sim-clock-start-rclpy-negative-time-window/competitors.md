# 경쟁 글 대비 차별점: gazebo-nonzero-sim-clock-start-rclpy-negative-time-window

한국어 검색("use_sim_time 시뮬레이션 시간 0 음수", "가제보 시뮬레이션 시간 /clock 0초")에서는 이 질문을 직접 다룬 한국어 글을 찾지 못했다. 아래는 영어 상위 문서를 직접 읽은 결과다. robotics.stackexchange.com 페이지는 이 runner에서 HTTP 403이 나서, 같은 글을 Stack Exchange 공식 API(api.stackexchange.com, 200 OK)로 읽었다. 그래서 본문에서 SE URL을 출처 링크로 걸지 않는다(아래 "글 작성 시 주의할 점" 참고).

1. Robotics Stack Exchange — "How can you start gazebo with a non-0 simulated clock time?" (https://robotics.stackexchange.com/questions/104397/how-can-you-start-gazebo-with-a-non-0-simulated-clock-time, 2023-09-28, 답변 3개)
   - 다루는 것: 질문자는 시각을 빼는 계산이 시작 직후 에러를 낸다고 말한다. 채택 답변은 use_sim_time을 권하고, 빼기 전에 값을 검사하라고 하며, SDF `<state><sim_time>`을 제안한다. 다른 답변은 Classic `--initial_sim_time`(11.13+, reset 버그 11.14 수정)과 Gazebo `--initial-sim-time`(Garden 7.5, Harmonic 8.0)을 알려 주고, 빼기 비교를 덧셈 비교로 바꾸라고 조언한다.
   - 빠진 것: rclpy에서 어느 줄이 어떤 메시지로 예외를 내는지가 없다. 오프셋을 줘도 `/clock` 전 0 구간이 남는다는 점이 없다. 경계 결과 0과 tf2의 "최신" 의미, 실패 횟수 계산도 없다. SDF `<sim_time>` 제안은 다른 질문에서 동작하지 않았다는 보고가 있다.
   - 이 글이 더할 것: 소스 앵커로 예외 경로를 보인다. 오프셋의 효과 범위를 구분한다. ⌈W·f⌉−1과 W÷r 계산(검산 사례 포함)을 제시한다. `<=` 가드와 버전별 인자를 소스로 재확인한다.
2. Robotics Stack Exchange — "Unable to start gazebo with a non-0 simulated clock time in Gazebo Simulation" (https://robotics.stackexchange.com/questions/113871/unable-to-start-gazebo-with-a-non-0-simulated-clock-time-in-gazebo-simulation, 2024-11, Fortress 6.16 + Humble)
   - 다루는 것: SDF `<state><sim_time>100 0</sim_time>`이 반영되지 않는다는 보고다. 답변은 CLI 옵션이 Garden부터라 Fortress에는 없다고 말한다.
   - 빠진 것: Fortress 사용자의 대안(가드)이 없다. 시작 시각을 바꿔도 남는 구간 이야기도 없다.
   - 이 글이 더할 것: Fortress CLI 소스에 인자가 없다는 것을 직접 확인했다. 그래서 Humble/Fortress에서는 가드가 유일한 수단이라는 판단을 준다.
3. Robotics Stack Exchange(ROS Answers 이관) — "[ROS2] Using sim time parameter, nodes time is always zero" (https://robotics.stackexchange.com/questions/93094/ros2-using-sim-time-parameter-nodes-time-is-always-zero, 2019, Dashing)
   - 다루는 것: use_sim_time을 켜고 wall timer에서 `now()`를 찍으면 계속 0이다. 원인은 `/clock` 발행 플러그인 부재였다.
   - 빠진 것: 0이 "미초기화"라는 규칙, 그 0에서 빼기 계산이 예외가 된다는 연결이 없다.
   - 이 글이 더할 것: 이 사례가 "/clock 전 0 구간을 맞는 것은 wall timer 같은 다른 경로"라는 rcl 소스 해석의 공개 증상 예시가 된다.
4. LXRobotics — "Time synchronisation between ROS2 and Gazebo" (https://lxrobotics.com/blog/time-synchronisation-ros2-gazebo/, Alexander Entinger, 작성일 표기 없음)
   - 다루는 것: rclcpp Clock/Time/Duration 사용, 세 시계 종류, use_sim_time, ros_gz_bridge `/clock` 브리지.
   - 빠진 것: 시작 시각 0 문제, 음수 시각, 초기 시각 옵션, `/clock` 전 동작, 가드가 없다. rclpy도 다루지 않는다.
   - 이 글이 더할 것: 같은 설정 뒤에 남는 시작 직후 구간의 계산과 처리.
5. gazebo_ros_pkgs Wiki — "ROS 2 Migration: ROS Clocks and sim time" (https://github.com/ros-simulation/gazebo_ros_pkgs/wiki/ROS-2-Migration:-ROS-Clocks-and-sim-time, 2022-05-17 수정, 저장소 보관됨)
   - 다루는 것: Classic gazebo_ros_init의 `/clock` 발행(기본 10 Hz, publish_rate), 일시정지 시 `/clock` 미발행, reset_simulation으로 0 복귀.
   - 빠진 것: 초기 시각 옵션, 음수 시각, 미초기화 0이 없다. Classic 전용이고 보관 상태다.
   - 이 글이 더할 것: 현재 권장 조합(Jazzy + Harmonic) 기준 인자와 rclpy 동작.

판정: 경쟁 문서에는 시작 시각을 바꾸는 방법만 있다. 이 글은 "그래도 남는 구간"과 그 크기·처리법을 소스와 검산으로 더한다. 실행 실측은 이번 Research에 없다. 더하는 가치는 소스 대조, 정정된 산술 모델, 버전 확인이다. foundation_concept 계약상 충분하다고 판단해 READY로 둔다.
