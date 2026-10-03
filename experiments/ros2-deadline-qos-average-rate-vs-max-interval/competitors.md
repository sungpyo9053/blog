# 경쟁 글 대비 차별점: ros2-deadline-qos-average-rate-vs-max-interval

모두 2026-10-03에 원문을 직접 열어 확인했다. 이 글이 더하는 것은 실측이 아니라 공식 원문 대조와 자체 산술 검산이다. 실측(ROS 2 실행)은 하지 않았으므로 "실측으로 더할 것"은 없다. 고유 가치는 산술 예제·소스 확인·용어 구분에서 나온다.

1. https://physicalailab.io/en/ros2-real-time-control-guide/ (Physical AI Lab, 2026-07-29 게시, 08-01 수정, 영어)
   - 다루는 것: real-time 제어는 "높은 평균 프레임레이트가 아니라 정해진 마감 안의 완료와 제한된 지터(bounded jitter)"라는 원칙, 측정 중심 접근.
   - 빠진 것: ROS 2 deadline QoS 정의·호환성, clock 문서의 'real time'과의 구분, `ros2 topic hz` 출력 해석, deadline 조정이 구독자에 미치는 영향이 없다. 수치 예제도 없다.
   - 이 글이 더할 것: 같은 평균을 가진 두 기록의 계산, QoS 정의 문장으로 '최대 간격' 판정 근거, 호환성 표에 따른 대가, `max:` 줄 읽는 법.
2. https://thomasthelliez.com/blog/build-sensor-actuator-timing-budget-ros-2-robot/ (Thomas Thelliez, 2026-06-08, 영어)
   - 다루는 것: Period·Latency·Jitter·Age를 구분하는 타이밍 예산, "평균 지연은 가장 덜 흥미로운 숫자", soft/firm/hard 루프 구분.
   - 빠진 것: deadline을 "timing tool"로 나열만 하고, 정의나 offered/requested 호환성은 설명하지 않는다. `ros2 topic hz`, clock 문서의 'real time' 구분도 없다.
   - 이 글이 더할 것: deadline QoS 한 정책에 좁힌 계산(여유 = deadline − 간격), 늘렸을 때 비호환이 되는 산술, hz 소스 근거.
3. https://hackmd.io/@st9540808/BkaxoWRiI (HackMD "ROS2 QoS", Foxy를 최신으로 언급해 2020년경으로 추정, 한국어 사용자 문서)
   - 다루는 것: deadline 정의 원문 인용 등 QoS 정책 개요.
   - 빠진 것·문제: deadline 호환성, 실시간 의미, 지터·최대 간격, hz 해석이 없다. Lifespan 정의 문장이 중간에 끊긴 미완성 상태다.
   - 이 글이 더할 것: 2026년 Rolling·Jazzy 원문 기준의 정의와 표, 계산 예제.
4. https://robertchoi.gitbook.io/ros2/03-dds (Robert Choi GitBook "03장 DDS란 무엇인가?", 2020년 1월경, 한국어)
   - 다루는 것: DDS를 "실시간 발간자-구독자 통신 미들웨어"로 소개, deadline은 "정해진 주기 안에 Pub/Sub 되지 않으면 EventCallback".
   - 빠진 것·문제: DDS의 'real-time' 표기가 무엇을 보장하는지 설명하지 않아, RSE 질문자가 겪은 혼동을 그대로 남긴다. 호환성은 이미지 표뿐이고 최대 간격·hz 해석이 없다.
   - 이 글이 더할 것: 'real-time'이라는 이름과 보장의 차이(배경 문서 L58-L64), 계산 예제.
5. (참고, 본문 링크 금지) Robotics Stack Exchange 22252의 채택 답변(점수 4)
   - 확인 경로: runner에서 페이지 접근에 실패해, Stack Exchange 공개 API로 질문·답변 본문을 읽었다.
   - 다루는 것: ROS가 말하는 것은 대체로 "soft realtime"이고, 엄격한 지연 보장은 "hard realtime"이라는 구분.
   - 빠진 것: 공식 문서 인용, QoS deadline과의 연결, 수치 판정 방법이 없다.
   - 이 글이 더할 것: 같은 구분을 ROS 2 공식 설계 문서(L47-L56)로 뒷받침하고, deadline 계산으로 연결한다.

판정: 경쟁 문서들은 일반 원칙(평균보다 최악값)이나 정의 한 줄에 그친다. 공식 정의·호환성 표·`ros2 topic hz` 소스·산술 예제를 한 흐름으로 묶은 문서는 확인되지 않아 더할 것이 있다. INSUFFICIENT 사유 아님.
