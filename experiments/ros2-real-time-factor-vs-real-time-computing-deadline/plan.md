# 실험 계획: RTF 1.0과 마감 준수를 한 번의 ROS 2 Jazzy 실행에서 따로 재기

## 질문

시뮬레이터의 실시간 계수(real time factor, RTF)가 1.0이면, 같은 시뮬레이션 시간으로 도는 내 제어 루프가
매 주기 마감(deadline)을 지킨다고 믿어도 될까?

이 실험은 같은 실행에서 두 가지를 따로 잰다.

- RTF: 시뮬레이션 경과 ÷ 벽시계(wall-clock) 경과
- 마감 준수: 100 Hz 타이머(주기 = 마감 = 10 ms) 콜백의 간격, 예정 격자 대비 시작 지연, 응답 시간, 건너뛴 주기 수

## 환경과 조건

- 하네스: `ros:jazzy-ros-base` 컨테이너, 네트워크 없음, 1 CPU·1 GiB, 기본 RMW(rmw_fastrtps_cpp)
- 사용 패키지: rclpy, rosgraph_msgs(`/clock`). 외부 설치는 없다.
- 호스트 커널은 PREEMPT_RT가 아닌 일반 커널이다. 실행 중 `os.uname()`으로 커널 문자열을 기록한다.
- 한 번 실행은 측정 구간 5개 × 5 s와 프로세스 시작 시간을 합쳐 60 s 안에 끝난다.

## 구간(phase) 설계

| 구간 | 타이머 시계 | /clock | 지연 주입 |
| --- | --- | --- | --- |
| `wall_baseline` | steady(단조 시계) | 없음 | 없음 |
| `wall_injected` | steady | 없음 | 50번째 콜백마다 22 ms `time.sleep` (25, 75, 125…번째) |
| `sim_rtf1` | ROS 시간(`use_sim_time=True`) | 별도 프로세스, 목표 RTF 1.0 | 없음 |
| `sim_rtf1_injected` | ROS 시간 | 별도 프로세스, 목표 RTF 1.0 | 22 ms 주입 |
| `sim_rtf05` | ROS 시간 | 별도 프로세스, 목표 RTF 0.5 | 없음 |

- 22 ms 주입은 설계상 넣은 대조군이다. 자연 발생 장애가 아니다.
- `/clock` 발행자는 같은 스크립트를 `--clock <rtf>` 인자로 다시 실행한 **별도 OS 프로세스**다. 시뮬레이터처럼
  1 ms씩 시뮬레이션 시간을 올리고, 목표 RTF에 맞춰 벽시계 간격을 조절한다. 뒤처지면 따라잡기 위해 몰아서
  발행하지 않고 잃은 시간을 그대로 둔다(그래서 부하가 있으면 RTF가 실제로 떨어진다).
- `/clock` 발행자는 약 100 ms마다 (단조 시계, 시뮬레이션 시각) 표본을 남긴다. Gazebo Sim이 통계 메시지를
  초당 10건으로 제한하는 것과 비슷한 해상도로 RTF를 본다.
- 제어 노드는 단일 스레드 실행기(SingleThreadedExecutor)에서 돈다. 지연 주입은 제어 노드에만 들어가고
  `/clock` 프로세스는 멈추지 않는다.

## 무엇을 어떻게 재는가

콜백마다 시작·종료 시각을 단조 시계(`time.monotonic_ns`)와 타이머 시계(steady 또는 노드의 ROS 시간)로 기록한다.
값은 모두 실행 중에 계산해 구간마다 JSON 한 줄로 출력한다. 첫 콜백은 기준점으로만 쓰고 통계에서 뺀다.

- `callbacks`, `grid_periods_spanned`, `skipped_periods`: rcl `rcl_timer_call`의 고정 격자 규칙(다음 예정 =
  직전 예정 + 주기, 이미 지났으면 놓친 주기만큼 건너뜀)을 스크립트 안에서 그대로 따라가며 건너뛴 주기를 센다.
  격자의 기준은 두 번째 콜백의 시작 시각이다(그 콜백의 지연을 0으로 가정).
