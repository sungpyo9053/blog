# 경쟁 글 대비 차별점: ros2-liveliness-lease-duration-vs-deadline-topic-stall

검색어 "ROS 2 liveliness lease duration deadline QoS detect sensor stopped publishing", "ROS2 QoS liveliness lease duration deadline 설명",
"ROS2 QoS liveliness lease duration velog OR tistory"로 찾은 상위 글을 2026-10-04 원문으로 열어 읽었다(모두 이 runner에서 source_digest 접근 OK).

1. https://myzhar.tech/tutorials/ros2/understanding-ros2-qos/ (Walter Lucetti, 2026-09-18, 영어)
   - 다루는 것: QoS 정책 전반과 호환성 규칙(제공 deadline ≤ 요청, 제공 lease ≤ 요청). deadline 위반 시 미들웨어 이벤트가 "조용해진 센서 감지에 매우 유용"하다고 설명.
     Automatic은 "노드 자체가 살아 있는 한 노드의 모든 publisher를 살아 있다고 본다"고 적는다.
   - 빠졌거나 틀린 것: 자기 설명(노드 생존 기반)이 ROS 2 사용자 문서(발행 기반)와 다르다는 점을 언급하지 않는다. 발행자 Default deadline/lease일 때 구독자 요청이 비호환이라는
     점, 이벤트 콜백 코드, 다중 publisher 노드에서 한 토픽만 멈추는 경우가 없다.
   - 이 글이 실측으로 더할 것: 진단 토픽이 계속 나가는 동안 카메라만 멈출 때와 모든 발행이 멈출 때 Automatic·MANUAL_BY_TOPIC liveliness와 deadline 이벤트가 각각 오는지, 언제
     오는지를 Jazzy·Fast DDS에서 실측해 두 정의 중 어느 쪽이 기본 RMW 동작과 맞는지 판정한다. 발행자 Default에 감시 노드만 deadline을 요청할 때 수신 0인지도 실측한다.
2. https://velog.io/@gaebalsebal/ROS2-QoSQuality-of-Service-Profile%EC%9D%B4%EB%9E%80 (작성자 YJ, 2024-06-13, 한국어)
   - 다루는 것: 정책별 한 줄 정의와 기본 프로필.
   - 빠졌거나 틀린 것: "Automatic: publisher가 lease duration 기간동안 메세지를 전송하지 않으면 비활성 상태로 간주"라고 **publisher 단위·발행 기반**으로 적는다. 공식 사용자 문서
     (노드의 어느 publisher든 발행하면 모든 publisher 갱신)와도, DDS·Fast DDS(미들웨어가 프로세스 단위로 갱신)와도 다르다. 이 설명대로면 카메라만 멈춰도 liveliness 이벤트가 와야
     한다. 호환성 표·이벤트·코드가 없다.
   - 이 글이 실측으로 더할 것: 그 서술이 실제와 맞는지(카메라만 정지 / 모든 발행 정지·프로세스 생존에서 Automatic Liveliness changed가 오는지)를 실측으로 판정하고, 세 계열 공식
     정의를 원문 줄 링크로 대조한다.
3. https://velog.io/@happy_lee0_0/ROS2-Qos-tf10 (작성자 이준혁, 2025-01-01, 한국어)
   - 다루는 것: QoS 정책 목록과 `QoSProfile(liveliness=AUTOMATIC, liveliness_lease_duration=1.0, deadline=..., ...)` 형태의 퍼블리셔 설정 코드.
   - 빠졌거나 틀린 것: Liveliness를 "정해진 주기 내 노드 또는 토픽의 생사 확인"으로만 적어 Automatic이 어느 단위를 보는지 구분하지 않는다. 구독자 쪽 이벤트 콜백·호환성 조건이 없고,
     예제는 발행자 설정만 있어 무엇이 감지되는지 관측하지 않는다.
   - 이 글이 실측으로 더할 것: 구독자 `SubscriptionEventCallbacks`로 deadline·liveliness 이벤트를 실제로 받아 alive_count/not_alive_count, total_count와 첫 이벤트까지 경과 시간을 실측해
     "노드 생사"와 "토픽 정지"가 어떤 이벤트로 갈리는지 보여 준다.
4. https://www.learnros2.com/ros/ros2-building-blocks/quality-of-service (작성자·날짜 미표시, 영어)
   - 다루는 것: QoS 기본 개념, 기본 프로필(liveliness system default, deadline·lease default), deadline 콜백 C++ 코드와 콜백 타입 목록.
   - 빠졌거나 틀린 것: Automatic과 Manual by topic의 차이, lease duration 동작, 미들웨어 자동 단언, 다중 publisher 노드 사례가 없다. 작성자·날짜 미표시라 핵심 근거로는 쓰지 않는다.
   - 이 글이 실측으로 더할 것: deadline 콜백이 "멈춘 토픽"에서 실제 언제부터 얼마나 누적되는지, 그리고 liveliness 콜백은 같은 상황에서 오지 않는지(또는 오는지)를 같은 실행에서 나란히 측정한다.

종합: 확인한 경쟁 글은 모두 정의 나열형이다. 다중 publisher 노드에서 한 토픽만 멈추는 상황, 문서 간 Automatic 정의 차이, 감시 노드 쪽 요청만으로 연결이 끊기는 함정(드라이버가
QoS 프로필 이름만 허용할 때), 실측 이벤트 시점을 함께 다룬 글은 찾지 못했다. HuntLab 기존 공개 글 `ros2-qos-deadline-period-compatibility`는 deadline 호환성 산술과
"발행자 Default + 구독자 x → 비호환"을 이미 다루므로, 이번 글은 이를 요약·링크하고 liveliness 쪽과 실측을 중심으로 한다(WordPress 공개 30·초안 113·예약 1 전체 목록에서 liveliness를
주제로 한 글은 없음을 run 디렉터리의 editorial-inventory.json으로 확인. 이것은 중복 검사 보조 확인이며 사실 근거가 아니다).
