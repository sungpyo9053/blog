# 경쟁 글 대비 차별점: colcon-build-resource-setup-bash-new-package-open-terminal

한국어 검색어 3개("colcon build 후 source install/setup.bash 다시 해야 하는 이유 새 터미널", "ROS2 colcon build 이후 source install/setup.bash 매번 해야 하나요 패키지 추가", "ros2 run package not found colcon build 했는데 패키지 못 찾음 source 티스토리")로 찾았다. 상위 결과는 모두 영어 문서나 공식 문서 미러였고, 이 질문을 직접 다루는 한국어 글은 확인하지 못했다. 아래는 원문을 직접 연 영어 글이다(2026-11-23 확인).

1. https://ros2-tutorial.readthedocs.io/en/latest/packages/source_after_build.html (Murilo's ROS2 Tutorial, "Always source after you build")
   - 다루는 것: 새로 만들거나 수정한 패키지는 다시 빌드하고 다시 source하지 않으면 시스템에 보이지 않는다고 말한다. 처음 빌드한 터미널에서 `ros2 run`을 하면 `Package 'python_package_with_a_node' not found`가 나온다는 예를 들고, "항상 빌드 후 source하라, 그래야 sourcing 오류를 배제할 수 있다"를 권한다. 다른 터미널에서도 source하라는 노트도 있다.
   - 빠졌거나 틀린 것: "새 패키지"와 "기존 패키지 수정"을 한데 묶는다. 공식 Creating-A-Workspace 7단계는 수정 후 재빌드가 이미 source한 터미널에 다시 source 없이 반영되는 흐름을 보여 주므로, 수정까지 다시 source가 필요하다는 인상은 정확하지 않다. 이미 열린 터미널이 왜 못 보는지(source 시점 고정)와 `--merge-install`에서의 차이는 설명이 없다.
   - 이 글이 더할 것: 새 prefix가 생기는 빌드와 생기지 않는 빌드를 나누고, 기본·merged 두 레이아웃에서 같은 터미널의 세 시점 패키지 수와 경로 항목 수를 실측해 어느 경우에 다시 source가 필요한지 판정한다.
2. https://automaticaddison.com/how-to-create-a-ros-2-package-jazzy/ (Automatic Addison, ROS 2 Jazzy, 2024-11-04 작성·2025-03-29 갱신)
   - 다루는 것: Jazzy에서 패키지를 만들고 `colcon build` 뒤 "새 터미널을 열거나 `source ~/.bashrc`"를 한 다음 `ros2 pkg list`로 확인하라는 절차.
   - 빠졌거나 틀린 것: 왜 새 터미널이나 다시 source가 필요한지, 언제 필요 없는지 설명하지 않는다. 레이아웃 차이도 없다.
   - 이 글이 더할 것: `ros2 pkg list`가 현재 셸의 `AMENT_PREFIX_PATH`를 매번 읽는다는 소스 근거와, 그 문자열이 source 시점에 고정된다는 원리를 측정값과 함께 보여 준다.
3. https://rossimplified.substack.com/p/ros-2-tutorial-for-beginners-part (ROS Simplified, 2026-02-02, Humble·Jazzy)
   - 다루는 것: `colcon build` 뒤 실행 파일이 install 폴더에 설치되므로 `source ~/<ws>/install/setup.bash`로 "ROS 2 환경을 갱신해야 노드를 찾는다"고 설명한다.
   - 빠졌거나 틀린 것: 어떤 환경변수가 어떻게 바뀌는지, 새 패키지와 수정한 패키지의 차이, merged 설치를 다루지 않는다.
   - 이 글이 더할 것: 바뀌는 변수(`AMENT_PREFIX_PATH`)의 항목 수를 레이아웃별로 예측하고 실측하며, 다시 source해도 중복이 쌓이지 않는다는 코드 근거를 준다.
4. https://techoverflow.net/2025/01/24/how-to-fix-ros2-package-not-found-package-not-found-searching/ (TechOverflow, 2025-01-24)
   - 다루는 것: `Package not found`의 원인을 `AMENT_PREFIX_PATH`의 prefix 아래 `share/ament_index/resource_index/packages/<name>` 색인 구조로 설명하고, colcon으로 빌드한 뒤 `install/local_setup.sh`를 source하라고 한다.
   - 빠졌거나 틀린 것: 이미 source한 터미널에서 빌드 후 새 패키지가 보이는지, merged 레이아웃에서 같은 prefix에 색인 파일이 추가되는 경우는 다루지 않는다.
   - 이 글이 더할 것: 같은 색인 원리를 "source 이후 생긴 prefix"와 "기존 prefix 안에 생긴 색인 파일"로 나눠, 다시 source 없이 보이는 경우와 안 보이는 경우를 실측으로 가른다.
5. 원 질문 Robotics Stack Exchange 113595 "ROS2 recommended handling of workspace setup.bash" (2024-11-04, 조회 1470, 답변 2. 원문은 Stack Exchange API `https://api.stackexchange.com/2.3/questions/113595?site=robotics&filter=withbody`로 확인. 질문 페이지 자체는 runner에서 403이라 본문 인용 링크로 쓰지 않는다)
   - 다루는 것: 채택 답변(점수 4)은 같은 터미널에서 source와 빌드를 함께 하면 다른 작업공간의 패키지가 덮어써지는 등 의도치 않은 결과가 생길 수 있다고 한다. 다른 답변(점수 1)은 setup.bash가 생성 당시 source돼 있던 prefix를 체인으로 포함한다고 설명하고, 대안으로 `local_setup.bash`를 제시한다.
   - 빠졌거나 틀린 것: 질문자가 "빌드 후 다시 source"하는 습관 중 실제로 언제 다시 source가 필요한지는 어느 답변도 다루지 않는다.
   - 이 글이 더할 것: 그 빈칸, 즉 빌드 후 다시 source가 필요한 시점을 레이아웃별 실측으로 채운다. 빌드 터미널 분리 권고는 공식 문서 문장으로만 짧게 연결한다.
