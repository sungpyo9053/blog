# 실험 계획: `/clock`이 앞으로·멈춤·뒤로 움직일 때 ROS 2 Jazzy의 시계·타이머·TF 버퍼는 실제로 어떻게 반응하는가

## 질문

글(`research.md`)은 `dt = t_now - t_previous`의 산술만 Python 3.12.3으로 검산했고 "ROS 2 노드, rosbag2,
시뮬레이터와 실물 로봇은 실행하지 않았다", "jump callback 호출 횟수, 실제 timer 스케줄링 … 을 확인한 증거는
아니다"라고 적었다. 타이머 재예약과 TF 버퍼 비우기는 "소스로만 확인했고 우리 컨테이너에서 실행하지는 않았다"고
했다. 이 실험은 그 부분을 ROS 2 Jazzy 노드로 실제로 실행한다. 핵심 질문은 하나다.

> `use_sim_time=true` 노드에 `/clock`을 정상 진행 → 2배속 → 정지 → 12초에서 9초로 역점프 → 앞으로 점프시키면,
> 노드 시계의 `dt`, 시간 점프 콜백, ROS 시간 타이머, SteadyTime 타이머, tf2 버퍼가 글이 말한 대로 반응하는가?

세부 확인 항목:

1. 첫 `/clock`이 오기 전 노드 시계는 0인가?
2. `/clock` 정상 진행(0.1 s 단계)·2배속(현실 0.1 s당 0.2 s)에서 ROS `dt`는 현실 경과와 무관하게 `/clock` 진행량을 따르는가?
3. `/clock`을 12.0초로 고정한 채 현실 5초 이상이 지나면 ROS 경과는 0이고, 5초 timeout은 ROS 시계로는 만료되지 않고
   SteadyTime으로는 만료되는가? (조건식 `now - last >= 5 s`와 `create_timer(5.0, …)` 두 방식 모두)
4. 12.0 → 9.0 역점프에서 `dt`는 -3 s이고, `x_next = x + v × dt`(x=10 m, v=2 m/s)는 4 m가 되는가?
5. `create_jump_callback`(뒤쪽 임계값 -1 ns, 앞쪽 2 s)의 pre/post 콜백은 역점프에서 각각 한 번 호출되고,
   post가 받은 `delta`는 -3 s인가? pre/post 안에서 읽은 시계는 점프 전/후 시각인가? 정지 구간(같은 값 반복)에서는 호출되지 않는가?
6. (글의 핵심 주장) 주기 1 s ROS 시간 타이머가 12초에 마지막으로 호출된 뒤 시간이 9초로 돌아가면,
   다음 콜백은 13초가 아니라 10초에 오는가? 역점프 직후 `time_until_next_call()`은 1 s인가?
7. 앞으로 점프(11.0 → 15.5)해 예정 시각(12.0)이 이미 지났으면 타이머가 바로 깨어나는가? 몇 번 호출되며 그 다음 예정은 언제인가?
8. tf2 버퍼는 음의 점프에서 비워지는가? 글은 C++ `tf2_ros::Buffer`(Rolling 소스)를 근거로 들었다.
   C++ 버퍼는 이미지에 든 `tf2_ros`의 `tf2_echo` 실행 파일(같은 `use_sim_time`)로, Python `tf2_ros.Buffer`는
   `TransformListener`로 같은 `/tf`를 받아 따로 확인한다.
9. ROSTime 값과 SteadyTime 값을 빼면 `TypeError`가 나는가? (참고 링크의 rclpy Jazzy 주장)

## 글이 주장한 예측값

실행 전 예측이다. 실측이 아니다.

| 항목 | 글의 주장 | 예측 |
|---|---|---|
| 첫 `/clock` 전 노드 시계 | 0은 초기화되지 않은 상태 | 0 ns, `ros_time_is_active=true` |
| 정상 진행 dt | 약 +0.1 s | 매 단계 ROS dt 0.1 s, 현실 dt는 0.1 s 근처(흔들림 있음) |
| 2배속 dt | +0.2 s | 매 단계 ROS dt 0.2 s, ROS/현실 비 약 2 |
| 정지 중 ROS 경과 | 0 s | 0 s (현실 5초 이상 경과) |
| 정지 중 `now - last >= 5 s` | ROS로는 만료 안 됨, Steady로는 만료 | ROS false, Steady true |
| 정지 중 5 s 타이머 | 같은 분리 | ROS 시간 타이머 0회, SteadyTime 타이머 1회 |
| 정지 중 jump 콜백 | (글에 없음) | 0회 |
| 역점프 dt | -3 s | -3 s |
| 위치 누적 `10 + 2 × dt` | 4 m | 4 m |
| jump 콜백(역점프) | 갱신 전·후 호출 | pre 1회(시계 12.0), post 1회(시계 9.0, delta -3 s, `ROS_TIME_NO_CHANGE`) |
| 1 s 타이머, 12초 호출 뒤 9초로 역점프 | 다음 콜백 10초(13초 아님) | 역점프 뒤 `time_until_next_call` 1 s(점프 직후 즉시 값과 50 ms 뒤 값을 따로 잰다), 9→11 진행 중 콜백 10.0·11.0초 |
| 11.0 → 15.5 앞쪽 점프 | 예정이 지났으면 바로 깨움 | 15.5초에 콜백 1회, 다음 예정 16.0초(남은 0.5 s), jump 콜백 pre/post 1회씩(delta 4.5 s) |
| C++ `tf2_ros::Buffer`(tf2_echo) | 음의 점프에서 버퍼를 비움 | 역점프 직후 "jump back" 경고, 그 뒤 `map`→`base_link` 조회 실패 |
| Python `tf2_ros.Buffer` | (글은 C++만 근거) | 모름. 실행해서 본다 |
| ROSTime − SteadyTime | `TypeError` | `TypeError` |

