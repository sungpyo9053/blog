# 경쟁 글 대비 차별점: ros2-deadline-qos-average-rate-vs-max-interval

모두 2026-10-03에 원문을 직접 열어 읽었다. 문장은 복제하지 않고 범위만 요약한다.

1. https://physicalailab.io/en/ros2-real-time-control-guide/ (Physical AI Lab, 2026-07-29 게시·08-01 수정, 영어)
   - 다루는 것: real-time 제어를 "높은 프레임레이트가 아니라 정해진 마감 안의 완료와 제한된 지터"로 설명한다. 가끔 멈추는 1 kHz 루프가 최악값이 맞는 느린 루프보다 못할 수 있다는 원칙과 측정 중심 검증을 강조한다.
   - 빠진 것: ROS 2 deadline QoS의 정의·호환성·이벤트, 시계 문서의 'real time' 구분, `ros2 topic hz` 해석, 수치 예제가 없다.
   - 이 글이 실측으로 더할 것: 같은 평균 100 Hz의 두 패턴을 실제 ROS 2 Jazzy 발행자·구독자에 넣었을 때 Offered/Requested deadline missed 이벤트가 어떻게 갈리는지를 하네스 측정값(results.json)으로 보여 준다. 원칙("평균보다 최악값")을 ROS 2 이벤트 수로 확인한다.
2. https://thomasthelliez.com/blog/build-sensor-actuator-timing-budget-ros-2-robot/ (Thomas Thelliez, 2026-06-08, 영어)
   - 다루는 것: Period·Latency·Jitter·Age를 나눈 타이밍 예산과 "평균보다 최악값"이라는 관점이다. sensor_age_ms 같은 예산 예시 값도 있다. deadline은 "업데이트가 멈추면 이벤트를 낸다" 수준으로 언급한다.
   - 빠진 것: deadline의 공식 정의, offered/requested 호환 방향과 비호환 결과, `ros2 topic hz`의 max 해석이 없다.
   - 이 글이 실측으로 더할 것: deadline 하나에 좁혀 '여유 = deadline − 간격'을 계산하고, 그 예측을 실제 이벤트 수와 수신 간격 max(하네스 측정)로 대조한다. deadline을 30 ms로 늘렸을 때 15 ms 구독자가 실제로 수신하지 못하고 비호환 이벤트(정책 DEADLINE)를 받는지도 측정값으로 보인다.
3. https://myzhar.tech/tutorials/ros2/understanding-ros2-qos/ (Walter Lucetti/Myzhar, 영어 튜토리얼)
   - 다루는 것: deadline을 "두 연속 메시지 사이의 최대 예상 주기"로 설명하고 offered/requested 약속을 쉬운 말로 풀었다. 호환 조건을 "publisher's offered period ≤ subscriber's requested period"로 정확히 제시하고, deadline miss 시 이벤트가 난다고 언급한다.
   - 빠진 것: 지터, 평균 빈도와 최대 간격의 차이, 이벤트 처리 예제가 없다. `ros2 topic hz`는 QoS 확인 퀴즈의 오답 선택지로만 나온다. '실시간'의 의미 구분도 없다.
   - 이 글이 실측으로 더할 것: 호환 조건이 실제로 연결을 끊는지(15 ms 요청 구독자의 수신 개수·비호환 이벤트), 평균이 같아도 deadline miss가 나는지를 실측으로 보이고, hz의 max 줄 읽기를 더한다.
4. https://velog.io/@hy_k/ROS2-DDS-%EA%B7%B8%EB%A6%AC%EA%B3%A0-QoS (HY K, velog, 2024-09-08, 한국어)
   - 다루는 것: DDS 도입 후 ROS 2의 변화와 QoS 6개 정책을 나열한다. deadline은 "정해진 주기 안에 데이터가 발신 및 수신되지 않을 경우 EventCallback 실행"으로 설명한다.
   - 빠진 것·틀린 것: 변화점으로 "실시간 데이터 전송 보장"을 적었지만, ROS 2 설계 배경 문서는 real-time 성능에 실시간 OS와 결정적 사용자 코드가 함께 필요하다고 쓴다(L63-L64). 미들웨어 도입만으로 보장된다는 서술은 근거보다 넓다. 호환 방향, 최대 간격, 수치 예제가 없다.
   - 이 글이 실측으로 더할 것: '실시간'이라는 이름과 보장의 차이를 공식 문서로 바로잡는다. 일반 Linux 컨테이너에서 실제 측정한 발행·수신 간격의 max와 deadline 이벤트로, 보장이 아니라 관측이라는 점을 보여 준다.
5. (참고, 본문 링크 금지) Robotics Stack Exchange 22252 채택 답변(점수 4). runner의 `source_digest`에서 페이지 접근에 실패해 Stack Exchange 공개 API로 본문을 읽었다.
   - 다루는 것: ROS가 말하는 real-time은 대개 soft realtime이고, 엄격한 지연 보장은 hard realtime이라는 구분이다.
   - 빠진 것: 공식 문서 인용, QoS deadline과의 연결, 수치 판정 방법이 없다.
   - 이 글이 더할 것: 같은 구분을 ROS 2 설계 문서(L45-L56)로 뒷받침하고 deadline 계산·실측으로 연결한다.

판정: 경쟁 글은 원칙("최악값이 중요")이나 정의·호환 방향 한 줄에 그친다. 공식 정의 문장, 호환성 표, `ros2 topic hz` 소스 해석, 산술 예제, 실제 ROS 2 이벤트 측정을 한 흐름으로 묶은 글은 찾지 못했다. 더할 것이 있으므로 INSUFFICIENT 사유가 아니다.
