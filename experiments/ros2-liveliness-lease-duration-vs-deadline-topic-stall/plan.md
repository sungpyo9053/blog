# 실험 계획: 센서 토픽 하나가 멈췄을 때 liveliness와 deadline 중 무엇이 알려 주는가

- 환경: 하네스의 `ros:jazzy-ros-base` 컨테이너, rmw_fastrtps_cpp(기본), 네트워크 없음, 1 CPU·1 GiB. rclpy·std_msgs(`Float64`)만 사용.
- 실행: `python3 experiment.py` 한 번이 60초 안에 끝나도록 설계했다(준비 최대 25초 + 관찰 8초 + 종료). 정식 5회 실행은 하네스가 하고, 수치는 `results.json`만 근거로 한다.
- 시뮬레이션·실제 하드웨어: 둘 다 아니다. 실제 카메라 없이 20 Hz로 `Float64`를 발행하는 가짜 드라이버 프로세스를 쓴다. 로봇·센서 하드웨어는 쓰지 않으므로 안전 조건이나 중지 방법은 해당 없다.

## 질문

1. 같은 노드가 20 Hz 카메라 토픽과 1 Hz 진단 토픽을 함께 발행하다가 **카메라만** 멈추면, Automatic liveliness(lease 2000 ms)는 이를 알려 주는가? deadline(100 ms)은 언제 알려 주는가?
2. 노드의 **모든** 발행이 멈췄지만 프로세스와 노드는 살아 있을 때, Automatic liveliness는 not alive가 되는가? (ROS 2 사용자 문서 정의 "발행하면 갱신"과 rmw·DDS·Fast DDS 정의 "미들웨어가 자동 갱신" 중 어느 쪽이 Jazzy 기본 RMW와 맞는가)
3. 보조: MANUAL_BY_TOPIC 카메라 정지, 노드 정상 삭제, 프로세스 SIGKILL에서 liveliness 이벤트와 카운트는 어떻게 다른가?
4. 보조: 드라이버가 기본 QoS로만 발행할 때 감시 노드가 deadline·lease·MANUAL_BY_TOPIC을 요청하면 연결이 되는가? 대안인 마지막 수신 시각 워치독은 언제 발화하는가?

## research.md 기준 예측값 (실행 전)

| 사례 | 설정 | 예측 |
| --- | --- | --- |
| A | 카메라만 정지, 진단 1 Hz 계속, 카메라 Automatic·lease 2000·deadline 100 | 마지막 수신 후 약 100 ms에 첫 Requested deadline missed, 이후 100 ms마다 total_count 누적(8000 ms 관찰이면 약 80). 카메라 구독 liveliness 변화 없음(두 정의 모두). 진단 수신 계속 |
| B | 모든 발행 정지, 프로세스·노드 생존 | 사용자 문서 정의: 약 2000 ms 뒤 not alive. rmw·DDS·Fast DDS 정의: 변화 없음(설정상 announcement 주기 2000 × 2/3 ≈ 1333.3 ms로 미들웨어가 갱신) |
| C | 카메라 MANUAL_BY_TOPIC·lease 2000, 카메라만 정지 | 마지막 카메라 발행 후 약 2000 ms에 구독자 not_alive_count +1, 발행자 Liveliness lost. 진단 liveliness 변화 없음 |
| D | Automatic 드라이버 노드 destroy, 프로세스 생존 | alive_count −1, not_alive_count 변화 없음(정상 삭제) |
| K | 드라이버 프로세스 SIGKILL, Automatic lease 2000 | lease 전후(약 2000 ms)에 alive_count −1·not_alive_count +1 |
| E | 발행자 Default + 감시 deadline 100 / lease 150 / MANUAL_BY_TOPIC, 발행자 lease 200 + 감시 150·300·200 | 비호환·비호환·비호환·비호환(−50), 호환(+100), 호환(0). 비호환 구독은 수신 0 |
| W | 발행자 Default + 기본 QoS 구독 + 임계 100 ms·확인 주기 10 ms 워치독 | 마지막 수신 후 100~110 ms 사이(임계 + 확인 주기 + executor 지연)에 발화 |

## 무엇을 어떻게 재는가

- 구조: 감시 프로세스 1개(`sensor_monitor` 노드)와 드라이버 프로세스 6개(a, b, c, d, k, w). 드라이버는 서로 다른 프로세스라서 DDS participant도 각각 따로다.
  각 드라이버 노드는 `/<case>/camera`(0.05 s 타이머, 20 Hz)와 `/<case>/diagnostics`(1.0 s 타이머, 1 Hz, Automatic·lease 2000)를 발행한다.
  드라이버 w는 카메라를 기본 `QoSProfile(depth=10)`로 발행하고(QoS를 프로필 이름으로만 고르는 드라이버 재현), 사례 E용 `/e/lease200`(Automatic, lease 200)도 발행한다.
