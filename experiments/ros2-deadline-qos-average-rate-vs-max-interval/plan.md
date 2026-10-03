# 실험 계획: 평균 100 Hz 토픽은 15 ms deadline QoS를 지키는가

## 질문

센서 토픽이 평균 100 Hz(평균 주기 10 ms)로 발행되면 15 ms deadline을 걸어도
마감을 지킨다고 볼 수 있는가? 아니면 판정을 정하는 것은 평균이 아니라 최대 간격인가?
발행자가 deadline을 30 ms로 늘려 통과시키면 15 ms를 요청하던 구독자는 어떻게 되는가?
덧붙여 research.md가 1차 자료로 확정하지 못한 점 하나를 실측한다. 긴 간격 하나가
deadline의 2배를 넘으면 deadline missed가 그 간격에서 몇 번 세지는가?

## research.md 기준 예측값

근거는 research.md의 산술 예제(간격 8,8,8,8,25,8,8,9,9,9 ms / 균일 10 ms, deadline 15 ms,
발행자 deadline 30 ms)다. 여기에 QoS 문서의 deadline 정의("연속 메시지 사이의 예상 최대 시간")와
호환성 표("발행자 x, 구독자 y, y < x → No")를 더한다. 시나리오마다 간격 패턴을 50주기 반복한다.
간격은 500개, 메시지는 501개다. 모든 패턴은 간격 합이 100 ms이므로 계획상 평균은 100 Hz다.

| 시나리오 | 설정 | 예측 |
| --- | --- | --- |
| uniform | 10 ms 균일, 발행자·구독자 deadline 15 ms | 평균 약 100 Hz, 최대 간격 약 10 ms, deadline missed 0회 |
| jitter | 8,8,8,8,25,8,8,9,9,9 반복, deadline 15 ms | 평균 약 100 Hz(uniform과 같음), 최대 간격 약 25 ms. 주기마다 25 ms 간격 1개가 15 ms를 넘는다. Offered·Requested deadline missed는 각각 약 50회(25 < 2×15이므로 긴 간격 하나에 1회) |
| long | 7,7,7,7,37,7,7,7,7,7 반복, deadline 15 ms | 평균 약 100 Hz, 최대 간격 약 37 ms, 15 ms를 넘는 간격 50개. 긴 간격 하나당 miss 횟수는 문서로 확정되지 않았다. 가설은 둘이다. (가) miss 뒤 deadline 창이 다시 시작되면 37 > 2×15이므로 간격당 2회, 합계 약 100회. (나) 메시지가 다시 올 때까지 한 번만 세면 간격당 1회, 합계 약 50회. 어느 쪽인지는 실측으로만 서술한다 |
| widened | jitter 패턴, 발행자 deadline 30 ms, 구독자 A 요청 15 ms, 구독자 B 요청 30 ms | A: 요청 15 < 제공 30이라 비호환. Requested incompatible QoS 이벤트(정책 DEADLINE)가 나고 수신 0개. B: 호환, 501개 수신. 25 < 30이므로 deadline missed 0회. 발행자: Offered incompatible QoS 이벤트(정책 DEADLINE) 발생 |

간격이 deadline과 정확히 같을 때의 판정은 문서로 확인되지 않아 예측하지 않는다.
설계한 간격(7, 8, 9, 10, 25, 37 ms)은 경계값(15 ms, 30 ms, 45 ms)과 겹치지 않게 골랐다.

## 무엇을 어떻게 재는가

- 환경: 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 실행한다.
  rmw는 기본값이고, 실제 rmw 이름은 실행 중에 `get_rmw_implementation_identifier()`로 읽어 출력한다.
- 노드 구성: 한 프로세스 안에서 발행 노드와 구독 노드를 시나리오마다 새로 만든다. 토픽 타입은
  `std_msgs/UInt32`이고 메시지 값은 순번이다. QoS는 RELIABLE, depth 10이며 deadline만 바꾼다.
  구독 콜백과 QoS 이벤트 콜백은 별도 스레드의 SingleThreadedExecutor가 처리한다.
- 발행: 메인 스레드는 간격 패턴으로 계산한 절대 목표 시각(`time.monotonic_ns`)까지 잠든 뒤
  `publish()`한다. 늦게 깨어나 다음 목표 시각이 이미 지났으면 곧바로 발행한다(따라잡기).
  그래서 평균 주기는 계획대로 유지되고, 실제 간격의 흔들림은 측정값에 그대로 남는다.
- 발행 간격(`pub.intervals`): `publish()` 직후 monotonic 시각의 차이.
- 수신 간격(`subs[].intervals`): 구독 콜백이 불린 시각의 차이. `ros2 topic hz`와 같은 식으로
  계산한다(mean, rate = 1/mean, min, max, 모표준편차). 다만 시계는 ROS clock이 아니라 monotonic이다.
  이 값은 콜백 시점 기준이라 rmw 계층의 deadline 판정 시점과 같지 않다.
  `over_deadline`은 deadline을 넘은 간격 수다.
