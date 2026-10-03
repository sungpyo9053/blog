# 실험 계획: liveliness가 멈춘 카메라 토픽을 알아채는가

## 질문

ROS 2 Jazzy 기본 RMW(rmw_fastrtps_cpp)에서 센서 드라이버 프로세스는 살아 있고 카메라 토픽 발행만
멈췄을 때, 별도 프로세스의 감시 구독자가 liveliness QoS 이벤트로 그 정지를 알아채는가?
AUTOMATIC과 MANUAL_BY_TOPIC은 어떻게 다르고, 감시 노드가 lease를 요구하면 연결은 어떻게 되는가?

## 환경과 공통 설정

- `ros:jazzy-ros-base` 컨테이너, 네트워크 없음, 1 CPU·1 GiB(하네스 고정). rclpy와 std_msgs만 쓴다.
- 감시 노드(구독자)는 메인 프로세스, "카메라 드라이버"(발행자)는 `experiment.py --pub`로 띄운 **별도 자식 프로세스**다.
- 카메라 대역 토픽: `std_msgs/String`, 10 Hz, RELIABLE / VOLATILE / KEEP_LAST 10, lease 0.5 s.
- 발행자는 구독자와 연결(matched)된 뒤 2 s 동안 발행하고, 감시 쪽은 정지 후 3 s(lease의 6배) 관찰한다.
- 비교용 애플리케이션 워치독: 카메라 구독 콜백에서 마지막 수신 시각을 기록하고 10 ms 타이머가
  "마지막 수신 후 0.5 s 초과"를 검사한다(QoS 설정 없이 동작하는 방식).

## research.md 기준 예측값(실행 전, 실측 아님)

| 사례 | 내용 | 예측 |
|---|---|---|
| E1 | AUTOMATIC, 단독 발행자, 발행만 정지(프로세스 유지) | 관찰 창 동안 not_alive 증가 0회 |
| E2 | AUTOMATIC, 발행자 프로세스 SIGSTOP | not_alive 1회, 정지 후 약 0.5 s(lease) 이내 감지 |
| E3 | MANUAL_BY_TOPIC, 단독 발행자, 발행만 정지 | not_alive 1회, 마지막 수신 후 약 0.5 s(5주기), 발행자 쪽 liveliness lost도 발생 |
| E4 | 같은 프로세스·노드에서 100 Hz IMU는 계속, 카메라만 정지 | AUTOMATIC 카메라 감지 0회(E1과 같음), MANUAL_BY_TOPIC 카메라 감지 1회 |
| E5 | 호환성 | 발행자 MANUAL 0.5 s + 구독자 0.3 s → 비호환·수신 0, 구독자 1.0 s → 수신. 발행자 Default + 구독자 0.5 s → 비호환. 발행자 AUTOMATIC + 구독자 MANUAL_BY_TOPIC → 비호환. `qos_check_compatible` 판정도 같은 방향 |
| E6 | MANUAL_BY_TOPIC, 정상 10 Hz 발행 중 lease 0.05 / 0.1 / 0.2 s | 0.05 s 반복 상실, 0.1 s 경계(간헐 상실 또는 0회, 단정 안 함), 0.2 s 0회(여유 0.1 s 양수, research의 L − T 규칙을 실험 설계에서 확장 적용) |

산술 근거: 주기 T = 1/10 = 0.1 s, 0.5/0.1 = 5주기, 여유 L − T(0.05 − 0.1 = −0.05, 0.1 − 0.1 = 0),
호환 판정 요청 − 제공(0.3 − 0.5 = −0.2 비호환, 1.0 − 0.5 = 0.5 호환).

## 무엇을 어떻게 재는가

- 시각은 모두 `time.monotonic()`(컨테이너 안 두 프로세스가 같은 시스템 시계를 공유)으로 실행 중에 기록한다.
- 발행자 프로세스는 JSON 줄로 `start`(연결 후 발행 시작 시각), `stopped`(토픽별 마지막 발행 시각·발행 수),
  `liveliness_lost`(발행자 쪽 이벤트)를 감시 프로세스에 알린다.
