# 경쟁 글 대비 차별점: ros2-installed-rclpy-not-found-source-setup-shell

1. https://www.cnblogs.com/jzssuanfa/p/19620079 (중국어, 2026-02-16, "已经安装了ROS环境却还是报错 No module named 'rclpy'")
   - 다루는 것: 터미널마다 source 미실행, 자동 로드 미설정, 가상환경·다중 Python 불일치를 원인으로 든다. `echo $PYTHONPATH`, `python3 -c "import rclpy"`, `which python3`, `.bashrc`/`.zshrc` 설정을 안내한다.
   - 빠졌거나 틀린 것: `No module named 'rclpy'`와 `rclpy._rclpy_pybind11`를 구분하지 않는다. 셸 판별에 `echo $SHELL`을 쓰는데, `SHELL`은 사용자의 선호(로그인) 셸을 나타내는 변수라 현재 셸과 다를 수 있다(POSIX XBD 8, bash 매뉴얼 `SHELL`). `/opt/ros/humble/bin/python3`로 실행하라는 대안은 apt ROS 설치에 그런 인터프리터가 없다(Jazzy 이미지의 `/opt/ros/jazzy/bin`에 python3 없음. Humble은 미확인이지만 ROS 패키지가 인터프리터를 배포한다는 공식 근거가 없음). 실제 출력이나 종료 코드가 없다.
   - 이 글이 실측으로 더할 것: 환경을 비운 새 셸마다 source·셸·setup 파일 조합별 import 종료 코드를 보여 주고, `python3 -I`로 `PYTHONPATH`가 원인 경로임을 대조한다(하네스 results.json).
2. https://6fingers.me/ros-on-ubuntu-20-04-no-module-named-rclpy-_rclpy_pybind11 (영어, 2021-10-20, Galactic/Ubuntu 20.04)
   - 다루는 것: 기본 Python(3.9)과 바이너리 빌드 Python(3.8)이 달라 `_rclpy_pybind11` 오류가 난다는 진단을 한다.
   - 빠졌거나 틀린 것: `sudo update-alternatives --config python3`로 시스템 기본 python3를 바꾸라고 권한다. Ubuntu 시스템 도구 전체에 영향을 주는 조치인데 위험을 설명하지 않는다. 공식 Troubleshooting의 권고는 "같은 인터프리터를 쓰라"와 "conda 경로를 PATH에서 빼라"다. 파일 이름 태그(`EXT_SUFFIX`)로 확인하는 방법이 없고, source·셸 갈래도 없다.
   - 이 글이 실측으로 더할 것: 현재 인터프리터의 `EXT_SUFFIX`와 rclpy 폴더의 실제 C 확장 파일 이름이 맞는지, 다른 버전 태그 파일은 없는지 확인한다. 시스템 Python을 바꾸지 않고 판별한다.
3. https://foxglove.dev/blog/installing-ros2-humble-on-ubuntu (영어, 2022-06-30, Humble 설치 가이드)
   - 다루는 것: desktop 설치, 터미널마다 source, `.bashrc`/`.zshrc` 자동화, talker/listener 확인을 다룬다.
   - 빠졌거나 틀린 것: rclpy import 오류, conda·인터프리터 불일치, ros-base 설치 시 listener 예제가 없다는 조건, 셸별 setup 파일이 필요한 원리가 없다. 종료 코드 기준의 판정도 없다.
   - 이 글이 실측으로 더할 것: listener 대신 ros-base에서도 가능한 최소 Python API 검사와 그 한계, source 조합별 종료 코드.
4. https://yiyuanlinxx.github.io/posts/2023/10/py-env-ros-conda/ (영어, 2024-12-18 표기)
   - 다루는 것: conda base(3.11) 활성 상태에서 Humble(3.10) 사용 시 C 확장 오류가 난다는 점과 `conda deactivate`, 자동 활성화 해제를 다룬다.
   - 빠졌거나 틀린 것: 어떤 명령으로 현재 인터프리터·`PYTHONPATH`·확장 태그를 확인하는지 없다. "PYTHONPATH는 모든 인터프리터가 공유하므로 순수 Python 부분은 찾고 C 확장에서 막힌다"는 원리 설명이 없다. source·셸 갈래가 없다.
   - 이 글이 실측으로 더할 것: `-I`(PYTHON* 무시) 대조로 rclpy를 찾는 경로가 `PYTHONPATH`임을 보이고, 인터프리터 갈래를 파일 이름 태그로 확인한다.
5. https://github.com/ros2/rclpy/issues/1194 (영어, 2023-11-01, 사용자 이슈)
   - 다루는 것: Ubuntu 22.04 + Humble + anaconda `(base)` Python 3.11.5에서 같은 `_rclpy_pybind11` 오류가 났다. `/usr/bin/python3.10`으로 실행하니 import 단계는 넘어갔다는 보고와 `python-is-python3` 등 댓글 제안이 있다.
   - 빠졌거나 틀린 것: 유지보수자 답변이 없는 사용자 스레드다. rclpy를 소스로 빌드하려다 헤더 불일치로 실패하는 우회가 섞여 있다(SE 질문자도 같은 시도로 실패). 원리 정리가 없다.
   - 이 글이 실측으로 더할 것: "소스 빌드·재설치 전에 확인할 네 칸"을 정리하고 종료 코드로 판정한다.
