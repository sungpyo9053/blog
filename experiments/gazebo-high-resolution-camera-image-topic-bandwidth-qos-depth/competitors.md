# 경쟁 글 대비 차별점: gazebo-high-resolution-camera-image-topic-bandwidth-qos-depth

검색어: "Gazebo high resolution camera sensor slow simulation real time factor drops", "ROS 2 image topic bandwidth calculation width height fps ros2 topic bw camera", "Gazebo Harmonic camera sensor performance RTF drops when subscribing image topic ros_gz_bridge", "가제보 카메라 센서 시뮬레이션 느려짐 해상도 ROS2 이미지 토픽", "ROS2 카메라 이미지 토픽 용량 계산 MB/s rgb8 1920x1080", "가제보 시뮬레이션 느림 카메라 해결 velog OR tistory ROS2" (2026-10-29). 아래 글은 원문을 직접 열어 읽었다.

1. https://clearpathrobotics.com/blog/2025/04/optimizing-video-streaming-in-ros-2/ (Clearpath Robotics, Darby Mills, 2025-04-15)
   - 다루는 것: 원시 이미지가 무선망을 압도하는 문제. 1280×720×3×30이면 "660 Mbps 이상"이라는 계산(검산 663.552 Mb/s 일치). image_transport·FFmpeg(H.264) 압축과 파라미터 조정.
   - 빠진 것: 실제 로봇 Wi-Fi 전송만 다룬다. QoS depth로 쌓이는 바이트, Gazebo 렌더링, 구독이 렌더링을 켜는 문제, `ros2 topic bw`의 측정 의미가 없다.
   - 이 글이 더할 것: 시뮬레이터 안에서 "렌더링 게이트 vs 메시지량"을 나누는 순서. depth 상한 계산. 하네스 실측으로 합성 토픽의 수신 MB/s·Hz가 계산과 맞는지 보여 주기.
2. https://github.com/MOGI-ROS/Week-5-6-Gazebo-sensors (MOGI-ROS 강의 저장소, Gazebo Harmonic)
   - 다루는 것: 640×480·20 Hz 카메라. "압축 없이 거의 20 MB/s"(검산 18.432 MB/s 일치). parameter_bridge 대신 ros_gz_image image_bridge와 JPEG 압축 권장. image/camera_info 토픽 접두사 맞추기.
   - 빠진 것: 계산식 일반화, depth 상한, RTF 측정, 구독-렌더링 관계, lazy 브리지, bw 측정 의미가 없다.
   - 이 글이 더할 것: 독자 설정을 넣는 식, Gazebo 소스 기반의 "구독하면 렌더링 시작" 설명, 실측 대조.
3. https://github.com/gazebosim/gz-sensors/issues/332 (Gazebo 공식 이슈, 2023-03 개설, 2025-02 질문자 댓글)
   - 다루는 것: FHD 카메라가 목표 30 Hz를 못 내는 문제. 메인테이너의 "구독자 없으면 카메라 갱신 안 함", "ros2 topic hz는 벽시계", 렌더링 스레드·GPU readback 병목 설명. 사용자 프로파일과 PR #1938 개선.
   - 빠진 것: 이슈 스레드라 체계적 설명이 아니다. 데이터량 계산·QoS depth·CameraInfo가 없고, 2025년 4512×4512 질문에는 답이 없다.
   - 이 글이 더할 것: 흩어진 메인테이너 발언을 현재 Harmonic 계열 소스(줄 단위)로 확인한다. 질문자 설정에 숫자를 대입하고, 판단 순서와 실측 대조로 정리한다.
4. https://classic.gazebosim.org/tutorials?tut=lockstep_physics_sensors (Gazebo Classic 공식 튜토리얼)
   - 다루는 것: 고해상도·고주기 카메라(1280×720, 500 fps 예시)가 물리를 못 따라갈 때 lockstep으로 센서 주기를 강제하면 RTF가 1 미만이 되는 트레이드오프.
   - 빠진 것: Gazebo Classic(지원 종료) 전용이다. 신형 Gazebo(Harmonic)의 렌더링 게이트·ros_gz 경로, 데이터량 계산, QoS가 없다.
   - 이 글이 더할 것: Harmonic 계열 소스 기준 설명과 메시지 쪽 계산·실측.
5. https://www.cerulion.com/blog/ros2-qos-field-guide (Cerulion, Raveen Kariyawasam, 2026-06-12)
   - 다루는 것: QoS 정책 일반론, sensor data 프로필(best effort, keep last 5), depth 트레이드오프, "history가 과부하를 없앤다고 가정하지 말고 측정하라".
   - 빠진 것: 이미지 바이트 기준의 depth 상한 계산, 해상도·fps 계산, Gazebo 맥락이 없다.
   - 이 글이 더할 것: depth × 프레임 바이트 상한을 구체 숫자(FHD 62.2 MB, 4512² 610.7 MB)로 계산하고 실측과 연결.
6. (한국어) https://velog.io/@cjh1995-ros/ROS2-Gazebo (최준혁, 2022-01-26)
   - 다루는 것: Gazebo(Classic 플러그인) 카메라 설정 예시. RGB 1920×1080·30 Hz, depth 640×480·30 Hz.
   - 빠진 것: 성능·데이터량·QoS·RTF를 다루지 않는다. 한국어 검색에서 이 질문을 직접 다룬 글은 찾지 못했다.
   - 이 글이 더할 것: 같은 1920×1080·30 Hz 설정이 186.6 MB/s라는 계산과 성능 판단 순서를 한국어로 제공.
   - 주의: 이 URL은 현재 runner에서 접근 실패(HTTP 오류)다. 경쟁 비교 기록으로만 남기고 본문 인용·링크에는 쓰지 않는다.

판정: 경쟁 자료는 공식·준공식 소스 기반 설명, 질문자 설정 대입, 측정 도구 의미 해석, 하네스 실측 대조를 갖추지 못했다. 이 글이 더할 것이 있으므로 READY.