- 시계: 모든 프로세스가 같은 커널의 `time.monotonic()`(CLOCK_MONOTONIC)을 쓴다. 메시지 `data`에 발행 시각을 넣어 감시자가 마지막 발행 시각을 안다.
- 이벤트: 감시자는 모든 구독에 `SubscriptionEventCallbacks(deadline, liveliness, incompatible_qos)`를 등록하고, 콜백이 실행된 시각과 `total_count`, `alive_count`, `not_alive_count`, `*_change`, 비호환 정책 이름을 기록한다. 드라이버는 `PublisherEventCallbacks(deadline, liveliness)`로 Offered deadline missed·Liveliness lost를 기록해 종료 시 JSON으로 넘긴다. 이벤트 시각은 콜백 실행 시각이므로 executor 지연이 포함된다.
- 준비 확인: 사례 a·b·c·d·k의 카메라 수신 20개 이상, 진단 수신 2개 이상, 두 구독 모두 alive_count ≥ 1, w 카메라 수신 20개 이상이 될 때까지(최대 25초) 기다린다. 못 채우면 `baseline_not_reached`를 출력하고 실패(종료 코드 1)한다.
- 정지: 준비가 끝나면 한 번에 stdin 명령을 보낸다. a·c·w는 `stop_camera`(카메라 타이머 취소), b는 `stop_all`(모든 타이머 취소, 노드·프로세스 유지), d는 `destroy`(`destroy_node()`, 프로세스와 rclpy context는 유지), k는 `SIGKILL`. 이후 8.0초(lease의 4배) 관찰한다.
- 출력(JSON 줄, 모두 실행 중 측정):
  - A·B·C: 정지 명령 기준 마지막 카메라 발행 시각, 마지막 수신→첫 deadline missed(ms), 관찰 끝의 deadline `total_count`와 콜백 수, 관찰 창 길이, 정지 후 카메라·진단 liveliness 하락 이벤트(alive −/not_alive +) 수와 첫 이벤트 시점, 정지 후 진단 수신 수, 드라이버 쪽 Liveliness lost·Offered deadline missed.
  - D·K: 명령/SIGKILL 기준 liveliness 이벤트 시점과 네 카운트, deadline, 관찰 끝 ROS 그래프의 카메라 publisher 수(`count_publishers`).
  - W: 워치독 첫 발화의 마지막 수신·발행 대비 지연.
  - E: 구독별 수신 메시지 수, Requested incompatible QoS 이벤트 수, 마지막 비호환 정책 이름.
  - run_info: RMW 이름, 준비 시간, 관찰 길이, 정지 명령 간 시간차.
- 판정: 질문 2는 B의 `camera_liveliness_drop_events`가 0인지(미들웨어 갱신 정의와 일치), 약 2000 ms 근처에서 1 이상인지(사용자 문서 정의와 일치)로 가린다. 단, 결과는 Jazzy·rmw_fastrtps_cpp·단일 호스트(네트워크 없음) 한정이다.
- 측정하지 않는 것: 다른 RMW(Cyclone DDS, Zenoh 등), 다중 호스트 네트워크, 실물 카메라·드라이버 내부 정지, rclcpp, 같은 프로세스 안 다른 노드의 갱신 효과.

## 시행착오 (시험 실행)

- 1차 시험 실행(`--try`): 종료 코드 0, 60초 제한 안에 끝남. 네트워크 없는 컨테이너에서 기본 discovery 설정으로 프로세스 간 연결이 됐으므로 discovery 환경 변수는 추가하지 않았다.
- 1차 출력에서 기준 시각을 잘못 잡은 필드를 고쳤다(측정 방식이 아니라 표시 기준 수정).
  - A·C의 "마지막 발행 이후 관찰 시간"이 계속 발행 중인 진단 토픽 기준이라 수백 ms로 짧게 나오고, C의 첫 liveliness 이벤트가 진단 발행 기준으로 음수로 나왔다. → 카메라 마지막 발행 기준으로 바꾸고, "모든 토픽의 마지막 발행" 기준은 모든 발행을 멈추는 B에서만 쓰도록 했다.
  - D의 기준 시각을 드라이버가 `destroy_node()` 반환 뒤 기록한 시각으로 잡아, 감시자의 liveliness 이벤트가 기준보다 먼저(음수) 찍혔다. 삭제 도중에 이미 연결 해제가 전달되기 때문이다. → 기준을 감시자가 명령을 보낸 시각으로 바꾸고, `destroy_node()` 반환 시각은 별도 필드로 남겼다.
- 2차 시험 실행: deadline `total_count`가 누적값이라 일부 실행에서 정지 전(매칭 직후 첫 샘플 전) 놓친 주기까지 포함돼 정지 후 증가분보다 1 크게 찍혔다. → 정지 후 증가분(`missed_after_last_rx`, `total_count_change` 합)과 누적값(`cumulative_total_count_at_window_end`)을 따로 출력하도록 바꿨다. 같은 실행에서 워치독이 준비 단계(1 CPU에서 프로세스 7개 기동 중)에 수신 간격이 임계를 넘어 한 번 더 발화했다. 정지 후 발화와 섞이지 않게 정지 전 발화의 간격을 `fires_before_stop_gap_ms`로 따로 남긴다(워치독 오경보 가능성의 근거로 쓸 수 있음).
- 3차 시험 실행: 종료 코드 0. 출력 필드가 의도대로 나오는 것을 확인했다. K 줄의 의미 없는 null 필드를 없앴다.