- deadline missed 이벤트(`offered_missed`, `requested_missed`): `PublisherEventCallbacks(deadline=…)`와
  `SubscriptionEventCallbacks(deadline=…)`가 받은 `total_count_change`를 콜백 시각과 함께 기록한다.
  - `during_run`: 첫 발행부터 마지막 발행 사이에 받은 이벤트의 합. 판정에는 이 값을 쓴다.
  - `after_last_publish`: 마지막 발행 뒤 0.3초 관찰 구간의 합. 메시지가 끊겼으니 계속 나는 것이
    정상이므로 판정에 쓰지 않는다. `before_first_publish`도 따로 센다.
  - `per_over_gap_hist`: 이벤트 콜백 시각이 발행 i와 i+1 사이면 간격 i에서 난 miss로 배정한다.
    그다음 deadline을 넘은 발행 간격마다 miss 수를 세어 분포 {miss 수: 간격 수}로 출력한다.
    구독자도 같은 프로세스·같은 monotonic 시계의 발행 시각으로 배정하고, 기준은 그 구독자의 요청
    deadline이다. `in_gaps_within_deadline`은 deadline 이하 간격에 배정된 miss 수다. 이 값이 0이 아니면
    콜백 전달이 늦었거나 수신 측 흔들림이 섞였다는 뜻이다. 비호환으로 연결되지 않은 구독자
    (widened의 A)는 발행 간격만 배정되고 이벤트는 없다.
- 비호환: `incompatible_qos` 콜백의 `total_count`(`incompatible_total`)와 `last_policy_kind`
  (`incompatible_policy`)를 기록한다.
- 수신 개수와 손실: `received`, `lost`(발행 수 − 받은 고유 순번 수).
- 연결 대기: 시나리오마다 호환 구독자 수만큼 매칭되고 예상한 비호환 이벤트가 올 때까지
  최대 5초 기다린다. 결과는 `matched`, `discovery_s`로 남는다.
- 출력: 시나리오마다 압축 JSON 한 줄, 마지막에 총 소요 시간 한 줄. `planned` 블록은 입력 패턴으로
  계산한 계획값이고, `pub`·`subs` 블록이 실행 중 측정값이다. 한 번 실행에 약 25초가 걸린다
  (컨테이너 기동 제외).

## 판정 기준

- 평균만으로 판정할 수 없다: uniform과 jitter의 측정 평균 빈도가 둘 다 약 100 Hz이고, jitter만
  deadline missed `during_run`이 0보다 크며, 그 횟수가 15 ms를 넘은 발행 간격 수와 같은 규모여야 한다.
- 긴 간격 하나의 miss 횟수: long의 `per_over_gap_hist`에서 가장 많은 값을 그대로 보고한다.
  가설 (가)·(나) 중 어느 쪽인지는 이 값으로만 말한다. 이번 환경(Fast DDS 기본 rmw, Jazzy)에서
  관측한 사실로만 쓰고, 다른 rmw·배포판의 규칙으로 일반화하지 않는다.
- 늘린 deadline이 구독자를 끊는다: widened에서 15 ms 구독자의 수신이 0이고 비호환 정책이
  DEADLINE이어야 한다. 30 ms 구독자는 정상 수신해야 한다.
- 예측과 다르면 결과를 그대로 보고하고 글의 결론을 결과에 맞춘다.

## 한계

- 클라우드 VM 한 대 위의 컨테이너, 1 CPU, 같은 프로세스 안의 통신이다. 네트워크 너머 전송 지연,
  다른 DDS 구현, rmw_zenoh, 실시간 커널(PREEMPT_RT)은 다루지 않는다.
- 1 CPU를 발행 스레드와 executor 스레드가 나눠 쓴다. 실행마다 늦은 깨어남이 섞여 최대 간격과
  miss 수가 조금씩 달라질 수 있다. 코드에서 이런 흔들림을 걸러 내지 않는다.
- 흔들림은 의도적으로 만든 간격 패턴이다. 실제 센서 드라이버의 지터를 재현한 것이 아니다.
- 시뮬레이터와 실물 로봇은 쓰지 않는다. deadline 이벤트는 송수신 간격을 감시하는 신호일 뿐이며
  비상 정지 같은 안전장치를 대신하지 않는다. 실물 하드웨어를 움직이는 단계가 없으므로 정지 절차가
  필요한 동작도 없다.

## 시행착오 (시험 실행)

1. 하네스는 `plan.md`가 없으면 실행을 거부한다. 그래서 첫 시험 실행 전에 제목만 있는 임시 plan.md를
   두었고, 시험 실행 뒤 이 문서로 바꿨다.
2. 시험 실행 전 코드를 다시 읽다가 버그 하나를 고쳤다. 처음 작성한 코드는 구독자 miss를 간격에
   배정할 때 구독자 요청 deadline이 아니라 발행자 deadline으로 "deadline을 넘은 간격"을 골랐다.
   widened의 30 ms 구독자처럼 둘이 다른 경우에 분포가 틀려지므로 구독자 자신의 deadline을 쓰도록 고쳤다.
3. 시험 실행은 한 번 했고 종료 코드 0으로 끝났다. 네 시나리오와 요약 줄이 모두 출력됐고 stderr는
   비어 있었다. 실패해서 고친 점은 없다. 시험 실행 값은 이 문서에 옮기지 않는다. 본문의 실측 숫자는
   하네스의 정식 실행 `results.json`만 근거로 한다.
