# 실험 계획: 레이저 스탬프와 tf 스탬프가 다른 시계에서 오면 "레이저 − tf" 뺄셈과 드롭 경로는 어떻게 나오는가

## 질문

`Message Filter dropping message: frame 'laser' at time ...` 로그가 계속 찍힐 때, 레이저 `header.stamp`에서
tf 최신 스탬프를 빼면 다음을 가를 수 있는가?

1. 같은 시계(둘 다 /clock, 둘 다 시스템 시계)면 차이는 작다(스캔·tf 주기 수준). 숫자가 커도 정상이다.
2. 한쪽만 시스템 시계면 차이는 수십억 초이고, 부호로 어느 쪽이 시스템 시계인지 알 수 있다.
3. 부호에 따라 tf2가 내놓는 실패 종류(과거/미래 외삽)와 메시지 필터의 드롭 경로(즉시 드롭 / 대기열 넘침)가 달라진다.
4. 레이저 스탬프가 0(레이저 노드가 /clock을 아직 못 받음)이면 드롭되지 않고 최신 tf와 짝지어진다.
5. 정적 변환만 있는 경로(target = base_link, base_link→laser static)는 시계가 섞여도 드롭되지 않는다.
6. 드롭 로그 줄 앞 대괄호 시각은 sim time 노드가 찍어도 시스템 시각이다.

## research.md 기준 예측값

research.md의 산술 예제(tf 최신 125.25 s, 시스템 시각 1790000000 s는 설명용 가정값)와 geometry2 jazzy
소스 읽기에서 나온 예측이다. 실험의 sim 시각은 120 s에서 시작하므로 절대값은 예제와 다르고, 규모와 부호를 대조한다.

| 경우 | 예측 차이(레이저 − tf) | 예측 tf2 응답 | 예측 드롭 경로 |
| --- | --- | --- | --- |
| same_sim (둘 다 /clock) | +0.25 s 같은 작은 값(스캔·tf 주기 수준) | 잠깐 미래 외삽 후 성공 | 대기 후 통과, 드롭 없음 |
| same_system (둘 다 시스템 시계) | 작은 값. 스탬프 자체는 약 1.79×10⁹ | 위와 같음 | 드롭 없음 |
| laser_system_tf_sim | +1789999874.75 s 규모(약 +1.79×10⁹) | 미래 외삽(extrapolation into the future) | 즉시 드롭 없음, 대기열이 차면 queue full 드롭 |
| laser_sim_tf_system | −1789999874.5 s 규모(약 −1.79×10⁹) | 과거 외삽(extrapolation into the past) | 요청 + 10 s < tf 최신 → 즉시 드롭(OutTheBack, 'earlier than all the data') |
| laser_no_clock_yet (스탬프 0) | −125.25 s 규모(−sim 시각) | 시각 0 = 최신 공통 시각으로 조회, 성공 | 드롭 없음. 조회된 변환의 스탬프 = 그 순간 tf 최신 |
| 위 경우들의 static-only target | — | 항상 성공 | 드롭 없음 |
| 로그 대괄호 시각 | 대괄호 − at time ≈ 시스템 시각 − sim 시각(수십억 초) | — | 대괄호 ≈ 같은 순간의 time.time() |

## 무엇을 어떻게 재는가

- 환경: 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 `experiment.py`를 실행한다.
  rclpy, tf2_ros, sensor_msgs, geometry_msgs, tf2_msgs, rosgraph_msgs만 쓴다. 한 번 실행은 약 15초다.
- 노드 구성(한 프로세스, SingleThreadedExecutor):
  - `clock_src`(시스템 시계): 10 ms 타이머로 /clock(120 s + 경과 시간)을 발행한다. 같은 타이머가 tf(50 Hz)와
    스캔(20 Hz) 발행 시점을 구동한다. 스탬프는 각 발행 노드 자신의 `get_clock().now()`다.
    (sim time 노드의 타이머는 /clock이 없으면 멈추므로 발행 시점만 시스템 시계로 구동한다.)
  - 경우마다 새 `tf_node_<경우>`(odom→base_link 동적 + base_link→laser 정적)와 `laser_node_<경우>`(LaserScan)를
    `use_sim_time` 조합만 바꿔 만든다. 프레임 이름에 경우 이름을 접두어로 붙여 경우 사이 간섭을 막는다.
  - `laser_no_clock_yet`의 레이저 노드는 `use_sim_time=True`이고 `-r /clock:=/clock_not_published`로 /clock
    구독을 다른 이름으로 돌린다. "레이저 노드가 아직 /clock을 받지 못한 상태"를 재현한다.
  - `consumer`(use_sim_time=True, 시뮬레이션 속 RViz·slam_toolbox 위치): `tf2_ros.Buffer`(캐시 10 s) +
    `TransformListener`, 그리고 /tf 원본 구독으로 동적 변환의 최신 스탬프를 기록한다.
