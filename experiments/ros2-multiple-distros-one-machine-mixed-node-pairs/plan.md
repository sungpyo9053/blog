# 실험 계획: Jazzy 하나만 있는 컴퓨터에서 셸 source 상태·RMW 지정·같은 묶음 통신을 직접 재기

## 질문

글의 질문은 "한 컴퓨터에 ROS 2 배포판을 여러 개 두면 터미널·.bashrc는 어떻게 나누고, 섞인 노드는
메시지를 주고받아도 되는가"다. 실험 환경(`ros:jazzy-ros-base`, 네트워크 없음, 1 CPU·1 GiB)에는
Jazzy와 Fast DDS만 있다. 그래서 이 실험은 그 질문 중 **이 환경에서 실제로 잴 수 있는 세 부분**만 확인한다.

1. 셸 상태: source를 안 한 셸, Jazzy를 한 번·두 번 source한 셸, `.bashrc`에 **설치되지 않은 배포판**
   (`/opt/ros/kilted/setup.bash`) 줄이 있는 셸, Jazzy 뒤에 그 줄이 이어지는 셸에서 `ROS_DISTRO`와
   경로 변수는 어떻게 되는가? 두 번 source하면 경로가 중복되는가?
2. 설치되지 않은 RMW를 `RMW_IMPLEMENTATION`으로 가리킨 셸(예: `.bashrc`에 다른 미들웨어를 적어 둔
   터미널)에서 rclpy 노드를 만들면 어느 단계에서 어떻게 실패하는가?
3. 보장 범위 안의 기준선: 같은 배포판(Jazzy)·같은 RMW(rmw_fastrtps_cpp)의 발행자 1개와 구독자 1개를
   별도 프로세스로 띄우면 보낸 메시지 중 몇 개를 받는가? 각 노드는 어떤 `ROS_DISTRO`·RMW로 실행됐는가?

## research.md 기준 예측값

- 셸 상태(Experiment Agent 참고 1번): source 안 함 → ROS 변수 없음. Jazzy 1회·2회 → `ROS_DISTRO=jazzy`.
  2회 source에서 `AMENT_PREFIX_PATH`·`PATH` 항목이 중복되는지는 research.md가 "모름, 측정 대상"으로 남겼다.
- 없는 배포판 source: research.md에 예측 없음. 이 실험에서 추가한 항목이다. 계획 단계 가정은
  "source가 0이 아닌 종료 상태로 실패하고, 앞서 Jazzy를 source했다면 `ROS_DISTRO`는 jazzy로 남는다"였다.
- 설치되지 않은 RMW(참고 2번): 실패. 실패 단계(import, init, 노드 생성)는 예측하지 않았다.
- 같은 묶음 기준선(참고 3번): 대부분 또는 전부 수신.
- 설치 목록: `/opt/ros`에는 jazzy만, RMW는 rmw_fastrtps_cpp 계열만 있다(research.md의 이미지 점검).

## 무엇을 어떻게 재는가

`experiment.py` 하나가 아래 순서로 실행되고 측정마다 JSON 한 줄을 출력한다. 결과 숫자는 코드에 없고
모두 실행 중에 읽거나 센 값이다.

1. `inventory`: `/opt/ros` 아래 디렉터리 이름, ament 색인의 `rmw_typesupport` 리소스 이름,
   `/opt/ros/*/lib/librmw_<구현>_cpp.so` 파일 이름, ament 색인 패키지 수, Python 버전.
2. `shell_state` 5개: `env -i HOME=/tmp PATH=<기본 경로> bash --noprofile --norc -c`로 하네스가 미리
   source한 환경을 비운 새 bash를 띄운다. 상태마다 source를 차례로 실행하고 각 source의 종료 상태를
   기록한 뒤 `env -0`으로 환경 전체를 읽는다. 기록 항목은 `ROS_DISTRO`, `ROS_VERSION`,
   `RMW_IMPLEMENTATION`, `AMENT_PREFIX_PATH` 항목 수와 고유 항목 수, `PATH`·`PYTHONPATH`·
   `LD_LIBRARY_PATH`에서 `/opt/ros`로 시작하는 항목 수, `ROS_`/`AMENT_` 변수 개수,
   `command -v ros2` 성공 여부, stderr 첫 줄이다.
   상태: `no_source`, `jazzy_once`, `jazzy_twice`, `missing_distro_only`(kilted만),
   `jazzy_then_missing_distro`(jazzy 다음 kilted).
