# 경쟁 글 대비 차별점: colcon-build-slow-overlay-colcon-ignore-symlink-install-order

같은 질문으로 검색되는 글을 직접 읽었다(2026-10-04 확인, 한국어 2·영어 2).

1. https://robotics.stackexchange.com/questions/105783/how-to-speed-up-colcon-build-notably-slower-than-catkin-cmake-and-or-debug-cau (원 질문, 영어. runner에서 HTML 403 → 공개 Stack Exchange API `https://api.stackexchange.com/2.3/questions/105783?site=robotics&filter=withbody`로 본문·답변·댓글을 읽음)
   - 다루는 것: Humble·Jetson arm64·Docker에서 `--merge-install` 빌드가 느리고, 변경 없는 빌드도 오래 걸린다는 질문. 프로파일링 방법을 묻는다.
   - 빠진 것: 채택 답변이 없다. 유일한 답변(2026-09-08, 점수 -1)은 ccache·병렬·변경 패키지만 빌드·Docker 최적화를 한 문단으로 나열할 뿐 명령·근거·측정이 없다. "무변경 빌드도 패키지마다 재구성 판단·빌드·설치를 거친다"는 원리 설명이 없다.
   - 이 글이 실측으로 더할 것: Jazzy 이미지에서 무변경 재빌드의 패키지당 비용과 `--packages-select`로 줄어드는 정도를 하네스로 측정해, "패키지 수가 손잡이"라는 원리를 숫자로 확인한다.
2. https://velog.io/@openjr/colcon-%EC%82%AC%EC%9A%A9%EB%B2%95-%EC%95%8C%EC%95%84%EB%B3%B4%EC%9E%90 (한국어, OpenJR, 2025-01-24)
   - 다루는 것: `--symlink-install`, `--packages-select`, `--packages-up-to` 사용법. symlink로 launch·config 수정 시 재빌드가 필요 없다는 설명.
   - 빠진 것: COLCON_IGNORE·overlay·BUILD_TESTING·실행기 설명 없음. symlink의 한계(C++ 수정, 새 파일, setup.py 변경)와 플래그 전환 시 재구성 문제 없음. 측정 없음.
   - 이 글이 실측으로 더할 것: symlink 있음/없음에서 Python 수정 반영 여부를 같은 조건으로 확인하고, 플래그 전환 시 재구성 비용을 측정한다.
3. https://fer.gs/ros2_cookbook/other/pages/colcon.html (영어, ROS 2 Cookbook, mikeferguson/ros2_cookbook 기반, 날짜 표기 없음)
   - 다루는 것: Python 스크립트·config·launch 수정 때 재빌드를 피하려면 `--symlink-install`, `--packages-select`, `--cmake-clean-cache`, 이벤트 핸들러 명령 한 줄씩.
   - 빠진 것: 각 옵션이 줄이는 몫, overlay·COLCON_IGNORE·BUILD_TESTING, 적용 안 되는 조건, 측정 없음.
   - 이 글이 실측으로 더할 것: 옵션별 "덜어내는 몫" 산술 모델과 하네스 실측의 대조.
4. https://zeta-edu-ros2.readthedocs.io/en/latest/courses/3.tutorial_client_libraries/1.colcon.html (한국어, ZetaBank 교육 문서, Humble 공식 튜토리얼 번역)
   - 다루는 것: underlay/overlay, `--symlink-install`, COLCON_IGNORE, `-DBUILD_TESTING=0`을 공식 튜토리얼 그대로 번역.
   - 빠진 것: 네 수단이 서로 다른 몫을 줄인다는 연결, 어떤 패키지에 무엇을 쓸지 판단 기준, 진단 방법, 측정 없음. 순차 실행기 팁도 없다.
   - 이 글이 실측으로 더할 것: 독자 패키지 분류(자주 고침/거의 안 고침 × python/cmake) → 수단 선택 → 산술 어림 → 실측 비교의 흐름.

공식 튜토리얼 자체(참고한 소스 1·2)도 기준선으로 대조했다: 네 수단을 다른 위치에서 각각 한 문장으로 소개하며 서로의 관계·적용 범위·측정은 다루지 않는다. 이 글은 그 문장을 번역하지 않고, 위 원리·산술·소스 근거·실측 대조를 더한다. 따라서 차별점이 있으며 INSUFFICIENT 사유가 아니다.
