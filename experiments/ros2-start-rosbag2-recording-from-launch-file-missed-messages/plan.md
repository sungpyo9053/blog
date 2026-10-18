# 실험 계획: launch 하나로 로봇 노드와 `ros2 bag record`를 띄우면 bag에서 무엇이 얼마나 빠지나

## 질문

launch 파일 하나로 로봇 노드와 `ros2 bag record`(ExecuteProcess)를 함께 시작할 때,

1. 녹화기를 지연 없이 같은 launch에 넣으면 앞부분 메시지가 빠지는가?
2. `TimerAction(period=2.0)`으로 녹화기만 늦추면 빠지는 개수가 "주기 × 지연"과 맞는가?
3. `--use-sim-time`이면 첫 `/clock` 전에는 구독 자체가 없어서, 그동안 발행된 메시지가 bag에 하나도 없는가?
4. 한 번만 보내는 `/tf_static`은 녹화기가 늦게 떠도 남는가? QoS override가 durability를 volatile로 덮으면 사라지는가?

## research.md 기준 예측값

research.md `## 5. 검산된 예제`의 설명용 가정값을 그대로 예측으로 쓴다(실측 아님).

| 사례 | research.md 식 | 예측 |
| --- | --- | --- |
| A 지연 없음 | 30 × 0 (사례 7의 경계) | 하한 0. 실제로는 CLI 기동·탐색 시간이 더해질 수 있다고 research.md가 경고 |
| B 2초 timer, 카메라 30 Hz | 30 × 2.0 | 60 이상 |
| B 2초 timer, IMU 200 Hz | 200 × 2.0 | 400 이상 |
| B 합계 | (30 + 200) × 2.0 | 460 이상 |
| C sim time, 첫 `/clock`이 녹화기 시작 3초 뒤 | 30 × 3 | 90개가 쓰이지 않음(bag 안 0개). 소스상 첫 `/clock` 전에는 `/cam` 구독 자체가 없음 |
| B `/tf_static`(transient local 녹화) | 1 − 1 | 빠지는 수 0(bag에 1개) |
| D override가 volatile로 덮음 | 1 − 0 | 빠지는 수 1(bag에 0개) |

research.md는 1~4번 개수를 "녹화기가 timer 만료 직후 즉시 구독한다는 가정의 하한"이라고 했다. 실험은 그 위에 실제로 더해지는 시간(CLI 기동 + 노드 생성 + 토픽 탐색)을 잰다.

## 환경

- 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 실행한다. 기본 RMW(rmw_fastrtps_cpp).
- 사용 패키지: launch, rclpy, std_msgs, rosgraph_msgs, geometry_msgs, tf2_ros, rosbag2(`ros2 bag record`, rosbag2_py). 모두 ros-base 이미지에 들어 있다.
- 시뮬레이터·실물 로봇은 쓰지 않는다. `/clock`은 실험 노드가 직접 발행하는 가짜 시뮬레이션 시계다.

## 무엇을 어떻게 재나

사례마다 `/tmp`에 Python launch 파일을 새로 만들고 `ros2 launch`로 실행한다. 사례별로 `ROS_DOMAIN_ID`를 달리해 서로 섞이지 않게 한다.

