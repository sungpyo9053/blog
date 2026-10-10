# 실험 계획: rclpy Rate.sleep()의 멈춤과 실효 주기 (ROS 2 Jazzy)

## 질문

Jazzy rclpy의 `Rate.sleep()`은 타이머 콜백이 세우는 `threading.Event`를 기다린다(research.md, timer.py L118-L177).
그렇다면 실제 `ros:jazzy-ros-base` 컨테이너에서

1. executor가 돌지 않거나, 유일한 executor 스레드가 콜백 안에서 `sleep()`에 묶이면 `sleep()`이 정말 돌아오지 않는가?
2. executor가 별도 스레드에서 돌 때, 루프 작업 시간 w와 목표 주기 T(8 Hz → 0.125 s)의 관계에 따라 실효 루프 주기는
   어떻게 되는가? 특히 w > T이면 "다음 타이머 눈금까지 기다림"이 아니라 "w 간격으로 돎"이 되는가?
3. MultiThreadedExecutor는 스레드 수가 2일 때만 콜백 안 `rate.sleep()`을 살리는가?

## research.md 기준 예측값 (실행 전에 적은 값)

| ID(출력 case) | 구성 | 예측 |
| --- | --- | --- |
| A (`A_no_spin_main_loop`) | spin 없음, 메인 while + 8 Hz Rate | 본문 1회 실행 후 첫 `sleep()`에서 멈춤, 워치독 전 반환 0회 |
| B (`B_spin_thread_work_0.0625`) | spin 데몬 스레드 + 8 Hz, 작업 0.0625 s, 5 s 창 | 평균 간격 ≈ 0.125 s, 대기 ≈ 0.0625 s, 루프 시작 ≈ 40회 |
| 경계 (`Bound_spin_thread_work_0.125`) | 같은 구성, 작업 = 주기 0.125 s, 3 s 창 | 대기 ≈ 0 s, 간격 ≈ 0.125 s (산술 예제의 경계 케이스) |
| D (`D_spin_thread_work_0.15`) | 같은 구성, 작업 0.15 s, 3 s 창 | 간격 ≈ 0.15 s (0.25 s로 올림되지 않음), 대기 ≈ 0 |
| C (`C_spin_thread_work_0.25`) | 같은 구성, 작업 0.25 s, 3 s 창 | 간격 ≈ 0.25 s, 실효 ≈ 4 Hz, 대기 ≈ 0 |
| E (`E_single_threaded_callback`) | SingleThreadedExecutor, 노드 기본 그룹 타이머 콜백 안 `rate.sleep()` | 워치독 전 반환 0회 |
| F1 (`F1_multi_threaded_1_thread_callback`) | MultiThreadedExecutor(num_threads=1), 같은 콜백 | 단일 스레드와 같음: 반환 0회 |
| F2 (`F2_multi_threaded_2_threads_callback`) | MultiThreadedExecutor(num_threads=2), 같은 콜백 | 반환함(Rate 타이머가 Reentrant `_rate_group`이라 다른 스레드가 실행), 간격 ≈ 0.125 s |

Experiment 단계에서 덧붙인 산술 예측(같은 가정): 창 길이 / 실효 주기 = 루프 시작 수이므로
경계 3/0.125 = 24회, D 3/0.15 = 20회, C 3/0.25 = 12회. 경계 케이스는 작업이 정확히 T라도 루프 오버헤드만큼
간격이 T보다 아주 조금 길어져(늘 작업 구간 안에 타이머 발화가 있어 `sleep()`이 즉시 반환) 실효 주파수가 8 Hz보다
아주 조금 낮을 것으로 예측한다.

## 무엇을 어떻게 재는가

- 환경: 하네스가 `ros:jazzy-ros-base`(1 CPU 제한, 1 GiB, 네트워크 없음)에서 실행. 기본 RMW, `use_sim_time` 끔(기본 ROSClock = 벽시계 속도).
  스크립트 첫 줄(`env`)에 `os.sched_getaffinity(0)` CPU 수와 `os.cpu_count()`를 실행 중에 기록한다
  (MultiThreadedExecutor 기본 스레드 수 결정에 쓰이는 값, executors.py L951-L983).