- `interval_wall_ms`(mean/min/p99/max), `interval_timer_clock_ms`(mean/max), `max_wall_interval_at_s`
- `start_lateness_ms`: 예정 격자 대비 시작 지연
- `response_ms_max`, `deadline_misses`: 응답 시간 = 시작 지연(타이머 시계) + 콜백 실행 시간(벽시계).
  응답 시간이 마감 10 ms를 넘으면 마감 초과 1회로 센다.
- `wall_intervals_over_period`(간격 > 10 ms), `wall_intervals_over_period_plus_jitter`(간격 > 10 ms의 105 %,
  공식 실시간 튜토리얼이 가정한 허용 지터 5 %), `max_wall_interval_minus_deadline_ms`,
  `wall_intervals_over_budget`(설명용 산술 예제의 벽시계 예산 25 ms 초과 횟수)
- `exec_timer_clock_ms_max_injected`, `exec_wall_ms_max_injected`: 주입한 콜백의 실행 시간을 두 시계로 각각 잰 값
- sim 구간만: `rtf_seen_by_control_node`(제어 노드가 본 시뮬레이션 경과 ÷ 벽시계 경과),
  `rtf_clock_publisher`(발행자 표본 기준), `rtf_clock_publisher_100ms_min/max`(약 100 ms 창별 RTF 최소·최대),
  `first_clock_wait_s`
- `cgroup_cpu_delta`: 컨테이너 cgroup v2 `cpu.stat`의 구간 전후 차이(nr_throttled, throttled_usec, usage_usec).
  CPU 제한에 걸려 멈춘 시간이 있었는지 구분하는 보조 지표다.

## research.md 기준 예측값

research.md의 rcl 타이머 소스 해석(고정 격자 + 놓친 주기 건너뛰기)과 산술 검산 예제(case 8: 10 ÷ 0.5 = 20 ms)에서
나온 예측이다. 측정값이 아니다.

- `wall_baseline`: 평균 간격 ≈ 10 ms. 최대 간격·마감 초과는 비실시간 컨테이너에 따라 달라지므로 예측하지 않는다.
- `wall_injected`:
  - 평균 간격은 주기 근처에 머문다. 5 s 동안 약 498 격자 중 주입 10회가 각각 한 주기를 건너뛰면 콜백 간격 수가
    약 488이 되어 평균 ≈ 4980 ÷ 488 ≈ 10.2 ms.
  - 최대 간격 ≈ 22 ms(주입 지연), 그 다음 간격은 ≈ 8 ms로 짧아진다.
  - 건너뛴 주기 ≈ 주입 1회당 1회 → 약 10회.
  - 마감 초과 ≈ 주입 1회당 2회 → 약 20회. 근거: rclpy 실행기는 콜백 실행 전에 `rcl_timer_call`을 부르므로
    주입된 콜백(응답 ≈ 22 ms)이 1회, 바로 다음 격자의 콜백이 약 12 ms 늦게 시작해 1회 더 초과한다(실험 에이전트가
    research.md의 rcl 규칙에서 추론한 값).
- `sim_rtf1`: RTF ≈ 1.0, 벽시계 평균 간격 ≈ 10 ms.
- `sim_rtf1_injected`: `/clock` 발행자 쪽 RTF ≈ 1.0을 유지하면서, 제어 콜백은 `wall_injected`와 비슷하게
  최대 간격 ≈ 22 ms, 마감 초과 ≈ 20회, 건너뛴 주기 ≈ 10회. 이 구간이 제목 질문에 대한 직접 측정이다.
- `sim_rtf05`: RTF ≈ 0.5, 시뮬레이션 시간 간격 평균 ≈ 10 ms, 벽시계 간격 평균 ≈ 20 ms. 시뮬레이션 시간 기준
  마감 초과 0회. 벽시계 간격은 모두 10 ms를 넘지만 25 ms 예산은 넘지 않을 것으로 예측한다.

