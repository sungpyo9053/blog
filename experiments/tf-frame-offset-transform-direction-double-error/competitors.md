# 경쟁 글 대비 차별점: tf-frame-offset-transform-direction-double-error

같은 질문("tf frame offset base_link", "frame_id child_frame_id 반대", "tf 변환 방향")으로 찾은 상위 문서를 직접 읽었다(2026-10-04).

1. [nu-msr — Transforms in ROS (Matthew Elwin)](https://nu-msr.github.io/ros_notes/ros2/tf.html) (runner 접근 OK)
   - 다루는 것: 브로드캐스터 설명에서 "the transform converts frame_id into child_frame_id", 동등하게 "coordinates in child_frame_id into coordinates in frame_id"라고 변환 의미를 정의한다.
   - 빠진 것: 부모·자식을 바꾸거나 역을 발행했을 때 생기는 오차, 그 오차로 원인을 판정하는 방법, 회전이 섞일 때의 차이가 없다.
   - 이 글이 더할 것: 같은 정의에서 "거꾸로 발행 = 2배 벌어짐(순수 이동)"을 산술 검산 10케이스로 보이고, 비율로 다음 행동을 고르게 한다.
2. [Foxglove — Publishing and Visualizing ROS 2 Transforms (José L. Millán, 2023-01-18)](https://foxglove.dev/blog/publishing-and-visualizing-ros2-transforms) (runner 접근 OK)
   - 다루는 것: `static_transform_publisher` 문법(parent child 순서), 동적 브로드캐스터, Foxglove 3D 패널 시각화
   - 빠진 것: 방향 실수 진단, 역변환, 오차 정량화가 없다.
   - 이 글이 더할 것: 화면에서 보이는 어긋남을 "몇 배인가"로 읽는 판정 기준, 1배 반례, 회전 반례
3. [Automatic Addison — Coordinate Frames and Transforms for ROS-based Mobile Robots (2021-06-16)](https://automaticaddison.com/coordinate-frames-and-transforms-for-ros-based-mobile-robots/) (runner 접근 OK)
   - 다루는 것: map/odom/base_footprint/base_link/laser_link 역할, base_link→laser 정적 변환 launch 예
   - 빠진 것: 방향을 바꿔 적었을 때의 결과, 역변환, 수치 진단이 없다.
   - 이 글이 더할 것: 같은 base_link→laser 상황을 0.2 m→0.4 m(비율 2)로 계산하고, 부모·자식 교환과 부호 실수를 트리 모양으로 구분하는 기준
4. [Articulated Robotics — The Transform System (tf2) (Josh Newans)](https://articulatedrobotics.xyz/ready-for-ros-6-tf/) (WebFetch로 읽음. runner의 `source_digest`에서는 HTTP 오류이므로 **본문 링크 금지**, 연구 참고만)
   - 다루는 것: "each frame is defined by one (and only one) transform from another frame", RViz는 화살표를 자식→부모로 그린다는 점, view_frames·topic echo 사용
   - 빠진 것: 교환 시 결과, frame/data formulation, 오차 계산이 없다.
   - 이 글이 더할 것: 위와 같다.
5. [Booil Jung — tf2 관련 오류 사례 및 해결책(한국어)](https://booiljung.gitbook.io/booil-jung/docs/robot/ros2_humble/chapter_09/0908) / [tf2 구조와 동작 원리](https://booiljung.gitbook.io/booil-jung/docs/robot/ros2_humble/chapter_09/0901) (runner `source_digest`에서 source_too_large/시간 초과 → **본문 링크 금지**)
   - 다루는 것: "frame_id와 child_frame_id 혼동"을 오류 사례로 들고, 원인(부모→자식 순서 혼동)과 해결(코드 점검)을 나열한다.
   - 빠진 것·틀린 것: 혼동 시 얼마나 어긋나는지, 무엇으로 판정하는지가 없다. 0901 페이지는 p_{A→B}를 "B 원점을 A 기준으로 표현한 위치"로 정의하면서 합성을 T_{A→C} = T_{B→C}·T_{A→B}로 적었다. 그 정의를 따르면 점을 C→B→A로 옮기는 행렬 합성은 T_{A→B}·T_{B→C} 순서가 되어야 하므로, 표기와 곱셈 순서가 서로 맞지 않는다(Research의 검토 의견이다. 원 저자 확인 없음).
   - 이 글이 더할 것: 한국어로 frame/data formulation 역관계를 1차원 숫자로 계산하고, "2배/1배/회전" 판정 기준을 제공한다.
6. 참고로 읽은 [TF101 (Bandi Jai Krishna, 2021, 갱신 2022)](https://textzip.github.io/posts/ROS-TF101/)은 base_laser가 base_link 기준 x 10 cm, y 20 cm라는 정의 예와 ROS 1 `static_transform_publisher` 문법을 다룬다. 교환 오류는 다루지 않는다.

- 판정: 상위 문서들은 문법과 정의까지만 다룬다. "거꾸로 발행했을 때의 정량 오차와 그 숫자로 원인을 가르는 법"은 확인한 범위에서 어느 문서도 다루지 않는다. 이 글이 더하는 것은 로봇 실측이 아니라 **커밋된 산술 검산(verification.json)**이다. Writer는 이를 "실측"이라고 부르지 않는다. 더할 것이 있으므로 INSUFFICIENT 사유가 아니다.
