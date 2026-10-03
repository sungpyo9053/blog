# 실험 계획: 센서 토픽 하나가 멈춘 것을 liveliness가 알려 주는가, deadline은 어떤가

## 질문

20 Hz 카메라 토픽과 1 Hz 진단 토픽을 같은 노드가 발행합니다. 카메라만 멈췄을 때
ROS 2 Jazzy 기본 RMW(rmw_fastrtps_cpp)에서 구독자가 받는 신호는 무엇일까요.
Automatic liveliness(lease 2000 ms)의 Liveliness changed일까요, deadline(100 ms)의
Requested deadline missed일까요. 그리고 liveliness는 멈춘 publisher를 실제로
언제 "살아 있지 않음(not alive)"으로 바꾸는가, 이것은 문서만으로 알 수 없으므로 실행해서 잽니다.

## 환경과 구조

- ros:jazzy-ros-base 컨테이너, 네트워크 없음, rclpy + std_msgs(UInt32)만 사용
- 감시자(monitor)는 실험 스크립트의 주 프로세스입니다. 드라이버(driver)는 같은 스크립트를
  `driver` 인자로 띄운 자식 프로세스입니다. 둘은 서로 다른 프로세스라 DDS participant도 다릅니다.
  같은 participant 안에서 결과가 섞이는 것을 피하려는 구조입니다.
- 감시자는 stdin 명령(`stop camera`, `stop all`, `destroy`, `exit`)으로 드라이버를 조작하고,
  드라이버는 자기 쪽 사건(마지막 발행 시각, Liveliness lost, Offered deadline missed)을 JSON 줄로 돌려줍니다.
- 시각은 두 프로세스 모두 `time.monotonic()`(Linux CLOCK_MONOTONIC, 프로세스 간 공유)로 잽니다.
  QoS 이벤트 시각은 rclpy 콜백이 실행된 시각입니다. 즉 executor 처리 지연이 포함됩니다.
- 사례마다 토픽 이름 접두사(/a, /b, ...)를 달리하고 감시 노드도 새로 만듭니다.
- 각 사례는 카메라 메시지 20개 이상 수신, 감시 구독의 liveliness alive_count ≥ 1 확인,
  0.3초 안정화를 거친 뒤 조작합니다(`setup_ok`).

## research.md 기준 예측값

research.md `## Experiment 단계 제안`의 표와 같은 값(20 Hz, 1 Hz, deadline 100 ms, lease 2000 ms)을 씁니다.

| 사례 | 설정 | 사용자 문서 정의로 본 예측 | DDS/Fast DDS 정의로 본 예측 |
| --- | --- | --- | --- |
| A 카메라만 정지 | camera(20 Hz, deadline 100, Automatic, lease 2000) + diagnostics(1 Hz, Automatic, lease 2000) | 마지막 수신 후 약 100 ms에 Requested deadline missed 시작, liveliness 변화 없음 | 같음 |
| B 모든 발행 정지, 프로세스·노드 생존 | A와 같은 드라이버, 두 타이머 모두 정지, lease의 3배 이상 관찰 | lease 2000 ms 경과 뒤 Liveliness changed(not_alive) | 변화 없음(미들웨어가 announcement로 갱신, 2000 × 2/3 ≈ 1333.3 ms 주기) |
| C MANUAL_BY_TOPIC 카메라 정지 | camera MANUAL_BY_TOPIC, lease 2000, 진단은 계속 | 마지막 발행 후 약 2000 ms에 Liveliness changed, 발행자 쪽 Liveliness lost | 같음 |
| D Automatic 드라이버 노드 삭제(프로세스 생존) | destroy_node | Liveliness changed | Liveliness changed(데모 README) |
| E 호환성 | 발행자 Default + 감시 deadline 100 / 발행자 Default + 감시 lease 150 / 발행자 Default(Automatic) + 감시 MANUAL_BY_TOPIC / 발행자 lease 200 + 감시 150·300·200 | 비호환·비호환·비호환·비호환(−50)·호환(+100)·호환(0) | 같음 |

계획 단계에서 덧붙인 사례(research.md 표에는 없음):

- K 드라이버 프로세스 SIGKILL(Automatic, lease 2000): 프로세스 자체가 죽었을 때 Automatic liveliness가
  알려 주는지 확인합니다. DDS 정의("프로세스 수준 실패 감지용")로 본 예측은 lease 2000 ms 전후의 not_alive입니다.
