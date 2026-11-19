# 경쟁 글 대비 차별점: ros2-multiple-distros-one-machine-mixed-node-pairs

1. https://robotics.stackexchange.com/questions/24180/multiple-ros-installation-on-single-machine (Stack Exchange API로 본문과 답변 확인. 실행 서버에서 웹 페이지는 403)
   - 그 글이 다루는 것: 채택 답변은 "/opt/ros/{distro}에 설치되므로 side-by-side로 no conflict, 한 번에 한 배포판만, .bashrc에 넣지 말고 수동 source"를 권한다.
   - 빠졌거나 틀린 것: "no conflict"는 코드네임 제약을 빠뜨린 과장이다(예: Noble에 Humble deb 없음, Noble의 Lyrical은 Tier 3). 배포판 간·RMW 간 통신 보장, EOL은 다루지 않는다.
   - 이 글이 실측으로 더할 것: 독자 컴퓨터에서 후보 유무(`apt-cache show` 종료 상태)와 제거 여부(`apt-get install -s`의 `Remv` 줄)를 판정하는 검증된 명령. 하네스가 Jazzy에서 잰 source 상태별 환경 변수 값.
2. https://robotics.stackexchange.com/questions/61098/can-i-install-multiple-ros-version-on-the-same-machine (구 answers.ros.org 187548, 2014, ROS 1. API로 답변 확인)
   - 그 글이 다루는 것: "apt로 쉽게 된다"는 채택 답변이 나중에 "Indigo는 12.04 미지원"으로 정정됐다. .bashrc에 넣지 말라는 조언, 메시지가 바뀌지 않았다면 어느 정도 상호 운용된다는 언급도 있다.
   - 빠졌거나 틀린 것: ROS 1 시대 글이라 ROS 2의 RMW·DDS 계층과 현재 배포판 표가 없다. "메시지가 같으면 된다"는 기대는 ROS 2 Humble↔Iron 이후에는 맞지 않을 수 있다(Discourse 메인테이너 설명).
   - 이 글이 실측으로 더할 것: 2026-11 기준 코드네임별 배포판 표. 하네스가 잰 "설치 안 된 RMW를 가리킨 셸"의 실제 실패 출력.
3. https://discourse.openrobotics.org/t/incompatability-between-distributions/43747 (2025-05, Humble↔Jazzy)
   - 그 글이 다루는 것: 섞인 배포판 통신이 실패한 사례, 원인(직렬화·GID·Fast DDS 버전), "NOT MIX NODES BETWEEN ROS DISTROS" 권고.
   - 빠졌거나 틀린 것: 설치 공존, .bashrc, 코드네임 제약은 다루지 않는다. 섞인 노드가 그래프의 몇 쌍에 영향을 주는지 수량화하지 않는다.
   - 이 글이 실측으로 더할 것: (배포판, RMW) 묶음별 보장 밖 쌍 계산과 검산. 하네스로 잰 같은 묶음 기준선 수신 개수(보장 범위 안의 기준값으로만 사용).
4. https://cobots2024.jeju.ai/week09/configure.html (한국어, 2024 협동로봇 강의 자료)
   - 그 글이 다루는 것: 공식 튜토리얼 번역. "여러 ROS 2 배포판(예: Dashing과 Eloquent)을 설치하고 전환할 수 있다", .bashrc에 source 추가, ROS_DOMAIN_ID.
   - 빠졌거나 틀린 것: 여러 배포판을 쓸 때 .bashrc에 한 배포판을 고정하면 생기는 문제, 코드네임 제약, 통신 비보장, EOL이 없다. 예시 배포판(Dashing·Eloquent)은 이미 지원이 끝났다.
   - 이 글이 실측으로 더할 것: 현재 배포판 기준의 확인 절차. 셸 상태별 ROS_DISTRO 등 하네스 측정값.
