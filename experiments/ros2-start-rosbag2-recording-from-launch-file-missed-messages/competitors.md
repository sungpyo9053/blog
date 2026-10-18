# 경쟁 글 대비 차별점: ros2-start-rosbag2-recording-from-launch-file-missed-messages

같은 질문으로 검색되는 상위 글을 2026-10-19에 직접 열어 읽었다.

1. [Robotics Stack Exchange — "[ROS2] Start rosbag2 recording from launch file"](https://robotics.stackexchange.com/questions/94391/ros2-start-rosbag2-recording-from-launch-file) (영어, 2020-01-14 질문, ROS Answers 이관. 본문은 Stack Exchange API로 확인. 페이지 자체는 예약 runner에서 접근 실패)
   - 다루는 것: 채택 답변(2020-01-17)이 `ExecuteProcess(cmd=['ros2','bag','record','-a'], output='screen')`와 Eloquent 이후 XML `<executable>`를 제시한다. 2026-03-08 답변은 Kilted(아마 Jazzy도)에서 `rosbag2_transport` `recorder` 노드와 `record.topics` 파라미터, 컴포넌트 방식을 보인다. 2021년 댓글은 Ctrl+C 시 녹화 프로세스가 exit code 2로 죽고 sqlite가 손상된 것 같다고 보고한다.
   - 빠진 것: 녹화기가 언제 실제로 구독하는지, 시작 지연·sim time 대기 동안 무엇이 빠지는지, latched 토픽의 durability 조건이 없다.
   - 이 글이 더할 것: 구독 시점 기준의 누락 계산 모델, 첫 `/clock` 전 구독 미생성(소스), 녹화기 QoS 선택 규칙과 0/1 대조.
2. [Automatic Addison — Record and Play Back Data Using ROS 2 Bag (Jazzy)](https://automaticaddison.com/record-and-play-back-data-using-ros-2-bag-ros-2-jazzy/) (영어, 2024-11-26, Addison Sears-Collins)
   - 다루는 것: CLI 녹화·재생·루프 재생, bag을 CSV로 바꾸는 Python 스크립트.
   - 빠진 것: launch에서 녹화하는 법 자체가 없다. sim time, QoS, 시작 지연 언급 없음. 예시 명령이 위치 인자(`ros2 bag record /mecanum_drive_controller/cmd_vel`)라 Jazzy에서는 deprecated 문법이다.
   - 이 글이 더할 것: launch 프로세스 구성과 배포판별 `--topics` 차이, 누락 계산.
3. [ZetaBank ROS 2 교육 자료 — 데이터 녹화 및 재생](https://zeta-edu-ros2.readthedocs.io/en/latest/courses/2.tutorial_cli_ros2/10.recording.html) (한국어, 작성자·날짜 표기 없음, Humble 관례)
   - 다루는 것: CLI `ros2 bag record <topic>`, `-o subset /turtle1/cmd_vel /turtle1/pose` 같은 기본 녹화.
   - 빠진 것: launch 녹화, sim time, QoS, 시작 시점 문제 전무.
   - 이 글이 더할 것: 한국어로 launch 녹화 + 시작 시점·sim time·durability를 한 흐름으로 설명.
4. [SAKIGAKE ROBO — ROS2講座⑥ rosbag2とrqtツール](https://sakigake-robo.com/ros2-6/) (일본어, 2025-10-27 게시 표기)
   - 다루는 것: `ExecuteProcess(cmd=['ros2','bag','record','/turtle1/pose','/turtle1/cmd_vel','-o','my_turtle_bag'], output='screen')` launch 예.
   - 빠진 것: 배포판 명시 없음, 위치 인자 문법, 시작 지연·sim time·QoS 언급 없음.
   - 이 글이 더할 것: 같은 구성에서 bag 앞부분이 비는 이유와 크기.
5. [Jeacson Snake — ROS2-019 rosbag2](https://blog.jeacsonsnake.com/learningNote/Ros2_Note/launch_rosbag2/2026_01_24.html) (중국어, 2026-01-24)
   - 다루는 것: CLI 녹화와 C++/Python 노드에서의 프로그램 녹화.
   - 빠진 것: launch 통합, sim time, QoS, 시작 지연 없음.
6. (참고, 공식) rosbag2 README "Using in launch"·"Simulation time" — 정답 문장은 있지만 두 절이 따로 있고, 시작 지연과 누락 수, 녹화기의 durability 선택 규칙은 설명하지 않는다.

판정: 읽은 상위 글은 모두 "띄우는 법"까지만 다룬다. 이 글은 실측이 아닌 계산 모델과 소스 근거로 "무엇이 얼마나 빠지는가"를 더한다. 더할 내용이 있으므로 INSUFFICIENT 사유가 아니다. 단, 이 글의 숫자는 실측이 아니므로 "경쟁 글이 틀렸다"는 주장은 위치 인자 deprecated처럼 문서로 확인한 범위에 한정한다.
