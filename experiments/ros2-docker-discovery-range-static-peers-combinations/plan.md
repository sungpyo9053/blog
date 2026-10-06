# 실험 계획: 같은 호스트에서 발견 범위·정적 피어 36칸을 실제 rclpy 노드로 판정하기

## 질문

ROS 2 공식 문서 "Using Improved Dynamic Discovery"의 같은 호스트 표는 노드 A 설정 6가지 ×
노드 B 설정 6가지 = 36칸에 O/X를 적어 둔다. 각 설정은 (정적 피어 없음/있음) ×
(`ROS_AUTOMATIC_DISCOVERY_RANGE` = OFF/LOCALHOST/SUBNET)이다. Jazzy의 실제 rclpy 노드 두 개를
한 기계에서 띄우면 이 36칸이 표 그대로 나오는가? research.md가 도출한 "양쪽 모두 OFF가 아니면 O"
규칙과 칸 단위로 일치하는가? A·B를 바꿔도 판정이 같은가?

같이 확인할 표 밖의 함정 세 가지:

1. OFF에 `ROS_STATIC_PEERS`를 넣으면 rcl이 피어를 버리는가, 그리고 경고를 남기는가?
2. `ROS_AUTOMATIC_DISCOVERY_RANGE=subnet`(소문자)은 실제로 무엇으로 해석되는가?
3. `ROS_LOCALHOST_ONLY=1`이 남아 있으면 SUBNET·정적 피어 설정이 무시되는가?

research.md는 표를 세고 rcl·rmw_fastrtps 코드를 읽었을 뿐 실행하지 않았다. 이 실험은 그중
**같은 호스트 표와 rcl 해석**만 실행으로 채운다.

## research.md 기준 예측값

- 같은 호스트 표: O 16칸, 행별 O 수 0, 4, 4, 0, 4, 4(행 순서: 피어 없음 OFF·LOCALHOST·SUBNET,
  피어 있음 OFF·LOCALHOST·SUBNET). 규칙 "양쪽 모두 OFF가 아니면 O"와 불일치 0칸.
- 대칭: A·B를 바꾼 15쌍(대각선 6칸 제외)에서 판정이 달라지는 쌍 0.
- OFF 행·열은 피어 유무와 무관하게 X.
- OFF + 정적 피어: research.md는 init.c를 근거로 "rcl이 `ROS_STATIC_PEERS will be ignored` 경고를
  남기고 피어를 무시한다"고 적었다. 예측: 피어는 버려지고(유효 피어 수 0), 경고는 OFF+피어 문맥
  수(12)만큼 나온다.
- 소문자 `subnet`: `Invalid value` 경고 후 LOCALHOST로 간주(discovery_options.c L76-L84). 같은
  호스트이므로 SUBNET 상대와는 여전히 O로 예측.
- `ROS_LOCALHOST_ONLY=1` + SUBNET + 피어: 경고 후 LOCALHOST로 고정, 정적 피어 수 0(init.c L187-L194).
  같은 호스트이므로 여전히 O로 예측.
- 다른 호스트 표(O 13칸)는 이 하네스로 잴 수 없다. 예측도 측정도 하지 않는다.

## 무엇을 어떻게 재는가

- 환경: 하네스의 `ros:jazzy-ros-base` 컨테이너 한 개, `--network none`(루프백만 있음), 1 CPU,
  1 GiB, 기본 RMW `rmw_fastrtps_cpp`. rclpy와 std_msgs만 쓴다.
- 구조: 메인 프로세스가 같은 파일을 `--worker a`, `--worker b`로 두 번 띄운다. 두 프로세스가 표의
  "노드 A", "노드 B"다. 칸 하나마다 두 워커가 각자 rclpy `Context`를 새로 열고, 그 직전에
  `os.environ`의 `ROS_AUTOMATIC_DISCOVERY_RANGE`·`ROS_STATIC_PEERS`(`127.0.0.1`)·
  `ROS_LOCALHOST_ONLY`를 그 칸의 값으로 바꾼다. rcl은 이 변수들을 `rclpy.init()` 안에서 읽으므로
  문맥마다 설정이 따로 고정된다.
- 칸끼리 섞이지 않도록 칸 k는 `ROS_DOMAIN_ID = 20 + k`를 쓴다. 9칸씩 4묶음으로 워커 쌍을 띄운다
  (워커당 Fast DDS 참가자 9개, 컨테이너 pids 한도 256 안에 들기 위함).
- 각 문맥에서 노드 `node_a`/`node_b`가 `probe_a`/`probe_b` String을 0.1초마다 발행하고 상대
  토픽을 구독한다. 노드를 다 만든 시점부터 4초 동안 매 0.1초에
  - `get_node_names_and_namespaces()`에 상대 노드 이름이 처음 보인 시각(`as`/`bs`, 초),
  - 상대 메시지를 처음 받은 시각(`ar`/`br`)과 받은 개수(`an`/`bn`)를 잰다.
- 판정 `ok=1`은 양쪽 모두 상대를 그래프에서 보고 **그리고** 양쪽 모두 메시지를 받은 경우다(표의
  "발견하고 통신함"). `pred`는 research.md 규칙으로 실행 중에 계산한 값이다.