- 시간은 전부 `time.monotonic()`으로 실행 중에 잰다. 결과 숫자를 코드에 적어 두지 않는다.
- A: 메인 스레드에서 `node.create_rate(8.0)` 후 `while` 루프. 2.0 s 뒤 워치독 스레드가 `node.destroy_rate(rate)`로 Rate 이벤트를
  세워 멈춘 `sleep()`을 깨운다(Rate.destroy → `_event.set`). 기록: 실행된 루프 본문 수, 워치독 전 `sleep()` 반환 수, 마지막 `sleep()`이 막혀 있던 시간.
- B/경계/D/C: `SingleThreadedExecutor.spin()`을 데몬 스레드에서 돌리고 메인 루프에서 `time.sleep(w)`(작업 대역) → `rate.sleep()`.
  창(5 s 또는 3 s) 안에서 시작한 루프 수, 루프 본문 시작 시각 사이 간격(첫 간격은 루프 시작과 타이머 눈금의 위상 차를 포함하므로
  `first_interval_s`로 따로 두고 나머지로 평균·중앙값·최소·최대·모표준편차·실효 Hz 계산; rclpy test_rate.py가 첫 sleep을 빼는 것과 같은 이유),
  `rate.sleep()` 안에서 보낸 시간(ms, 첫 번째 따로 + 나머지 평균·최대).
- E/F1/F2: 노드 기본(상호 배타) 그룹의 0.05 s 트리거 타이머 콜백이 한 번만 들어와 `rate.sleep()`을 최대 8회 시도한다.
  메인 스레드는 2.0 s까지 콜백 종료를 기다리고, 끝나지 않으면 `destroy_rate`로 깨운다. 기록: 워치독 전 반환 수,
  워치독 없이 끝났는지, 반환이 있으면 콜백 진입 시각 기준 간격 통계(첫 간격은 위상 차 포함).
- 안전장치: 55 s 하드 데드라인(`os._exit(3)`)으로 한 번 실행이 60 s를 넘지 않게 한다. 시험 실행 기준 전체 약 21~22 s.
- 판정 기준: "멈춤" = 워치독 전 반환 0회. "주기 유지" = 첫 간격 제외 평균 간격이 목표 T에 가까움.
  "작업 시간 지배" = 평균 간격이 w에 가깝고 `sleep()` 대기가 ms 이하.

## 한계

- 작업은 `time.sleep(w)`로 흉내 냈다. GIL을 놓는 대기라 executor 스레드가 자유롭게 돈다. GIL을 잡는 CPU 계산 작업이면
  executor 콜백 지연과 지터가 달라질 수 있다(측정하지 않음).
- 작업 시간은 일정하다. 가변 작업 시간, `use_sim_time` + /clock, 다른 배포판(Humble·Rolling)은 측정하지 않았다.
- 컨테이너는 CPU 제한이 있는 하네스 환경이며, 실물 로봇·시뮬레이터 실행이 아니다. 실시간 마감 보장을 뜻하지 않는다.

## 시행착오 (시험 실행 `--try`)

1. 첫 시험 실행이 케이스 B에서 종료 코드 1로 실패했다. 케이스 이름(`B_spin_thread_work_0.0625`)을 그대로 노드 이름으로 썼는데
   점(`.`)이 들어 있어 `InvalidNodeNameException`(노드 이름은 영숫자와 `_`만 허용)이 났다. 노드 이름에서 `.`을 `_`로 바꿔 고쳤다.
   A는 이 실행에서도 정상 측정됐다.
2. 두 번째 시험 실행은 성공했지만, 작업 ≥ 주기 케이스의 `sleep()` 대기가 0에 너무 가까워 초 단위 소수 넷째 자리 반올림에서
   0으로만 보였다. 소수 여섯째 자리로 바꾸자 지수 표기(`e-05`)로 출력돼 본문 대조가 어려워서, 대기 시간 필드를 밀리초
   소수 셋째 자리(`*_sleep_wait_ms`)로 바꿨다. 세 번째 시험 실행이 성공(종료 코드 0)했다.
3. 시험 실행의 `env` 줄에서 affinity CPU 수가 하네스의 1 CPU 제한(`--cpus`, CFS 쿼터)과 같지 않았다. 그래서 MultiThreadedExecutor는
   기본 스레드 수에 기대지 않고 F1/F2에서 `num_threads`를 명시했다. F1은 rclpy의 "MultiThreadedExecutor is used with a single thread"
   UserWarning을 stderr에 남긴다(의도한 구성).