- 측정(경우마다 준비 후 2.0 s 창, 시스템 시계 기준):
  - 스캔 수, 첫 스캔 스탬프, 그때의 tf 최신 스탬프, 스캔마다 "레이저 스탬프 − 동적 tf 최신 스탬프"의 중앙값·최솟값·최댓값.
  - 측정 직전 레이저 노드와 tf 노드의 `now()`.
  - 드롭 판정기: `tf2_ros::MessageFilter`(C++)의 분기를 Python으로 단순화해 옮긴 것이다. 변환 가능 여부와 오류
    문자열은 실제 tf2 Buffer(`can_transform_core`, `get_latest_common_time`)의 답이다.
    ① 성공 → 통과 ② 실패이고 요청 시각 + 10 s < 경로 최신 공통 시각 → 즉시 드롭(OutTheBack 경로)
    ③ 그 밖 → 대기열(크기 5)에 넣고 tf가 올 때마다 다시 묻는다. 넘치면 가장 오래된 것을 드롭(QueueFull 경로).
    결과로 통과·대기 후 통과·즉시 드롭·대기열 넘침 드롭·창 종료 시 대기 수와 첫 tf2 오류 문자열을 낸다.
    판정기는 target이 odom(동적 경로)인 것과 base_link(정적 경로만)인 것 두 개를 동시에 돌린다.
  - 스탬프 0 경우: 첫 0 스탬프 스캔으로 `lookup_transform_core(odom, laser, 0)`을 호출해 돌려받은 변환의 스탬프와
    그 순간 tf 최신 스탬프를 기록한다.
  - 로그 대괄호: 자식 프로세스(ROS_DOMAIN_ID=77로 분리)에서 use_sim_time 노드가 /clock을 받은 뒤 드롭 로그와 같은
    형식의 INFO 한 줄을 찍는다. 부모가 그 줄의 대괄호 시각과 `at time` 값을 파싱하고, 로그 직전·직후의
    `time.time()`과 비교한다.
- 출력: 실행 중 계산한 값만 JSON 줄로 출력한다(`log_bracket`, 경우별 `case` 5줄, `meta`).
- 한계: 판정기는 C++ MessageFilter 자체가 아니라 그 분기를 옮긴 단순화다(tolerance, buffer_timeout 유한값,
  다중 스레드 콜백은 재현하지 않음). RViz·slam_toolbox·Gazebo·실물 라이다는 쓰지 않았다. 모두 한 컴퓨터의 한
  프로세스이므로 서로 다른 컴퓨터 사이의 NTP 어긋남은 재현하지 않는다. 시스템 시각의 절대값은 실행 시점에 따라 달라진다.

## 시행착오

- 첫 시험 실행: 스크립트는 수정 없이 끝까지 실행됐고, 다섯 경우 모두 예측한 방향의 결과가 나왔다.
- 고친 점 1개: 같은 시계 경우에도 첫 tf2 오류 문자열에 "extrapolation into the future"가 기록됐다. 스캔 스탬프가
  그 순간의 tf 최신 스탬프보다 몇 ms 앞서 잠깐 대기한 뒤 통과했기 때문이다. 그런데 출력에는 "통과" 합계만 있어서
  "곧바로 통과"와 "잠깐 대기 후 통과"를 구분할 수 없었다. 그래서 판정기에 `passed_after_wait` 카운터를 추가하고
  다시 시험 실행했다. 두 번째 시험 실행도 정상 종료했다.
- 같은 시계 경우의 첫 오류 문자열은 드롭이 아니라 짧은 대기를 뜻한다. 이를 드롭 근거로 해석하지 않는다.