## 해석 한계

- 1 CPU 컨테이너, 비RT 커널, Python(rclpy), 기본 RMW, 단일 스레드 실행기 조건의 결과다. C++·RT 커널·실물 로봇
  성능으로 일반화하지 않는다.
- sim 구간의 응답 시간은 시작 지연(시뮬레이션 시간)과 실행 시간(벽시계)을 더한 근사다. RTF 0.5 구간처럼 두 시계
  속도가 다르면 실행 시간이 짧을 때만 의미가 있다(이 구간에는 주입이 없다).
- `/clock` 해상도는 1 ms이므로 sim 구간의 타이머 시계 값은 1 ms 단위로 양자화된다.
- 5회 실행의 편차는 하네스 `results.json`에서 확인한다. 한 번의 시험 실행 값으로 결론을 내리지 않는다.

## 시행착오 (시험 실행 3회)

1. **디스커버리 범위 지정이 적용되지 않음**: 처음에는 네트워크가 없으니 `ROS_AUTOMATIC_DISCOVERY_RANGE`를
   `LOCALHOST`로 `setdefault`했다. 첫 시험 실행의 환경 줄을 보니 이미지가 이미 `SUBNET`을 설정해 두어 지정이
   적용되지 않았다. 그 상태로도 별도 프로세스의 `/clock`을 1 s 안에 받았으므로, 덮어쓰지 않고 이미지 기본값을
   그대로 쓰고 값만 기록하도록 고쳤다.
2. **"간격 > 10 ms" 개수가 지터에 휩쓸림**: 첫 시험 실행에서 지연을 넣지 않은 구간에서도 간격의 약 절반이
   10 ms를 아주 조금 넘어 이 개수가 마감 판정에 쓸모없었다. 공식 실시간 튜토리얼이 가정한 허용 지터 5 %를
   더한 기준(10.5 ms 초과) 개수를 함께 출력하도록 추가했다. 엄격한 개수도 "간격만으로 판정하면 지터를 어떻게
   다룰지 먼저 정해야 한다"는 근거로 남겼다.
3. **주입이 없는 기준선에서 자연 지연 발생**: 두 번째 시험 실행에서는 `wall_baseline`에서도 수십 ms짜리 간격,
   건너뛴 주기와 마감 초과가 생겼다. 실행 초반 영향인지 CPU 제한 때문인지 구분하려고 최대 간격이 나온 시점
   (`max_wall_interval_at_s`)과 cgroup `cpu.stat` 차이(`cgroup_cpu_delta`)를 추가했다. 세 번째 시험 실행에서는
   기준선이 깨끗했지만 `sim_rtf1`에서 큰 간격이 생겼고, 그때는 `/clock` 발행자 쪽 RTF도 1.0보다 낮아졌다.
   즉 비실시간 환경의 자연 지연은 실행마다 위치가 다르다. 이 변동은 숨기지 않고 5회 결과로 보고한다.
4. **시험 실행에서 처음 알게 된 점(예측에 없던 관찰)**: 단일 스레드 실행기에서 콜백이 22 ms 동안 막혀 있으면
   그동안 `/clock` 구독도 처리되지 않아, 제어 노드의 ROS 시간으로 잰 주입 콜백 실행 시간은 0에 가깝게 보였다
   (`exec_timer_clock_ms_max_injected`). 벽시계로 잰 값(`exec_wall_ms_max_injected`)과 나란히 기록한다.
   sim 시간으로만 실행 시간을 재면 늦은 콜백을 놓칠 수 있다는 근거다.
5. `/clock`을 1 kHz로 발행하는 sim 구간은 Python 두 프로세스가 CPU를 상당히 쓴다. 측정값을 그대로 쓰되,
   CPU 사용량은 `cgroup_cpu_delta.usage_usec`로 함께 남긴다.
