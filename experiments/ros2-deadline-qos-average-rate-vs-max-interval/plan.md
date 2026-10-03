# 실험 계획: 평균 100 Hz 토픽은 15 ms deadline QoS를 지키는가

## 질문

센서 토픽이 평균 100 Hz(평균 주기 10 ms)로 발행되면 15 ms deadline을 걸어도
마감을 지킨다고 볼 수 있는가? 아니면 판정을 정하는 것은 평균이 아니라 최대 간격인가?
그리고 발행자가 deadline을 30 ms로 늘려 통과시키면, 15 ms를 요청하던 구독자에게는
무슨 일이 생기는가?

## research.md 기준 예측값

research.md의 산술 예제(간격 8,8,8,8,25,8,8,9,9,9 ms / 균일 10 ms, deadline 15 ms,
발행자 deadline 30 ms)와 QoS 문서의 deadline 정의·호환성 표를 근거로 예측한다.
한 시나리오는 이 간격 패턴 50주기, 즉 간격 500개(메시지 501개)다.

| 시나리오 | 설정 | 예측 |
| --- | --- | --- |
| uniform | 10 ms 균일, 발행자·구독자 deadline 15 ms | 평균 약 100 Hz, 최대 간격 약 10 ms, deadline missed 0회 |
| jitter | 흔들림 패턴, 발행자·구독자 deadline 15 ms | 평균 약 100 Hz(uniform과 같음), 최대 간격 약 25 ms, 주기마다 25 ms 간격 1개가 15 ms를 넘으므로 Offered·Requested deadline missed 각각 약 50회(주기당 1회. 25 ms < 2×15 ms라 한 간격에서 1회) |
| widened | 흔들림 패턴, 발행자 deadline 30 ms, 구독자 A 요청 15 ms, 구독자 B 요청 30 ms | A: 요청 15 < 제공 30이라 비호환, Requested incompatible QoS 이벤트(정책 DEADLINE) 발생, 수신 0개. B: 호환, 501개 수신, 25 ms < 30 ms라 deadline missed 0회. 발행자: Offered incompatible QoS 이벤트 발생 |

간격이 deadline과 정확히 같을 때의 판정은 문서로 확인되지 않았으므로 예측하지 않는다.
설계한 간격은 경계값(15 ms, 30 ms)과 겹치지 않게 했다.

## 무엇을 어떻게 재는가

- 환경: 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 실행한다.
  rmw는 기본값(rmw_fastrtps_cpp)이고, 사용한 rmw 이름을 실행 중에 읽어 출력한다.
- 노드 구성: 한 프로세스 안에 발행 노드와 구독 노드를 시나리오마다 새로 만든다. 토픽 타입은
  `std_msgs/UInt32`이고 메시지 값은 순번이다. QoS는 RELIABLE, depth 10, deadline만 바꾼다.
  구독 콜백과 QoS 이벤트 콜백은 별도 스레드의 SingleThreadedExecutor가 처리한다.
- 발행: 메인 스레드가 간격 패턴으로 계산한 절대 목표 시각(`time.monotonic_ns`)까지 잠든 뒤
  `publish()` 한다. 늦게 깨어나면 다음 목표 시각이 이미 지났으므로 곧바로 발행한다.
  그래서 평균 주기는 계획대로 유지되고, 실제 간격의 흔들림은 그대로 측정값에 남는다.
- 발행 간격: 매 `publish()` 직후의 monotonic 시각 차이.
- 수신 간격: 구독 콜백이 불린 시각의 차이. `ros2 topic hz`의 계산 방식(mean, rate = 1/mean,
  min, max, 모표준편차)을 그대로 따른다. 다만 시계는 ROS clock이 아닌 monotonic이다.
  이 값은 콜백 시점이므로 rmw 계층의 deadline 판정 시점과 같지 않다.
