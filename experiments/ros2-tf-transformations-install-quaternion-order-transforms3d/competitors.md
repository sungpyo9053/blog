# 경쟁 글 대비 차별점: ros2-tf-transformations-install-quaternion-order-transforms3d

확인일 2026-10-12. 한국어 검색(`ROS2 tf_transformations 설치`, `ROS2 쿼터니언 오일러 변환 tf_transformations`)에서는 같은 질문을 다루는 한국어 본문 글을 찾지 못했고 결과가 영어 문서·저장소로 채워졌다. 아래는 영어 상위 결과 중 직접 원문을 연 글이다.

1. **Robotics Stack Exchange — "How do you install tf_transformations?"** (https://robotics.stackexchange.com/questions/99908/how-do-you-install-tf-transformations, Stack Exchange API로 본문·답변 확인; runner 직접 접근은 403)
   - 다루는 것: Galactic에서 `rosdep`이 `tf_transformations` 키를 못 찾는 문제. 채택 답변(tfoote, 2021-08-23)은 `ros-galactic-tf-transformations` apt 설치와 `ROS_DISTRO`를 설정해야 rosdep이 배포판을 안다고 안내. 두 번째 답변(2021-08-24)은 당시 README를 인용해 "transforms3d는 Ubuntu debian으로 설치할 수 없으니 `sudo pip3 install transforms3d`".
   - 빠졌거나 틀린 것: 쿼터니언 순서 언급 없음. transforms3d를 직접 쓰는 경로 설명 없음. "debian으로 설치 불가"는 현재 rosdep 키(Ubuntu `'*'` → apt `python3-transforms3d`)와 tf_transformations 1.1.1 apt 패키지 Depends(`python3-transforms3d`)와 다르다. Galactic은 EOL.
   - 이 글이 더할 것: 현재 활성 배포판 기준 설치·의존성, `$ROS_DISTRO` vs README의 `$ROSDISTRO`, 두 경로의 순서 차이와 계산.
2. **GitHub gist salmagro — "ROS2 euler to quaternion transformation."** (https://gist.github.com/salmagro/2e698ad4fbf9dae40244769c5ab74434, 2021-01-11 작성)
   - 다루는 것: tf 없이 쓰는 `euler_from_quaternion`, `quaternion_from_euler` 직접 구현.
   - 빠졌거나 틀린 것: `quaternion_from_euler`가 docstring(`[x, y, z, w]`)과 달리 `[w, x, y, z]`를 반환(`q[0] = cy*cp*cr + sy*sp*sr`는 w). 댓글로 지적됐으나 코드 리비전 1개로 미수정. 테스트 없음.
   - 이 글이 더할 것: 이 반환값을 `Quaternion(x=q[0], …, w=q[3])`에 넣으면 어떤 자세가 되는지 계산과, 그런 실수를 잡는 테스트 입력. (gist 저자를 비난하는 어조 금지. "공개 코드에서도 생기는 실수"의 사례로만 사용)
3. **Automatic Addison — "How To Convert a Quaternion Into Euler Angles in Python"** (https://automaticaddison.com/how-to-convert-a-quaternion-into-euler-angles-in-python/, 2020-11-24)
   - 다루는 것: `(x, y, z, w)` 인자를 받는 `euler_from_quaternion` 직접 구현, ROS 2에서 `tf.transformations`가 없어서 쓸 수 있다는 설명, 예제 1개(z·w=0.7072 → yaw≈π/2).
   - 빠졌거나 틀린 것: 설치 경로(tf_transformations apt, transforms3d) 없음. 다른 라이브러리와 순서가 다를 수 있다는 경고 없음. 예제가 yaw 90° 하나라 순서 실수 검출력 논의 없음.
   - 이 글이 더할 것: 두 공식 경로 비교와 순서 변환 지점, 검출력 있는 테스트 입력 선택 기준.
4. **The Construct — "[ROS Q&A] How to convert quaternions to Euler angles"** (https://www.theconstruct.ai/ros-qa-how-to-convert-quaternions-to-euler-angles/, 2017-10-18)
   - 다루는 것: ROS 1 `rospy` + `tf.transformations.euler_from_quaternion`, 메시지 필드를 `[x, y, z, w]` 리스트로 만드는 코드.
   - 빠졌거나 틀린 것: ROS 1 기준이라 ROS 2 설치 질문에 답하지 않음. 순서 차이 언급 없음.
   - 이 글이 더할 것: 이 ROS 1 코드를 ROS 2로 옮길 때 import 한 줄만 바꾸면 되는 경우(tf_transformations)와 순서까지 바꿔야 하는 경우(transforms3d)를 구분.
5. (공식 1차 자료이자 상위 결과) **tf_transformations README / index.ros.org** — 순서 차이를 한 문장으로 명시하지만 그 결과가 얼마나 큰지, 테스트로 어떻게 잡는지는 다루지 않는다. 설치 명령 변수명이 `$ROSDISTRO`. 이 글은 README를 재요약하지 말고 위 계산·반례·테스트 기준을 더한다.

판정: 경쟁 글 대비 더할 것이 있다(계산된 오차 범위, 정규화·성분 비교의 반례, 실제 공개 코드 사례, 현재 배포판 기준 설치 정정). INSUFFICIENT 아님.
