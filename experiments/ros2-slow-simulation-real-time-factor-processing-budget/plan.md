# 실험 계획: RTF를 낮추면 느린 노드가 16 Hz 프레임을 몇 개 처리하나 (ROS 2 Jazzy)

## 질문

시뮬레이터가 노드를 기다리지 않고 목표 RTF로만 sim 시간을 진행할 때, 콜백 한 번에 벽시계
0.25 s를 쓰는 keep last 구독 노드는 16 Hz(sim 주기 T = 0.0625 s) 카메라 프레임을 몇 개
처리하고 몇 개를 놓치나? research.md의 식 `RTF 상한 = T ÷ p`, `처리 비율 ≈ min(1, T ÷ (p × r))`과
이산 사건 모델이 실제 rclpy·Fast DDS 경로에서도 맞는가? depth를 10으로 올리면 손실 대신
지연이 커지는가? 처리 시간이 가끔 0.375 s로 튀면 평소값 기준 상한(0.25)에서 손실이 나고,
여유를 둔 RTF 0.2에서는 사라지는가?

## research.md 기준 예측값 (실행 전에 계산)

식(research.md `## 원리`)과, research.md의 이산 사건 모델을 그대로 옮긴 `model_processed()`로
이 실험의 프레임 수(조건마다 sim 2 s = 32프레임)를 넣어 실행 전에 계산했다.
같은 함수로 960프레임을 넣으면 research.md 표의 241 / 481 / 960 / 250 / 245를 그대로 재현한다.

| 조건 | 목표 RTF | depth | 처리 | 식의 처리 비율 | 모델 처리 수 / 32 |
| --- | --- | --- | --- | --- | --- |
| A | 1 | 1 | sleep 0.25 s | 0.25 | 9 |
| B | 0.5 | 1 | sleep 0.25 s | 0.5 | 17 |
| C | 0.25 (평소값 상한) | 1 | sleep 0.25 s | 1 | 32 |
| D | 1 | 10 | sleep 0.25 s | — | 18 (짧은 실행이라 큐 10칸이 끝에 비워지며 더 많이 처리됨, 대신 지연 약 `depth × p` ≈ 2.5 s 예상) |
| E | 0.25 | 1 | 프레임 번호 k % 4 == 3이면 0.375 s, 나머지 0.25 s | — | 29 (손실 3) |
| F | 0.2 (여유 20%) | 1 | E와 같음 | — | 32 (손실 0) |
| G | 0.5 | 1 | busy-wait 0.25 s (CPU 점유) | 0.5 | 17 (CPU 경쟁이 없다면) |

- RTF 상한: 평소값 기준 `0.0625 ÷ 0.25 = 0.25`, 최악값 기준 `0.0625 ÷ 0.375 ≈ 0.1667`.
- 벽시계 비용: sim 2 s를 RTF 0.25로 돌리면 8 s, 0.2로 돌리면 10 s (`L ÷ r`).
- 주의: research.md의 "네 번에 한 번 튀는" 모델(960프레임에서 854 처리)은 튀는 프레임의 위치 정의가
  이 실험과 다를 수 있다. 이 실험은 "프레임 번호 k % 4 == 3"으로 정의했고, 같은 정의로 960프레임을
  계산하면 841이 나온다. 결론(평소값 상한 RTF 0.25에서는 손실, 0.2에서는 손실 0)은 같다.

## 무엇을 어떻게 재는가

구성 (`ros:jazzy-ros-base`, 네트워크 없음, 1 CPU, rclpy + rosgraph_msgs + std_msgs만 사용):

- **시뮬레이터 역할 프로세스** (`experiment.py --sim`, 자식 프로세스): sim 스텝 `T ÷ 16`
  (0.00390625 s)마다 `/clock`을 발행하고, 16스텝(= sim 0.0625 s)마다 `std_msgs/Header`를
  `/camera_<조건>`에 발행한다. `stamp`는 sim 시각, `frame_id`는 `프레임번호:발행 시점 CLOCK_MONOTONIC ns`.
  벽시계 주기는 `스텝 ÷ 목표 RTF`이고, 늦으면 다음 갱신 시각을 `now + period`로 재설정한다
  (research.md가 읽은 gz-sim8 `SimulationRunner` 루프와 같은 방식). **노드의 처리 완료를 기다리지 않는다.**
  조건 사이에는 `(depth + 1) × 최대 처리 시간 + 0.3 s` 동안 발행을 멈춰(일시정지) 남은 큐를 비운다.
