제목: ROS 2 새 터미널에서 ros2: command not found — local_setup.bash만 source해서 생기는 일 (실측)

.bashrc에 작업공간 줄만 남겨 두고 새 터미널을 열었더니 ros2: command not found가 난다면, 원인은 대부분 source한 파일이 local_setup.bash라는 데 있습니다.

■ 결론 먼저
- install/setup.bash : 내 작업공간 + 빌드할 때 불려 있던 ROS 2 설치(/opt/ros/jazzy)까지 함께 불러옵니다.
- install/local_setup.bash : 내 작업공간 패키지만 불러옵니다. ROS 2 설치는 안 불러오므로 ros2 명령도, rclpy도 안 보입니다.
- 그래서 .bashrc에는 둘 중 하나만 두면 됩니다.
  1) source ~/ros2_ws/install/setup.bash 한 줄
  2) source /opt/ros/jazzy/setup.bash 다음 줄에 source ~/ros2_ws/install/local_setup.bash

■ 직접 재 본 숫자 (ROS 2 Jazzy 컨테이너, 깨끗한 셸, 5회 반복 모두 동일)
- /opt/ros/jazzy/setup.bash만 : 패키지 194개
- 작업공간 setup.bash만 : 197개 (194 + 내 패키지 3)
- 작업공간 local_setup.bash만 : ros2: command not found, 내 패키지 3개만 보임
- jazzy setup.bash → 작업공간 local_setup.bash : 197개 (setup.bash 한 줄과 같은 결과)

■ 왜 이렇게 되나
colcon이 빌드할 때 setup.bash 안에 "그때 불려 있던 underlay 경로"(/opt/ros/jazzy)를 문자열로 적어 둡니다. 그래서 setup.bash는 나중에 어느 셸에서 source해도 그 경로를 다시 불러옵니다. local_setup.bash에는 그런 줄이 없습니다.
→ underlay(예: 다른 작업공간)를 바꿨다면 작업공간을 다시 빌드해야 setup.bash가 새 경로를 가리킵니다.

colcon 소스 코드 근거, 재현 스크립트, 5회 원본 출력은 원문에 정리했습니다.
원문: https://huntlab.app/ros2-local-setup-vs-setup-bash-fresh-terminal-package-count/

#ROS2 #colcon #setup.bash #local_setup #ros2commandnotfound #우분투 #로봇개발