## 측정 방법

- 환경: 하네스의 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB). `rclpy`, `rosgraph_msgs`, `geometry_msgs`,
  `tf2_ros`(Python 모듈과 C++ `tf2_echo` 실행 파일)만 쓴다. 패키지 버전은 `package.xml`, rmw 이름은 실행 중에 읽는다.
- 노드:
  - `sim_clock`(use_sim_time 끔): `/clock`(`rosgraph_msgs/Clock`)과 `/tf`(`map → base_link`, stamp = 그 순간의 `/clock`)를 보낸다.
    `/tf`는 정상·2배속 구간(10.0~12.0초)에서만 보낸다.
  - `app`(use_sim_time 켬): 노드 시계를 읽는 쪽. 1 s ROS 시간 타이머, jump 콜백, Python `Buffer` + `TransformListener`.
  - 별도 프로세스 `tf2_echo map base_link --ros-args -p use_sim_time:=true`(C++ 버퍼, 기본 1 Hz 출력). stdout/stderr 줄을 받은 순간의
    단계 이름과 함께 기록한다.
  - 두 노드는 백그라운드 스레드의 `SingleThreadedExecutor`로 돈다. `/clock` 발행과 판독은 메인 스레드가 한다.
- `/clock` 한 단계: 값을 발행하고 `app` 시계가 그 값이 될 때까지(2 ms 간격 확인, 50 ms마다 재발행, 상한 2 s) 기다린다.
  시각은 부동소수점 오차를 피하려고 정수 ns로 만든다.
- 진행(모든 판독은 실행 중에 잰다):
  0. `app` 생성 직후 시계 값. tf2_echo와 Python listener가 `/tf`·`/clock`을 구독할 때까지 기다린다(상한 20 s).
  1. 정상: 10.0 → 11.0초, 0.1 s 단계, 현실 0.1 s 간격. 단계마다 ROS dt와 Steady dt.
  2. 2배속: 11.0 → 12.0초, 0.2 s 단계, 현실 0.1 s 간격.
  3. 정지: 12.0초를 현실 0.1 s마다 다시 보내며 5.5 s 유지. 시작 시 5 s ROS 시간 타이머와 5 s SteadyTime 타이머를 만들고,
     끝에서 두 시계의 경과·조건식 판정·각 타이머 호출 수를 읽은 뒤 두 타이머를 없앤다.
  4. 역점프: 9.0초 발행. dt, 위치 누적식, 시계가 9.0초를 읽은 즉시와 50 ms 뒤의 `time_until_next_call`, jump 콜백 기록,
     Python 버퍼의 프레임 목록과 11.0초·최신 조회(점프 전에도 같은 조회).
  5. 9.0 → 11.0초, 0.1 s 단계, 현실 0.05 s 간격. 1 s 타이머 콜백이 온 ROS 시각.
  6. 앞쪽 점프: 15.5초 발행 후 0.5 s 대기. 콜백 수, 발행에서 콜백까지의 Steady 지연, `time_until_next_call`.
  7. tf2_echo를 SIGINT로 끝내고 출력 줄을 단계별로 요약한다(`At time` 줄 수와 마지막 변환 시각, `Failure at` 줄 수,
     점프 경고, 실패 문구 앞부분). 숫자만 있는 행렬 줄은 버린다.
  8. ROSTime − SteadyTime 뺄셈의 예외 이름.
- 스크립트의 숫자(10.0/11.0/12.0/9.0/15.5초, 0.1·0.2 s 단계, 현실 간격, 5 s timeout, 5.5 s 유지, 1 s 주기, x=10 m, v=2 m/s,
  임계값 -1 ns·2 s, 대기 상한)는 입력과 제한값이다. 결과 숫자는 미리 적지 않는다. 출력은 `kind` 필드가 있는 JSON 줄이다.
  하네스가 stdout 끝 8000자만 남기므로 출력은 요약해서 짧게 낸다.

## 판정 기준

- 위 표의 예측과 실측 줄을 그대로 대조한다. ROS 시각·dt는 `/clock`이 정한 값이라 정확히 비교하고,
  Steady 경과·지연은 실행마다 달라지므로 "현실 시간이 흘렀는가 / 바로 깨어났는가" 수준으로만 읽는다.