- **처리 노드** (부모 프로세스): 조건마다 별도 토픽 구독(RELIABLE, KEEP_LAST depth 1 또는 10)을
  만들고 SingleThreadedExecutor로 돈다. 콜백에서 `time.sleep(p)` 또는 busy-wait로 벽시계 p초를 쓴다.
  시뮬레이터를 다른 프로세스로 분리해, 느린 콜백이 `/clock` 발행을 멈추게 하는 함정(사실상 lockstep)과
  GIL 경쟁을 피했다. busy-wait 조건(G)만 일부러 1 CPU를 두 프로세스가 나눠 쓰게 한다.

측정값 (조건마다 JSON 한 줄, 마지막에 summary 한 줄):

- `published`, `processed`, `dropped`, `processed_ratio`, 처리된/놓친 프레임 번호(`processed_ids`, `missed_ids`)
- `achieved_rtf`: 시뮬레이터가 실제 달성한 sim 경과 ÷ 벽시계 경과, `sim_late_steps`: 주기를 놓친 스텝 수
- `callback_p_mean/max`: 콜백 안에서 실제로 쓴 벽시계 시간
- `frame_age_wall_mean/max`: 프레임 발행 → 콜백 시작까지 벽시계(두 프로세스가 같은 CLOCK_MONOTONIC 사용)
- `result_latency_wall_max`: 발행 → 처리 완료 벽시계, `result_latency_sim_max`: 이를 달성 RTF로 sim 시간에 환산
- 비교용 계산값: `formula_ratio`, `rtf_bound_normal`, `rtf_bound_worst`, `model_processed`, `model_ids`
  (식과 이산 사건 모델로 실행 중 계산. 결과 숫자를 코드에 미리 적지 않는다)

판정: 각 조건의 `processed`가 `model_processed`와 같거나 ±1~2 안이면 식·모델이 ROS 2 Jazzy rclpy
경로에서 맞는다고 본다. C(경계값)는 타이밍 지터로 소수 손실이 날 수 있다. D는 `frame_age_wall_max`가
A보다 크게 늘면 "depth는 손실 대신 지연"을 지지한다. G는 `achieved_rtf`가 목표보다 낮아지거나
`sim_late_steps`가 늘면 CPU 공유가 RTF 달성에 영향을 준다는 신호다.

범위와 한계: Gazebo·물리 엔진·카메라 플러그인을 띄우지 않는다. "시뮬레이터가 목표 RTF로 sim 시간을
진행하고 기다리지 않는다"는 동작을 Python 루프로 흉내 낸 것이므로, 결과는 ROS 2 시간·QoS·executor
계층에서 식이 맞는지까지만 말한다. 조건당 32프레임의 짧은 실행이라 첫·마지막 프레임 경계 효과가
비율에 섞인다(예: A의 식 비율 0.25 대비 처리 수 9/32). 실물 하드웨어 실험이 아니다.

## 시행착오

- 첫 시험 실행(`--try`)은 종료 코드 0으로 끝났고 실패는 없었다. 전체 약 48 s(컨테이너 기동 포함)로 60 s 안이다.
- 고친 점: 시뮬레이터가 보고하는 sim 경과가 공칭 2 s가 아니라 첫 프레임부터 마지막 프레임 발행까지의
  실제 진행량(31 × T + 한 스텝)이라 `sim_seconds`라는 이름이 공칭 길이로 오해될 수 있었다.
  `sim_elapsed_seconds`(실제 경과)와 `sim_length_nominal`(설정 길이)로 나눠 두고 다시 시험했으며,
  재시험도 종료 코드 0이었다.
- 설계 단계 판단: 조건을 sim 3 s(48프레임)로 잡으면 research.md 예측처럼 합계가 길어져 busy-wait 조건과
  튀는 처리 시간 조건을 넣을 수 없어서, 조건당 sim 2 s로 줄였다. 최악값 기준 상한(약 0.1667)은 벽시계
  12 s가 들어 시간 한도 때문에 넣지 않고, 20% 여유인 0.2로 대신 확인한다.
- 모델 함수 점검: 컨테이너 밖 Python 3.12로 `model_processed()`에 960프레임을 넣어 research.md 표의
  처리 수와 같은지 먼저 확인했다(튀는 처리 시간 행만 위 '주의'처럼 정의 차이로 다름).
