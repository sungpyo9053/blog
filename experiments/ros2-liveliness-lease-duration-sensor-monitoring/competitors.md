# 경쟁 글 대비 차별점: ros2-liveliness-lease-duration-sensor-monitoring

검색어 "ROS 2 liveliness lease duration automatic manual_by_topic", "ROS2 QoS liveliness lease duration 설명", "ROS 2 detect sensor topic stopped publishing liveliness deadline watchdog", "ROS2 QoS deadline liveliness 차이 센서 노드 죽음 감지"(2026-10-03)로 찾은 상위 글을 직접 읽었다.

1. https://myzhar.tech/tutorials/ros2/understanding-ros2-qos/ (Walter Lucetti, 2026-09-18)
   - 다루는 것: QoS 정책 전반과 "노드끼리 통신이 안 되는 이유". Liveliness를 AUTOMATIC("노드가 살아 응답하는 한 그 노드의 모든 발행자를 살아 있다고 본다")과 MANUAL_BY_TOPIC("lease 안에 발행이나 API로 직접 알려야 한다")으로 나눠 설명한다.
   - 빠졌거나 틀린 것: AUTOMATIC 설명의 방향은 Fast DDS와 맞지만 근거(RMW 매핑, announcement_period)와 실행 확인이 없다. 구독자 쪽 lease와 발행자 Default의 비호환, liveliness 이벤트 코드, rmw_zenoh 미지원이 없다.
   - 이 글이 더할 것: (실측) 같은 Jazzy 컨테이너에서 AUTOMATIC과 MANUAL_BY_TOPIC으로 카메라 발행만 멈췄을 때의 liveliness changed 이벤트 유무와 감지 지연(5회), 구독자 lease 비호환 시 수신 메시지 수와 incompatible 이벤트.
2. https://www.mathworks.com/help/ros/ug/manage-quality-of-service-policies-in-ros2.html (MathWorks ROS Toolbox, R2026b)
   - 다루는 것: MATLAB에서 Liveliness·LeaseDuration 설정 방법. "발행자 중 하나가 발행하면 노드의 모든 발행자를 LeaseDuration만큼 더 살아 있다고 본다"고 설명한다.
   - 빠졌거나 틀린 것: ROS 문서의 단순화된 문장을 그대로 옮겼다. 독자가 "발행을 멈추면 lease 뒤에 잃는다"고 오해할 수 있다. 발행 정지 시 실제 반응, 멈춘 토픽 감지 방법, 호환성 함정이 없다.
   - 이 글이 더할 것: (실측) 그 문장대로라면 잃어야 하는 상황(단독 발행자 정지)에서 Fast DDS가 실제로 어떻게 반응하는지 측정값과 1차 자료의 차이.
3. https://stevengong.co/notes/Quality-of-Service (Steven Gong, 2026-02-11)
   - 다루는 것: ROS 2 QoS 정책 정의 노트(Liveliness, Lease Duration, Deadline).
   - 빠졌거나 틀린 것: 공식 문서 정의 반복이다. 센서 정지 감지, 호환성 방향, 계산 예가 없다.
   - 이 글이 더할 것: (실측) 주기·lease로 감지 시점을 계산하는 예제와 그 예측을 MANUAL_BY_TOPIC 실측으로 대조.
4. https://velog.io/@hy_k/ROS2-DDS-%EA%B7%B8%EB%A6%AC%EA%B3%A0-QoS (HY K, 2024-09-08, 한국어)
   - 다루는 것: DDS와 QoS 개요. liveliness 옵션으로 AUTOMATIC, MANUAL_BY_NODE, MANUAL_BY_TOPIC을 들고, AUTOMATIC lease 1000 ms rclcpp 설정 코드를 보인다.
   - 빠졌거나 틀린 것: MANUAL_BY_NODE는 rmw에서 deprecated다(types.h L458-L491; rclpy enum에는 없음). lease_duration을 "liveliness를 확인하는 주기"로 설명한다. 실제 의미는 "살아 있음을 알려야 하는 최대 시간"이다(ROS 문서 L66-L68). AUTOMATIC에서 발행 정지 시 무슨 일이 생기는지 다루지 않는다.
   - 이 글이 더할 것: (실측) 올바른 lease 의미와 호환 규칙(요청 ≥ 제공)을 계산과 실측 비호환 사례로 보인다.
5. https://github.com/ros-safety/software_watchdogs (README, 커밋 f2886f1, 2021-04-01, Rolling/Ubuntu 20.04 기준)
   - 다루는 것: liveliness·deadline 기반 워치독 라이브러리. 하트비트가 수동으로 liveliness를 assert하고, 워치독 lease는 하트비트 lease 이상이어야 연결된다는 호환 주의([README L11-L17, L36-L38](https://github.com/ros-safety/software_watchdogs/blob/f2886f10da4d6ecc66fdf3f407a76303fbc16d72/README.md#L36-L38)).
   - 빠졌거나 틀린 것: 별도 하트비트 토픽을 추가하는 방식이라 센서 토픽 자체의 정지를 보지 않는다. 오래된 환경 기준이고 AUTOMATIC으로는 왜 안 되는지 설명하지 않는다. 드라이버 QoS를 바꿀 수 없는 경우는 다루지 않는다.
   - 이 글이 더할 것: (실측) 하트비트 없이 센서 토픽 발행자 자체를 MANUAL_BY_TOPIC으로 둘 때의 감지 동작을 현재 Jazzy에서 측정한다. QoS를 못 바꾸는 드라이버라면 애플리케이션 수준 감시가 필요하다는 판단 기준도 남긴다.

참고: https://github.com/mikeferguson/ros2_cookbook/blob/349605e3ca147055421362be92c65aa7de477635/pages/qos.md 는 qos_overrides와 Infinite 매직 넘버를 다루지만 liveliness 동작은 다루지 않아 직접 경쟁 글로 세지 않았다.