- 예측과 다르면 결과를 그대로 보고하고 글의 설명을 결과에 맞춘다. `wait_timeouts`가 0이 아니면 그 사실을 먼저 본다.

## 한계

- `/clock`은 스크립트가 직접 보낸 값이다. rosbag2 재생, 시뮬레이터, 실물 로봇·하드웨어 드라이버는 없다.
- rclpy 타이머와 Python·C++(tf2_echo) TF 버퍼만 본다. rclcpp 노드 타이머, `ros2_control`은 재지 않았다.
- 한 컨테이너 안 두 프로세스, 기본 rmw(Fast DDS)다. 여러 호스트, 실제 네트워크 지연, 부하 상황은 재지 않았다.
- Jazzy 한 배포판이다. Humble·Kilted·Rolling 동작으로 일반화하지 않는다.

## 시행착오

- 하네스(`--try`)는 plan.md가 없으면 실행을 거부하므로 이 계획을 시험 실행 전에 썼다.
- 설계 단계: `/clock` 구독(rclpy TimeSource)은 BEST_EFFORT·깊이 1이라 빠르게 보내면 값이 덮이거나 빠질 수 있다.
  그래서 단계마다 `app` 시계가 그 값이 될 때까지 기다리고 필요하면 재발행한다(rosbag2 정지 중 같은 값 반복 발행과 같은 모양).
- 설계 단계: 첫 `/clock`(0 → 10초)도 앞쪽 점프로 잡힐 수 있어, jump 콜백을 첫 `/clock` 전에 등록하고 단계 이름을 붙여 기록한다.
- 설계 단계: tf2_echo의 `std::cout`은 파이프로 연결하면 블록 버퍼링될 수 있어 `stdbuf -oL`로 줄 버퍼링하고,
  rcutils 로그도 `RCUTILS_LOGGING_BUFFERED_STREAM=1`로 줄 단위로 내보낸다.
- 시험 실행 1회차(`--try`): 종료 코드 0, `wait_timeouts` 0. 두 가지를 고쳤다.
  (1) Jazzy의 `tf2_echo`는 세 번째 위치 인수(출력 주기)를 받지 않고 사용법을 출력한 뒤 바로 끝났다(종료 코드 5).
  그래서 C++ 버퍼 측정이 비었고, 구독자 대기가 상한 20 s를 다 썼다. 주기 인수를 빼 기본 1 Hz로 돌리고,
  tf2_echo가 먼저 끝나면 구독자 대기 조건에서 빼도록 했다. 1 Hz로도 정지(5.5 s)와 역점프 뒤 구간에 줄이 남는다.
  (2) 역점프 직후 읽은 `time_until_next_call`이 재예약 전 값(원래 예정 13초 기준)으로 나왔는데, 이어진 9→11 진행에서
  콜백은 10.0·11.0초에 왔다. 메인 스레드가 시계 값 9.0을 본 순간과 executor 스레드에서 타이머의 post-jump 처리가
  끝나는 순간 사이에 틈이 있는 것으로 보였다. 측정을 숨기지 않고 "즉시" 값과 "50 ms 뒤" 값을 둘 다 내도록 바꿨다.
  같은 실행의 stderr에 Python 쪽 `tf2_buffer` 로거가 "Detected jump back in time. Clearing tf buffer."를 남겼고
  점프 뒤 Python 버퍼 조회가 실패했다. stderr는 하네스가 끝부분만 남기므로 stdout에도 프레임 목록을 넣었다.
- 시험 실행 2회차: 종료 코드 0, `wait_timeouts` 0, 컨테이너 기동 포함 한 번 실행이 60초보다 훨씬 짧았다. tf2_echo가
  정상 동작해 역점프 단계에서 C++ 버퍼의 "Detected jump back in time. Clearing TF buffer." 경고와 그 뒤 `map`–`base_link`
  조회 실패 줄이 잡혔다. Python 버퍼도 점프 뒤 프레임 목록이 비었다. 50 ms 뒤 `time_until_next_call`은 예측과 같았다.
- 시험 실행 3회차: tf2_echo 요약에서 변환 행렬의 숫자 줄을 버리고 `Failure at` 줄 수를 세도록만 바꿨다. 측정 항목은 그대로이며
  종료 코드 0, `wait_timeouts` 0, stdout은 8000자 한도 안이었다.
- 판독 주의점(수치는 옮기지 않음): 첫 `/clock`(0 → 10초)도 앞쪽 2 s 임계값을 넘는 점프로 pre/post가 호출된다.
  post의 `clock_change`는 세 점프 모두 `ROS_TIME_NO_CHANGE`였다(시간원 전환이 아니라 같은 ROS 시간 안의 이동).
  역점프 "즉시" 값은 스레드 경합에 따라 실행마다 달라질 수 있으므로 본문에서는 재예약이 끝난 뒤 값과 실제 콜백 시각을 근거로 쓴다.
- 시험 실행의 수치는 이 문서에 옮기지 않는다. 본문의 실측 숫자는 하네스 정식 실행의 `results.json`만 근거로 한다.
