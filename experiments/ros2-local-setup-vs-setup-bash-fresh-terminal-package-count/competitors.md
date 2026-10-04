# 경쟁 글 대비 차별점: ros2-local-setup-vs-setup-bash-fresh-terminal-package-count

같은 질문("local_setup.bash와 setup.bash 차이", "ROS2 setup.bash local_setup.bash 차이 새 터미널")으로 검색되는 상위 글을 2026-10-04 직접 열어 읽었다. 한국어 2개, 영어 3개. (Robotics Content Lab 영문 글은 인증서 만료로 열지 못해 제외, CSDN 중문 글은 언어 조건 밖이라 제외.)

1. https://robotics.stackexchange.com/questions/87173/what-is-the-difference-between-local-setup-bash-and-setup-bash (영어, 원 질문. 2018-05-29 ROS Answers 이관, 조회 2,467. 이 runner에서 직접 접속은 HTTP 403이라 공개 Stack Exchange API https://api.stackexchange.com/2.3/questions/87173?site=robotics&filter=withbody 와 /answers 로 본문을 읽음)
   - 다루는 것: 질문자는 새 터미널에서 overlay `local_setup.bash`만 source하고 `ament build`를 하자 `ament: command not found`가 났고 `setup.bash`로는 성공했다고 보고. 채택 답(Dirk Thomas)은 local_setup은 그 prefix만, setup은 "빌드 당시 환경에 source돼 있던 작업공간"의 local_setup을 먼저 부른다고 정확히 설명. 다른 답(mjcarroll)은 ament 문서를 인용.
   - 빠졌거나 틀린 것: ROS 2 Ardent·ament 빌드 도구 시대(2018) 답이다. mjcarroll이 인용한 "ament index의 parent prefix path를 읽는다"는 설명은 현재 colcon 구현(빌드 시점 `COLCON_PREFIX_PATH`/`AMENT_PREFIX_PATH`에서 경로를 골라 `setup.bash`에 문자열로 기록)과 다르다. 현재 배포판에서의 확인 절차·측정값이 없다.
   - 이 글이 더할 것: Jazzy 기준 공식 문서·고정 커밋 코드로 원리를 갱신하고, 새 터미널 세 개에서 `ros2` 존재 여부와 패키지 개수를 하네스로 5회 실측해 질문자의 `command not found` 관측을 현재 도구로 재현·판정한다.
2. https://velog.io/@hwang-chaewon/ROS-2026 (한국어, maroo, 2022-08-30, Foxy)
   - 다루는 것: underlay(`/opt/ros/foxy`)와 overlay(`ros2_ws`) 구분, local_setup은 같은 폴더 패키지만, setup은 빌드에 필요한 작업공간의 local_setup을 포함한다는 정의. 일반적으로 underlay setup 뒤 overlay local_setup을 source한다는 사용법.
   - 빠졌거나 틀린 것: 정의는 맞지만 실행 출력·검증이 없다. 새 터미널에서 local_setup만 쓰면 무엇이 깨지는지(`ros2` 없음), 왜 그런지(빌드 시점 chain), 이름이 겹칠 때 개수 해석이 없다. Foxy 기준(EOL 배포판).
   - 이 글이 더할 것: Jazzy 실측 개수와 종료 코드, 기준선 (U+2M)/2로 내리는 판정, chain이 빌드 시점에 고정된다는 코드 근거.
3. https://goodgodgd.github.io/ian-lecture/archivers/ro-ros-setup (한국어, Hyukdoo Choi, 2022-01-11, Foxy)
   - 다루는 것: `/opt/ros/foxy/setup.bash`는 ROS 명령을 쓰게 하고, 작업공간의 `install/local_setup`을 실행해야 작업공간 패키지를 쓸 수 있다고 설명. `.bashrc`에 두 줄을 순서대로 넣는 설정과 talker/listener 실행 출력.
   - 빠졌거나 틀린 것: overlay의 `setup.bash`가 underlay까지 부른다는 사실과 두 스크립트의 차이 자체를 설명하지 않는다. 두 줄 순서가 왜 필요한지, 한 줄(`setup.bash`)로 대체 가능한지 판단 근거가 없다.
   - 이 글이 더할 것: "underlay 줄 + local_setup" 두 줄과 "overlay setup.bash" 한 줄이 같은 결과를 내는지 실측(T2 vs T4)과 공식 note로 확인하고, 독자가 자기 `.bashrc`를 고르는 기준을 준다.
4. https://industrial-training-master.readthedocs.io/en/latest/_source/session7/ROS2-Basics.html (영어, ROS-Industrial Training, Eloquent)
   - 다루는 것: "setup.bash will configure a terminal environment to see the workspace packages as well as the environment the workspace was built in", "local_setup.bash will add the workspace packages to the current environment", `.bashrc`에 underlay가 있으면 local_setup만 source하면 된다는 조건부 안내.
   - 빠졌거나 틀린 것: 문장은 정확하지만 "environment the workspace was built in"이 실제로 무엇을 뜻하는지(빌드 시점 경로를 문자열로 고정 → underlay 교체 시 재빌드 필요)를 설명하지 않는다. 출력·검증 없음, Eloquent(EOL).
   - 이 글이 더할 것: "built in"의 의미를 colcon-bash 템플릿 코드로 풀고, 생성된 `setup.bash`의 chained prefix 줄을 실측 출력으로 보여 준다.
5. https://www.theconstruct.ai/ros2-in-5-mins-007-how-to-create-a-ros2-overlay-workspace/ (영어, Alberto Ezquerro, 2019-12-07, Crystal)
   - 다루는 것: 빈 overlay 작업공간 생성과 `colcon build` 출력, `source install/local_setup.bash && source install/setup.bash` 두 줄 실행.
   - 빠졌거나 틀린 것: 두 스크립트의 차이를 설명하지 않고 둘 다 source한다. colcon-bash 템플릿상 `setup.bash`가 마지막에 같은 prefix의 `local_setup.bash`를 다시 source하므로 같은 overlay에 대해 앞의 `local_setup.bash` 줄은 불필요하다(코드 근거). 제목과 달리 underlay/overlay 개념 설명이 없다.
   - 이 글이 더할 것: 같은 overlay에 두 줄을 쓸 필요가 없다는 코드 근거와, 한 줄만으로 U+M개가 보이는지의 실측.

공통 공백: 다섯 글 모두 "새 터미널에서 실제로 무엇이 보이는가"를 숫자로 확인하지 않고, `setup.bash`의 상위 경로가 빌드 시점에 결정된다는 점과 `ros2 pkg list`의 계수 규칙을 다루지 않는다. → 판정: 이 글이 실측으로 더할 것이 있으므로 READY.