- E의 기본 QoS 구독에 100 ms 수신 간격 워치독 타이머(10 ms마다 확인)를 붙입니다. 드라이버 QoS를 바꿀 수
  없을 때의 대안이 실제로 정지를 잡는지 봅니다. 예측: 마지막 수신 후 100 ms에 확인 주기 10 ms를 더한 범위 안.

## 무엇을 어떻게 재는가

- A: 정지 직전 deadline 콜백 수, 드라이버의 마지막 발행 → 감시자의 마지막 수신(ms), 마지막 수신 →
  첫 Requested deadline missed(ms), 관찰 4.5초 동안 deadline 콜백 수와 total_count, 같은 기간 진단 수신 수,
  정지 후 카메라 Liveliness changed 이벤트 목록, 끝났을 때 alive_count, 드라이버 쪽 Liveliness lost·Offered deadline missed 수.
- B: 관찰 6.5초(lease의 3.25배) 동안 카메라·진단 구독의 Liveliness changed 이벤트, 끝났을 때 alive_count,
  그래프에 보이는 카메라 publisher 수(`count_publishers`), deadline 콜백 수, 드라이버 쪽 Liveliness lost 수.
- C: 정지 전 alive_count, 마지막 발행 → 첫 not_alive_count 증가(ms)와 lease와의 차이, 마지막 발행 →
  드라이버 쪽 Liveliness lost(ms), 진단 수신 수와 진단 구독의 liveliness 이벤트.
- D: destroy_node 호출 직전 시각 기준 이벤트 목록(alive_count_change와 not_alive_count_change를 구분), 호출 소요 ms,
  삭제 전후 그래프상 publisher 수, 삭제 뒤 수신 메시지 수.
- K: SIGKILL 직전 시각 기준 첫 alive_count 감소·첫 not_alive 증가(ms), 5초 뒤 그래프상 publisher 수.
- E: 각 구독의 수신 메시지 수, Requested incompatible QoS total_count와 마지막 정책 이름, 워치독의 마지막 수신 →
  발화(ms)와 마지막 발행 → 발화(ms).
- 모든 숫자는 실행 중 콜백 시각의 차이로 계산해 JSON 줄로 출력합니다. 결과값을 코드에 적어 두지 않습니다.
  한 번 실행은 약 40초이고, 하네스가 정식으로 5회 실행합니다.

## 시행착오(시험 실행에서 실제로 고친 점)

1. 첫 시험 실행에서 C의 진단 구독에 "정지 후" liveliness 이벤트(alive_count +1)가 잡혔습니다. 원인은 진단 첫 메시지만
   기다리고 바로 카메라를 멈춘 것이었습니다. 진단 publisher의 시작 시점 alive 전환이 정지 직후에 도착했던 것입니다.
   모든 감시 구독이 alive_count ≥ 1이 된 것을 확인하고 0.3초 기다린 뒤 조작하도록 바꿨고, 이후 해당 이벤트는 사라졌습니다.
2. D(노드 삭제)는 처음에 이벤트가 하나도 없는 것으로 나왔습니다. 기준 시각을 드라이버가 destroy_node를 **마친 뒤**의
   시각으로 잡았는데, 감시자의 이벤트가 그보다 먼저 도착해 걸러졌기 때문입니다. destroy_node 호출 **직전** 시각을
   기준으로 바꾸고, 호출 소요 시간과 그래프상 publisher 수, 삭제 뒤 수신 수를 함께 기록하도록 고쳤습니다.
3. B·D·K에 `count_publishers` 기록을 추가했습니다. "이벤트가 없음"이 publisher가 그래프에 남아 있어서인지를 구분하기 위해서입니다.
4. E의 비호환 구독 때문에 드라이버 stderr에 "requesting incompatible QoS" 경고가 찍힙니다. 이것은 의도한 관측이며 실패가 아닙니다.

## 한계

- 컨테이너 안 두 프로세스(같은 호스트, 네트워크 없음, 1 CPU) 측정입니다. 실제 카메라·실제 네트워크·실물 로봇 검증이 아닙니다.
- rmw_fastrtps_cpp 기본 설정만 봤습니다. Cyclone DDS, Connext, Zenoh는 다를 수 있습니다.
- 이벤트 시각은 rclpy 콜백 실행 시각이라 executor 지연이 포함됩니다. 이벤트가 합쳐져 콜백이 한 번만 불릴 수 있으므로
  "콜백 횟수"보다 "첫 이벤트 시점과 카운트 값"을 우선합니다.
- deadline·liveliness 이벤트와 워치독은 진단 신호입니다. 로봇 정지 로직이나 하드웨어 비상정지를 대신하지 않습니다.
