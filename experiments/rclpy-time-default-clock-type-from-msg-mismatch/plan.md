# 실험 계획: rclpy Time의 생성 경로별 clock_type과 섞었을 때 TypeError가 나는 연산

## 질문

ROS 2 Jazzy rclpy에서 `rclpy.time.Time()`, `Time(seconds=…)`, `Time.from_msg()`, `Clock().now()`,
`Node.get_clock().now()`가 실제로 어떤 clock_type과 나노초 값을 갖는가?
이 값들을 서로 빼거나 비교하면 어느 연산에서 `TypeError`가 나고, 어느 연산은 통과하는가?
노드 타이머 콜백에서 이 예외가 나면 `spin_once` 밖으로 빠져나오는가(rosbridge rosapi 사고 패턴)?

## research.md 기준 예측값 (소스 읽기에서 나온 예측이며 실측이 아니다)

| 객체 | 코드 | 예측 clock_type | 예측 nanoseconds |
|---|---|---|---|
| A | `Time()` | SYSTEM_TIME | 0 |
| B | `Time(seconds=1.5)` | SYSTEM_TIME | 1500000000 |
| B2 | `Time(seconds=2, nanoseconds=500000000)` | SYSTEM_TIME | 2500000000 (두 인자가 더해짐) |
| C | `Time.from_msg(B.to_msg())` | ROS_TIME | 1500000000 |
| D | `node.get_clock().now()` (use_sim_time=False) | ROS_TIME | 시스템 시각 기반 값 |
| E | `sim.get_clock().now()` (use_sim_time=True, /clock 수신 전) | ROS_TIME | 0 |
| F | `Clock().now()` | SYSTEM_TIME | 시스템 시각 |
| G | `Time(seconds=1.5, clock_type=node.get_clock().clock_type)` | ROS_TIME | 1500000000 |

메시지 분해 예측: `B.to_msg()`는 sec=1, nanosec=500000000이고, `B2.to_msg()`는 sec=2, nanosec=500000000이다.

연산 예측:
- `B == C`, `B != C`, `B < C`, `B <= C`, `B > C`, `B >= C`는 `TypeError: Can't compare times with different clock types`.
  `B - C`는 `TypeError: Can't subtract times with different clock types`. 반면 `B.nanoseconds == C.nanoseconds`는 True다.
- `D - A`, `A < D`, `A == E`는 TypeError다. A와 E는 둘 다 0 ns여도 예외가 나므로 값과 무관하다.
  `A.nanoseconds == E.nanoseconds`는 True다.
- `C == G`는 True, `D - C`는 Duration(예외 없음), `D - E`는 Duration이다. clock_type이 같으면 시간원이 달라도 통과한다.
- `F - D`는 TypeError다(Clock() 기본 SYSTEM_TIME vs 노드 ROS_TIME).
- `B + Duration(seconds=1)`은 SYSTEM_TIME을 유지하고, `C - Duration(seconds=1)`은 ROS_TIME을 유지한다(예외 없음).
- `A == None`은 False(예외 없음)다. `A < None`은 Python 일반 TypeError이며 문구가 rclpy 문구와 다르다.
- `Time(1, 500000000)`(위치 인자)는 TypeError다(키워드 전용 인자).
- `Time.from_msg(msg, clock_type=ClockType.SYSTEM_TIME) == B`는 True다(clock_type을 명시하면 왕복 비교 가능).
- use_sim_time=True 노드가 `/clock`을 받은 뒤에도 clock_type은 ROS_TIME이고 값만 /clock 값으로 바뀐다.
  그 값에서 `Time()`을 빼면 TypeError, `Time.from_msg(...)`(ROS_TIME)를 빼면 Duration이다.
- 타이머 콜백에서 `now() - Time()`을 하면 첫 콜백에서 TypeError가 나고 `spin_once` 밖으로 전파된다.
  기준 시각을 `now()`로 잡으면 콜백이 예외 없이 반복된다.

## 무엇을 어떻게 재는가

- 환경: 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 단일 프로세스로 실행한다.
  rclpy 버전은 스크립트가 `importlib.metadata`(실패 시 package.xml)로 읽어 출력한다. 하네스도 dpkg 버전을 따로 기록한다.
- 노드 두 개: `clock_type_probe`(use_sim_time 기본값)와 `clock_type_probe_sim`
  (`parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)]`). 각 노드의 use_sim_time 파라미터 값을 실제로 읽어 출력한다.
- 객체 A~G를 위 코드로 만들고 `clock_type.name`, `nanoseconds`, `repr()`를 출력한다. `to_msg()`의 sec/nanosec도 출력한다.
  노드 시계의 클래스 이름(ROSClock 여부), clock_type, `ros_time_is_active`를 함께 출력한다.
- 연산 22개를 하나씩 try/except로 실행한다. 예외가 나면 예외 클래스 이름과 메시지 문자열을 그대로 기록한다.
  예외가 없으면 결과의 타입, clock_type, 나노초를 기록한다.
- /clock 단계: 같은 프로세스에 `/clock` 발행 노드를 만든다. 입력값 sec=42, nanosec=250000000인
  `rosgraph_msgs/Clock`을 SingleThreadedExecutor로 최대 15초 동안 반복 발행·spin한다. sim 노드의 now()가 0이 아니게
  되면 멈춘다. 발행 횟수, 수신 여부, 대기 시간, 수신 후 now()를 기록하고, 그 값에서 A·C를 빼 본다.
- 타이머 단계(rosbridge 패턴 최소 재현): 주기 0.05초 타이머 콜백에서 `now() - last_used`를 계산한다.
  (1) `last_used = Time()`, (2) `last_used = node.get_clock().now()` 두 변형을 각각 콜백 5회 또는 5초까지 spin_once한다.
  기록 항목은 콜백 진입 횟수, 정상 완료 횟수, 최소 경과 나노초, spin_once 밖으로 빠져나온 예외(클래스·메시지)다.
- 모든 측정값은 실행 중에 관측한 값을 JSON 한 줄씩(`kind` 필드로 구분) stdout에 출력한다.
  스크립트에 결과 숫자를 미리 적지 않는다. 스크립트에 있는 숫자(1.5, 2, 500000000, 42, 250000000, 0.05, 5, 15)는 입력값과 제한값이다.

## 해석 경계

- 이번 실험은 순수 소프트웨어 실측이다. 시뮬레이터나 실물 하드웨어는 쓰지 않았다. /clock은 같은 프로세스의 노드가 직접 발행한 값이고 Gazebo 출력이 아니다.
- D·F·타이머 경과 시간 같은 시스템 시각 값은 실행마다 달라진다. 비교 대상은 clock_type, 예외 여부, 예외 문구, 고정 입력에서 나온 나노초 값이다.
- 측정 범위는 rclpy(Python)뿐이다. rclcpp 동작은 측정하지 않았다.
- `A < None`의 메시지는 CPython이 만든 문구이며 rclpy 문구가 아니다.

## 시행착오

- 하네스(`--try`)는 plan.md가 없으면 실행을 거부한다. 그래서 첫 시험 실행 전에 임시 plan.md를 두었고, 이 문서로 교체했다.
- 그 밖에는 없음. 첫 시험 실행 1회가 종료 코드 0으로 끝났다. 모든 단계(객체 생성, 연산 22개, /clock 수신, 타이머 두 변형)가
  예외 없이 JSON 줄을 출력했고 스크립트는 수정하지 않았다. 시험 실행의 수치는 여기에 옮기지 않는다. 실측값의 근거는 하네스의 results.json뿐이다.
