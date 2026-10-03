# 경쟁 글 대비 차별점: ros2-liveliness-lease-duration-vs-deadline-topic-stall

검색어 "ROS 2 liveliness lease duration deadline QoS detect sensor topic stopped publishing", "ROS2 QoS liveliness lease duration 설명 deadline", "ROS2 QoS liveliness 라이브니스 lease duration velog OR tistory"로 찾은 상위 글을 이 runner에서 원문으로 열어 읽었습니다(2026-10-04).

1. https://myzhar.tech/tutorials/ros2/understanding-ros2-qos/ (Walter Lucetti, 2026-09-18, 영어)
   - 다루는 것: QoS 정책 전체, 호환성 규칙, qos_overrides를 통한 튜닝. deadline이 "조용해진 센서를 감지하는 데 매우 유용"하다고 적고, Automatic은 "노드 자체가 살아 응답하는 한" publisher를 살아 있다고 봅니다.
   - 빠졌거나 틀린 것: 사용자 문서의 "발행 기반" 정의와 자신의 "노드 생존 기반" 설명이 다르다는 점을 언급하지 않습니다. 발행자 Default deadline/lease일 때 감시용 구독자가 deadline·lease를 요청하면 연결이 끊긴다는 점, 다중 publisher 노드에서 한 토픽만 멈춘 사례, 이벤트 콜백 코드가 없습니다.
   - 이 글이 더할 것: 같은 노드의 진단 토픽이 계속 나가는 동안 카메라 토픽만 멈출 때 Automatic·MANUAL_BY_TOPIC·deadline 이벤트가 각각 언제 오는지를 Jazzy·Fast DDS에서 실측해 나란히 보여 줍니다. 발행자 Default deadline에 감시 노드만 deadline을 요청할 때 연결이 끊기는 것도 실측합니다.
2. https://velog.io/@gaebalsebal/ROS2-QoSQuality-of-Service-Profile%EC%9D%B4%EB%9E%80 (2024-06-13, 한국어)
   - 다루는 것: 정책별 한 줄 정의와 기본 프로필(Sensor Data, Default 등).
   - 빠졌거나 틀린 것: "Automatic: publisher가 lease duration 기간동안 메세지를 전송하지 않으면 비활성 상태로 간주한다"고 publisher 단위·발행 기반으로 적습니다. 공식 사용자 문서(노드의 어느 publisher든 발행하면 모든 publisher 갱신)와도, DDS/Fast DDS 정의(미들웨어가 프로세스 단위로 갱신)와도 다릅니다. 이 설명대로라면 카메라만 멈춰도 liveliness 이벤트가 와야 하지만 두 공식 정의 어디에서도 그렇게 되지 않습니다. 이벤트 이름·호환성 표·코드가 없습니다.
   - 이 글이 더할 것: 그 서술이 맞는지(카메라만 멈출 때, 모든 발행을 멈추고 프로세스는 살아 있을 때 Automatic에서 Liveliness changed가 오는지)를 실측으로 판정합니다. 공식 문서 세 종류의 정의를 원문 줄 링크로 대조합니다.
3. https://velog.io/@happy_lee0_0/ROS2-Qos-tf10 (2025-01-01, 한국어)
   - 다루는 것: 정책 목록과 `QoSProfile(liveliness=AUTOMATIC, liveliness_lease_duration=1.0, deadline=1.5 ...)` 퍼블리셔 코드.
   - 빠졌거나 틀린 것: Liveliness를 "정해진 주기 내 노드 또는 토픽의 생사를 확인"으로만 적어 Automatic이 어느 단위를 보는지 구분하지 않습니다. 구독자 쪽 이벤트 콜백, 호환성 조건이 없고, 예제는 퍼블리셔 설정만 있어 무엇이 감지되는지 관측하지 않습니다.
   - 이 글이 더할 것: 구독자 쪽 `SubscriptionEventCallbacks`로 deadline·liveliness 이벤트를 실제로 받아 alive_count/not_alive_count와 첫 이벤트까지의 경과 시간을 실측합니다. 그래서 "노드 생사"와 "토픽 정지"가 어떤 이벤트로 갈리는지 보여 줍니다.
4. https://www.mathworks.com/help/ros/ug/manage-quality-of-service-policies-in-ros2.html (MathWorks ROS Toolbox 문서, 영어)
   - 다루는 것: ROS 2 사용자 문서와 같은 정의("any of the publishers has published a message → all publishers of the node alive for an additional LeaseDuration"), 호환성, Liveliness Changed 이벤트.
   - 빠졌거나 틀린 것: 미들웨어의 자동 갱신(DDS AUTOMATIC) 의미와의 차이를 다루지 않습니다. 센서 토픽 정지 감지 사례가 없습니다(직접 curl은 차단되어 WebFetch로 본문 확인. source_digest 접근은 OK).
   - 이 글이 더할 것: 문서 문구("발행하면 갱신")를 그대로 믿었을 때의 예측과 Fast DDS 실측을 같은 표에 놓아, 어느 정의가 Jazzy 기본 RMW 동작과 맞는지 보여 줍니다.

종합: 확인한 경쟁 글은 모두 정의 나열형입니다. 다중 publisher 노드에서 한 토픽만 멈추는 상황, 문서 간 Automatic 정의 차이, 감시 노드 쪽 요청만으로 연결이 끊기는 함정, 실측 이벤트 시점을 함께 다룬 글은 없었습니다. 기존 HuntLab 공개 글 `ros2-qos-deadline-period-compatibility`는 deadline 호환성 계산과 "발행자 Default + 구독자 x → 비호환"을 이미 다룹니다. 이번 글은 이를 요약 링크로 처리하고 liveliness 쪽을 중심으로 합니다.