- launch 구성: `ExecuteProcess(python3 robot.py)`(로봇 노드 역할) + `ExecuteProcess(ros2 bag record -o ... --topics ...)`. 사례 B·D는 녹화기를 `TimerAction(period=...)` 안에 넣는다.
- robot.py: `/cam`(UInt32, 30 Hz), `/imu`(UInt32, 200 Hz, A·B만)를 0부터 1씩 늘어나는 일련번호로 발행한다. CPU가 밀려도 "주기 × 경과 시간"만큼 보내도록 밀린 메시지를 이어서 보낸다. 시작 직후 `tf2_ros.StaticTransformBroadcaster`로 `/tf_static` 1개를 보낸다(A·B·D).
- 녹화기 구독 시점: robot.py가 발행할 때마다 자기 발행자의 `get_subscription_count()`를 보고, 0에서 1 이상이 된 시각과 그때까지 보낸 개수(`published_before_recorder_subscribed`)를 기록한다. 시각은 프로세스 간 공통인 `time.monotonic()`이다.
- sim time(C): robot.py가 `/clock` 발행자를 미리 만들어 두고, 녹화기 노드가 `/clock`을 구독한 순간(= 녹화기 노드가 살아 있음)을 잡는다. 그로부터 3.0초 뒤 첫 `/clock`(sim time 100.0초부터, 100 Hz)을 보낸다. 녹화기의 `/cam` 구독이 첫 `/clock`보다 먼저 생겼는지, 기다리는 3초 동안 보낸 `/cam` 중 bag에 들어간 개수를 센다. launch 출력에서 소스의 로그 문자열 "waiting for /clock before starting recording"과 "Sim time /clock found, starting recording"이 실제로 찍히는지도 본다.
- override(D): `/tf_static`에 `durability: volatile`을 주는 YAML을 `--qos-profile-overrides-path`로 넘긴다.
- 종료: robot.py가 모든 녹화 대상 토픽의 구독을 확인하고 1.5초 더 발행한 뒤 스스로 끝나면, launch 프로세스 그룹에 SIGINT(Ctrl+C와 같은 신호)를 보낸다. 녹화기 종료 코드와 bag이 정상으로 열리는지도 기록한다.
- bag 판정: rosbag2_py로 bag을 읽어 토픽별 개수, bag 안의 첫 일련번호, 첫 번호 이후 빠진 번호(구멍) 수를 센다. `missing_from_bag = 발행 총수 − bag 개수`.
- 출력: 사례별 JSON 한 줄 + 요약 JSON 한 줄. 숫자는 모두 실행 중 측정값이며 코드에 결과 숫자를 적지 않는다. 사례 설정값(30 Hz, 200 Hz, 2.0초, 1.0초, 3.0초, 100.0초)은 실험 조건이다.

## 판정 기준

- 질문 2: `missing_from_bag`이 `rate_x_timer_delay`(예측 하한) 이상이고, `published_before_recorder_subscribed`와 거의 같으면(차이 1 안팎) "빠지는 수 = 구독 전 발행 수" 모델이 맞다. 예측 하한보다 큰 만큼이 timer 밖에서 더해진 기동·탐색 지연이다.
- 질문 3: `cam_subscription_existed_before_first_clock=false`이고 `of_those_in_bag=0`이면 "첫 `/clock` 전 구독 없음"이 확인된다.
- 질문 4: B의 `/tf_static` in_bag이 1, D가 0이면 durability가 결과를 가른다는 경계가 확인된다.
- 한 번이라도 bag을 못 열면(`bag_error`) 그 실행은 실패로 본다(종료 코드 1).

## 한계

- 1 CPU 컨테이너, 같은 호스트 안 프로세스, 작은 메시지(UInt32)다. 카메라 이미지 같은 큰 메시지, 여러 호스트, 실제 시뮬레이터의 `/clock` 시점은 재지 않는다.
- 녹화기 구독 시점은 발행자 쪽 매칭 시각이다. 구독자 쪽 매칭과 수 ms 어긋날 수 있어 경계 메시지 1개 정도의 차이가 날 수 있다.
- 사례 A의 결과는 "로봇 노드와 녹화기 중 누가 먼저 준비되나"라는 경쟁 결과다. 로봇 노드가 더 무겁거나 녹화기 토픽이 많으면 달라질 수 있다.
- 실물 로봇은 쓰지 않으므로 하드웨어 안전 조건은 해당 없다.

## 시행착오

- 첫 시험 실행에서 실패는 없었다. 네 사례 모두 bag이 mcap으로 정상 생성·판독됐고 60초 안에 끝났다.
- 시험 실행에서 발견한 점: launch 프로세스 그룹에 SIGINT를 보내면 launch는 정상 종료(0)하지만 `ros2 bag record` 프로세스는 launch 로그에 "process has died ... exit code 2"로 찍힌다. 그래도 bag은 열린다. 이것을 결과로 남기려고 `recorder_exit_code_after_sigint` 필드를 추가했다.
- 사례 B 해석에 timer 밖의 기동 시간을 분리해야 해서 `recorder_subscribed_s_after_launch_start`(launch 시작 기준) 필드를 추가했다. robot.py 기준 시각만으로는 로봇 노드 자체의 기동 시간이 섞이기 때문이다.
- 쓰지 않던 sim time 전용 `tail_s` 재설정 코드를 지웠다(값이 기본값과 같아 동작 변화 없음).
- 수정 후 두 번째 시험 실행도 성공했다. 사례 A는 첫 시험에서는 빠진 메시지가 없었지만 두 번째에는 `/cam`·`/imu`가 몇 개씩 빠졌다. 사례 A는 실행마다 달라지는 경쟁 결과이므로, 글에서는 정식 5회 결과의 범위로만 말해야 한다. B·C·D는 두 시험에서 예측과 같은 방향이었다.