- 정지 시각 t_stop: 발행 정지 사례는 발행자가 보고한 마지막 발행 시각, E2는 감시 쪽이 SIGSTOP을 보낸 직전 시각.
- 구독자 쪽 측정(사례·구독별 JSON 줄):
  - `msgs_received`: 수신 메시지 수(연결·수신 실패 판정용)
  - `not_alive_increments` / `not_alive_after_stop`: `SubscriptionEventCallbacks(liveliness=...)`에서
    `not_alive_count_change > 0`인 이벤트 수(전체 / 정지 이후)
  - `detect_ms_from_stop`, `detect_ms_from_last_rx`: 정지 후 첫 not_alive 이벤트까지 걸린 시간(정지 시각·마지막 수신 기준)
  - `watchdog_ms_from_stop`, `watchdog_ms_from_last_rx`: 애플리케이션 워치독이 정지를 처음 판정한 시간
  - `incompatible_qos_events`, `incompatible_policy`: `incompatible_qos` 이벤트 수와 마지막 정책 종류
  - E5·E6: `max_rx_gap_ms`(수신 간격 최댓값), E5는 `rclpy.qos.qos_check_compatible` 판정과 사유 문자열을 같은 줄에 기록
- 발행자 쪽 측정: `publisher_liveliness_lost`(토픽별 `PublisherEventCallbacks(liveliness=...)` 발생 수).
- 마지막 `summary` 줄에 핵심 판정과 전체 실행 시간(`elapsed_s`)을 모은다.
- 실패 판정: E1~E4 카메라 구독이 정지 전 메시지를 하나도 받지 못하면 `valid=false`, 종료 코드 2(실험 무효).
  E3에서 감지 0회가 나오면 숨기지 않고 그대로 출력한다.

## 시행착오(시험 실행)

1. 첫 시험 실행은 E6에서 실패했다. 토픽 이름에 lease 값을 `/e6/lease_0.05`처럼 넣었는데 ROS 2 토픽 이름은
   점(`.`)을 허용하지 않아 `InvalidTopicNameException`이 났다. 토픽 이름을 `/e6/lease_50ms` 형식으로 바꿨다.
2. 같은 첫 실행에서 측정 정의 오류를 찾았다. "정지 전 메시지"를 "수신 시각 ≤ 마지막 발행 시각"으로 셌더니,
   마지막 발행 메시지가 전달 지연 때문에 발행 시각보다 조금 늦게 도착해 "정지 후 수신 1개"로 잘못 분류됐고,
   마지막 수신 기준 감지 시간이 한 주기만큼 부풀려졌다. 정지된 토픽의 메시지는 모두 정지 전에 발행된 것이므로
   관찰 창 안의 마지막 수신을 "마지막 수신"으로 쓰고, 그 수신이 정지 시각보다 얼마나 늦었는지를
   `last_rx_ms_after_stop`으로 따로 출력하도록 고쳤다.
3. 수정 후 두 번째 시험 실행은 종료 코드 0, 전 사례 출력, 컨테이너 안 실행 시간 60 s 미만으로 통과했다.

## 한계

- 단일 컨테이너·루프백·1 CPU의 Fast DDS(rmw_fastrtps_cpp) 결과다. Cyclone DDS, rmw_zenoh, 다중 호스트 네트워크,
  실제 카메라 드라이버(realsense-ros)와 실제 하드웨어는 검증하지 않는다.
- 감지 지연은 한 실행당 사례별 1회 표본이며, 정식 5회 실행 범위로만 말할 수 있다.
- liveliness 이벤트와 워치독은 실물 로봇의 안전 정지 수단이 아니다. 이 실험은 하드웨어를 움직이지 않는다.