3. `rmw_probe` 3개: `RMW_IMPLEMENTATION`을 지우거나(unset), `rmw_fastrtps_cpp`, `rmw_cyclonedds_cpp`
   (이미지에 없음)로 둔 하위 Python 프로세스에서 `import rclpy` → `rclpy.init()` → `create_node`를
   차례로 시도한다. 각 단계에 도달할 때마다 즉시 JSON 줄을 출력해 마지막 도달 단계를 남긴다.
   종료 상태, 도달 단계 목록, 파이썬 예외 보고 여부, `get_rmw_implementation_identifier()` 값,
   stderr에서 `rmw`가 들어간 첫 줄을 기록한다.
4. `baseline_same_distro_same_rmw`: 구독자 프로세스(`--role sub`)를 먼저 띄우고 준비 신호를 받은 뒤
   발행자 프로세스(`--role pub`)를 띄운다. 둘 다 `std_msgs/msg/String`, RELIABLE, KEEP_LAST
   depth = N_MESSAGES(200)이다. 발행자는 구독자가 매칭될 때까지(최대 15초) 기다린 뒤 `seq:<번호>`
   메시지를 200개, 0.01초 간격으로 보내고 2초 더 머문다. 구독자는 200개를 받거나 시간이 다 될 때까지
   받는다. 기록 항목은 매칭 대기 시간, 보낸 개수, 받은 개수·고유 개수·중복·순서 뒤바뀜, 첫·마지막 번호,
   수신 비율, 양쪽 프로세스의 `ROS_DISTRO`와 RMW 식별자, 발행자가 그래프에서 본 구독 엔드포인트의
   타입 해시 접두어와 길이다.
5. `summary`: 전체 실행 시간(초). 한 번 실행은 60초 안에 끝나도록 설계했다.

종료 상태: 기준선의 두 프로세스가 모두 0으로 끝나면 0, 아니면 1.

## 해석 범위와 한계

- 이 실험은 **배포판 간 통신, RMW 간 통신, 두 배포판의 apt 공존, 서로 다른 배포판을 연달아 source한
  셸**을 재지 않는다. 컨테이너에 Jazzy와 Fast DDS만 있기 때문이다. 결과를 이 넷의 증거로 쓰면 안 된다.
- `missing_distro_*` 상태는 "설치되지 않은 배포판의 setup.bash를 source한 셸"이다. Kilted가 실제로
  설치된 셸이 아니다. "다른 배포판을 연달아 source했을 때"의 결과로 일반화하지 않는다.
- `jazzy_twice`는 같은 배포판을 두 번 source한 결과다. 다른 배포판을 겹쳐 source한 결과가 아니다.
- 기준선은 한 컨테이너 안 두 프로세스(같은 호스트, 네트워크 없음)에서 잰 "보장 범위 안" 값이다.
  여러 컴퓨터 사이의 통신이나 섞인 묶음의 수신율을 예측하지 않는다.
- 타입 해시(`RIHS01_…`)는 Jazzy 엔드포인트가 그래프에 타입 해시를 싣는다는 관찰일 뿐이다. 이것으로
  Humble 노드와의 비호환을 증명하지 않는다.
- 실물 로봇·시뮬레이터는 쓰지 않는다. 시간 값은 1 CPU 컨테이너의 한 번 실행 값이며 성능 지표가 아니다.

## 시행착오 (시험 실행 기준)

1. 첫 시험 실행에서 `rmw_cyclonedds_cpp` 탐침이 종료 상태 1로 끝났지만, 탐침 코드의 `try/except`가
   출력하도록 만든 JSON 줄이 하나도 나오지 않았다. 처음 코드는 실패 단계를 끝에서만 출력했기 때문에
   어디서 멈췄는지 알 수 없었다. 단계마다 즉시 `reached` 줄을 출력하도록 고쳤다. 다시 실행해 보니
   `start` 다음 `import_ok`에 도달하지 못했다. 즉 `import rclpy` 단계에서 rcl이 RMW 공유 라이브러리
   로드 오류를 stderr에 남기고, 파이썬 예외 없이 프로세스가 끝났다. 그래서 `try/except`로 잡을 수 없다.
   이 동작은 `stages_reached`와 `python_exception_reported` 필드로 기록한다.
2. 첫 시험 실행에서 `/opt/ros/*/lib/librmw_*_cpp.so` 패턴이 RMW 구현이 아닌 메시지 typesupport
   라이브러리(`librmw_dds_common__…`)와 공용 라이브러리(`librmw_fastrtps_shared_cpp.so`)까지 세었다.
   이름에 `__`나 `_shared_`가 든 파일을 빼도록 고쳤다.
3. 그 밖의 실패는 없었다. 두 번째 시험 실행은 종료 상태 0이었고 60초보다 훨씬 짧게 끝났다.