- deadline 이벤트: `PublisherEventCallbacks(deadline=…)`와 `SubscriptionEventCallbacks(deadline=…)`가
  받은 `total_count_change`를 콜백 시각과 함께 기록한다. 첫 발행부터 마지막 발행까지 사이에
  받은 것만 `*_during_run`으로 센다. 마지막 발행 뒤 300 ms 관찰 구간에서는 메시지가 없으므로
  deadline 이벤트가 계속 나는 것이 정상이다. 이 값은 `*_after_last_publish`에 따로 적고 판정에
  쓰지 않는다.
- 비호환: `incompatible_qos` 콜백의 `total_count`와 `last_policy_kind`. 수신 개수와 순번으로
  `received`와 `lost`(발행 수 − 받은 고유 순번 수)를 센다.
- 연결 대기: 시나리오마다 호환 구독자 수만큼 매칭되고 예상한 비호환 이벤트가 올 때까지
  최대 5초 기다린다. 결과는 `discovery_matched`, `discovery_s`로 남는다.
- 출력: 시나리오마다 JSON 한 줄, 마지막에 총 소요 시간 한 줄. `planned` 블록은 입력 패턴에서
  계산한 계획값이고, `publisher`·`subscribers` 블록이 실행 중 측정값이다.
  한 번 실행은 약 17초(컨테이너 기동 제외)다.

## 판정 기준

- 평균만으로 판정할 수 없다는 주장이 지지되려면, uniform과 jitter의 평균 빈도가 함께 약 100 Hz이고
  jitter만 deadline missed가 0보다 커야 한다. 그 횟수는 최대 간격이 15 ms를 넘은 간격 수와
  같은 규모여야 한다.
- 늘린 deadline이 구독자를 끊는다는 주장이 지지되려면, widened에서 15 ms 구독자의 수신이 0이고
  비호환 이벤트 정책이 DEADLINE이어야 한다. 30 ms 구독자는 정상 수신해야 한다.
- 예측과 다르면 그 결과를 그대로 보고하고, 글의 결론을 결과에 맞춘다.

## 한계

- 한 대의 클라우드 VM 위 컨테이너, 1 CPU, 같은 프로세스 안의 통신(loopback/공유 메모리)이다.
  네트워크 너머 전송 지연, 다른 DDS 구현, rmw_zenoh, 실시간 커널은 다루지 않는다.
- 흔들림은 의도적으로 만든 간격 패턴이다. 실제 센서 드라이버의 지터를 재현한 것이 아니다.
- 시뮬레이터와 실물 로봇은 실행하지 않는다. deadline 이벤트는 송수신 여부만 보는 신호이므로
  로봇 정지 같은 안전장치를 대신하지 않는다.

## 시행착오 (시험 실행)

1. 첫 시험 실행에서 세 시나리오의 JSON은 모두 출력됐지만, 종료할 때 프로세스가 SIGSEGV(종료 코드
   139, stderr `terminate called without an active exception`)로 끝나 하네스가 실패로 판정했다.
   원인은 executor가 다른 스레드에서 아직 spin 중인데 rclpy를 내린 것이다. 고친 순서는
   `executor.shutdown()` → 스핀 스레드 `join()` → `rclpy.try_shutdown()`이다.
   이렇게 고친 뒤 두 번째 시험 실행은 종료 코드 0으로 끝났다.
2. 첫 시험 실행의 jitter·widened 시나리오에서는 발행 스레드가 25 ms 대기 뒤 몇 ms 늦게 깨어난
   간격이 있었다. 그래서 15 ms를 넘은 간격과 deadline missed가 예측한 주기 수보다 약간 많았다.
   따라잡기 발행 때문에 다음 간격이 거의 0에 가까운 경우도 있었다. 두 번째 시험 실행에서는 이런
   늦은 깨어남이 보이지 않았다. 1 CPU를 executor 스레드와 나눠 쓰는 환경의 실행마다 다른
   흔들림이므로 코드에서 숨기지 않는다. 정식 5회 결과에서 실행마다 다를 수 있다.
