# 경쟁 글 대비 차별점: ros2-wifi-topic-list-visible-some-topics-echo-qos-vs-fragment-measurement

확인일 2026-11-21. 영어 상위 결과 4개를 직접 읽었다. 한국어 검색(`ros2 topic list 보이는데 echo 안됨 와이파이 cyclonedds` 등)에서는 같은 질문을 다루는 한국어 글이 상위에 나오지 않았다. 그래서 한국어 경쟁 글은 비교하지 않았다.

1. [Fictionlab — ROS 2 QoS Explained for Field Robots](https://fictionlab.pl/blog/ros-2-qos-explained-why-your-topics-silently-drop-messages-in-the-field/) (Tom Cosgrove, 2026-10-30)
   - 다루는 것: QoS 호환 규칙, 와이파이 손실, 큰 메시지 조각화("조각 하나가 빠지면 샘플 전체가 무효"), `tc netem` 손실 주입, `topic info --verbose`.
   - 빠졌거나 틀린 것: "CLI의 기본 구독은 reliable·volatile이라 best effort 센서 토픽을 그냥 echo하면 불일치를 재현한다"고 쓰는데, ros2cli 소스와 다르다. IP 조각 수 계산, `MaxMessageSize`, 커널 재조립 대기, 토픽별 수신 수 측정이 없다.
   - 이 글이 더할 것: 배포판별 echo QoS 소스 근거, 링크 교체 판별, 조각 수 산술, 카운터 확인 명령.
2. [Kopik — ROS 2 QoS Compatibility: Why Topics Won't Connect](https://kopik.io/blog/ros2-qos-compatibility-publisher-subscriber-not-connecting) (Kopik team, 2026-10-07)
   - 다루는 것: Request vs Offered 모델과 정책별 호환 표, 기본 QoS(keep last 10, reliable, volatile), `topic info --verbose`·`ros2 doctor`·`rqt_graph`.
   - 빠졌거나 틀린 것: 노드 기본 QoS(reliable)를 echo의 기본으로 읽히게 쓴다. 와이파이·큰 메시지·IP 조각을 다루지 않는다.
   - 이 글이 더할 것: echo는 노드 기본값과 다르게 자동 선택한다는 점과, 링크·크기 의존 원인을 가르는 법.
3. [Myzhar — ROS 2 QoS: Why Your Nodes Aren't Talking](https://myzhar.tech/tutorials/ros2/understanding-ros2-qos/) (Walter Lucetti, 2026-09-18)
   - 다루는 것: offered ≥ requested 원칙, reliability/durability 표, `topic info --verbose`, QoS override.
   - 빠졌거나 틀린 것: "`ros2 topic echo /my_sensor_topic`은 reliable 구독이 기본이라 best effort 토픽이면 아무것도 안 보인다"고 쓰는데 소스와 다르다. 와이파이·조각화·측정 방법이 없다.
   - 이 글이 더할 것: 위와 같고, 경고 문구(`offering incompatible QoS`)로 불일치를 바로 확인하는 법도 더한다.
4. [Southampton Go2 troubleshooting](https://robots.ecs.soton.ac.uk/go2/troubleshooting) (작성자·날짜 미표기, © 2025 SooratiLab)
   - 다루는 것: "echo 출력이 멈추면 와이파이 대역폭 포화로 패킷이 버려지는 것"이라는 진단과 "유선을 써라"는 처방.
   - 빠졌거나 틀린 것: 근거나 측정이 없다. QoS, IP 조각, `ipfrag_*`, `MaxMessageSize`, 토픽별 비교가 없다. 작성자·날짜가 없어 핵심 근거로 쓰지 않는다.
   - 이 글이 더할 것: 대역폭 포화와 조각 재조립 정지를 구분할 카운터와 수신 수 표.

이 글이 실측으로 더할 것: 현재 실측은 이 runner의 커널 기본값 읽기(`ipfrag_*` sysctl)와 카운터 명령 실행 확인뿐이다. 와이파이·ROS 수신 수 실측은 없다. 하네스가 `experiment/results.json`을 쓰면 그 값만 measured 구간에 들어간다. 그 전에는 측정 계획과 공식 근거·산술로 차별화한다. 이 차별점은 위 4개 글에 없는 내용이므로 INSUFFICIENT 사유가 아니라고 판단했다.