- 유효 설정: rcl은 `rcl_init`에서 `Automatic discovery range is ...`, `Static peers count is N`을
  DEBUG로 남긴다. 워커가 `rcl` 로거를 DEBUG로 올리고, 메인이 워커 stderr에서 이 두 줄을 문맥 순서대로
  읽어 칸별 `ae`/`be`(예: `L1` = LOCALHOST, 정적 피어 1개)로 적는다. 줄 수가 문맥 수와 다르면
  None으로 남기고 `effective_missing`에 센다.
- 경고: 워커 stderr에서 `ROS_STATIC_PEERS will be ignored`, `Invalid value`,
  `'localhost_only' is enabled` 문자열 개수를 센다.
- 함정 2·3은 칸 sweep 뒤에 각자 독립 워커 쌍으로 돌려 경고가 어느 설정 것인지 섞이지 않게 한다.
  A만 함정 설정, B는 SUBNET.
- 출력: 칸마다 JSON 한 줄(36줄), 함정 2줄, 요약 1줄. 요약에는 O 칸 수, 행별 O 수, 규칙 불일치
  칸, 비대칭 쌍 수, 한쪽만 본 칸, OFF+피어 경고 수와 피어가 버려진 문맥 수, 유효 범위 불일치 수,
  첫 발견·첫 수신 시각 최소/최대, 워커 준비 시간·스레드 수, 전체 소요 시간이 들어간다.
- 결과 숫자는 코드에 적지 않는다. 코드의 숫자는 입력값(도메인 시작 20, 묶음 9, 관찰 4초, 주기 0.1초,
  피어 주소 127.0.0.1)뿐이다.

## 한계

- 같은 컨테이너 안 두 프로세스이므로 공식 표의 "같은 호스트" 절반만 잰다. 다른 호스트 표, Docker
  컨테이너 두 개 사이, `--network host`/브리지 비교는 측정하지 않는다.
- `--network none`에는 루프백만 있다. SUBNET 칸이 O로 나와도 실제 LAN 멀티캐스트가 된다는 뜻이
  아니다(같은 호스트 통신은 Fast DDS 공유 메모리·루프백으로도 성립한다).
- 정적 피어 주소는 루프백뿐이라, 같은 호스트에서는 피어 유무가 판정을 바꾸지 않는 것이 예상이다.
  "한쪽 피어만으로 다른 호스트 O"라는 표의 주장은 이 실험으로 확인되지 않는다.
- 한 프로세스가 문맥 여러 개(=Fast DDS 참가자 여러 개)를 가진다. 칸마다 도메인이 달라 서로
  발견하지 않지만, 문맥당 프로세스 하나를 쓰는 실제 배치와 자원 사용은 다르다.
- 첫 발견 시각은 각 워커가 자기 노드를 다 만든 시점 기준이다. 두 워커의 시작이 어긋나 0초가
  나올 수 있으며, 발견 지연 측정값으로 일반화하지 않는다.
- rmw_fastrtps_cpp만 확인했다. Cyclone DDS·Connext·rmw_zenoh는 다루지 않는다.

## 시행착오

1. 1차 시험 실행에서 36칸 판정은 예측과 같았지만, OFF+정적 피어 문맥 12개에서
   `ROS_STATIC_PEERS will be ignored` 경고가 한 번도 나오지 않았다(0/12). rcl jazzy(18d96c9)
   init.c를 다시 읽으니, 범위가 OFF이면 `rcl_get_discovery_static_peers()`를 아예 호출하지 않아
   피어 수가 0으로 남고, 경고는 "피어 수 > 0이고 OFF"일 때만 나온다. 즉 환경변수 경로에서는 이 경고가
   나올 수 없고, 코드로 init options에 피어를 직접 넣은 경우에만 해당한다. research.md의
   "OFF + 정적 피어 → 경고" 서술은 환경변수 사용자에게는 맞지 않는다는 점을 확인했다.
   경고 개수만으로는 피어가 버려졌는지 알 수 없으므로, rcl의 DEBUG 로그에서 유효 범위와 정적 피어
   수를 읽어 칸별로 기록하도록 고쳤다.
2. 1차 실행의 `ROS_LOCALHOST_ONLY` 함정은 stderr에서 부분 문자열 `ROS_LOCALHOST_ONLY`를 세었는데,
   rcl이 실제로 남기는 고정 문구는 `'localhost_only' is enabled, ...`이라 그 1회가 어느 문장이었는지
   확인할 수 없었다. 정확한 문구로 세도록 바꿨다.
3. rcl은 `rcl_init` 안에서 유효 설정을 DEBUG로 찍는데, `--ros-args --log-level rcl:=debug`만으로는
   첫 문맥에서 로그 설정이 그 뒤에 적용될 수 있다. 그래서 `rclpy.init()` 전에
   `set_logger_level("rcl", DEBUG)`도 호출했다. 2차 시험 실행에서 유효 설정이 모든 문맥에서
   읽혔다(누락 0, 로그 레벨 설정 오류 0).
4. 2차 시험 실행 전체 소요 시간은 하네스 기준 약 34초로 60초 한도 안이다(문맥 9개 워커의 스레드
   최대값도 기록해 pids 한도 256과 비교할 수 있게 했다).
