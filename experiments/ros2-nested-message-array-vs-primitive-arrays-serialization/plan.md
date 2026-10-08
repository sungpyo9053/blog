# 실험 계획: Foo[] 대 uint64[]+uint32[] — 비기본형 요소 수를 세고 rclpy publish() 경로를 재기

## 질문

같은 값, 같은 N=10000, 같은 30 Hz 조건에서 ROS 2 DDS tuning 문서의 예시인 `Foo[] my_large_array`와
`uint64[] foo_1_array` + `uint32[] foo_2_array`를 비교한다. 두 구조는 다음 항목에서 얼마나 다른가?

1. 메시지 하나에 든 비기본형(non-primitive) 요소 수
2. 선언 필드 바이트와 실제 직렬화 크기(`serialize_message` 길이)
3. 메시지 구성 시간, `serialize_message`·`deserialize_message` 시간
4. `publish()` 호출 시간
5. 수신 측에서 raw 구독과 역직렬화 구독이 실제로 받은 개수와 주기

요소마다 `builtin_interfaces/Time`을 넣으면 차이가 어떻게 달라지는지도 함께 본다
(`FooStamped[]` 대 `uint64[]`+`uint32[]`+`int32[] stamp_sec`+`uint32[] stamp_nanosec`).

## research.md 기준 예측값(실행 전에 적은 값)

- 비기본형 요소 수(메시지당, 메시지 자신은 세지 않음): FooArray = N, FooSplit = 0,
  FooStampedArray = 2N(Foo 하나 + Time 하나), FooStampedSplit = 0.
  N=10000이면 10000 / 0 / 20000 / 0이다.
- 선언 필드 바이트: Foo 계열 12N, Stamped 계열 20N. N=10000이면 두 구조 모두 120000(Foo), 200000(Stamped)으로 같다.
- 직렬화 크기(XCDRv1, 인캡슐레이션 4바이트 포함): Research가 Fast-CDR 정렬 규칙에서 손으로 도출한 식이다.
  - FooArray 16N+8, FooSplit 12N+16, FooStampedArray 24N+8, FooStampedSplit 20N+24
  - N=0: 8 / 16 / 8 / 24 (Research는 N=0에서 빈 uint64 시퀀스 앞 정렬 패딩 여부를 불확실하다고 표시했다)
  - N=1: 24 / 28 / 32 / 44
  - N=2: 40 / 40 / 56 / 64
  - N=3: 56 / 52 / 80 / 84
  - N=10000: 160008 / 120016 / 240008 / 200024
- 시간: 방향만 예측한다. Foo[] 쪽이 구성·`serialize_message`·`publish()`·역직렬화 수신에서 더 오래 걸린다
  (요소별 `__convert_from_py` 루프 근거). Time을 넣은 배열 쪽 차이가 더 크다. 배율은 예측하지 않는다(공식 근거 없음).
- 수신: raw 구독에서는 두 구조의 차이가 줄고, 역직렬화 구독에서 차이가 커질 수 있다(방향 가설).

## 환경(하네스 고정)

`ros:jazzy-ros-base`, `--network none`, 1 CPU(`--cpus 1`, `os.cpu_count()`는 호스트 값을 보일 수 있다), 1 GiB,
기본 RMW `rmw_fastrtps_cpp`. `ROS_PYTHON_CHECK_FIELDS`와 `RMW_FASTRTPS_PUBLICATION_MODE`는 설정하지 않고,
실행 때 실제 값을 `env` 줄에 기록한다. 시뮬레이터·실제 로봇·액추에이터는 쓰지 않는다.

## 무엇을 어떻게 재는가

`experiment.py` 한 파일이 세 단계로 실행된다. 모든 숫자는 실행 중에 재며, 한 줄에 JSON 하나씩 출력한다(`kind` 필드로 구분).

1. **build**: DDS tuning 문서 예시 그대로의 `Foo.msg`, `FooArray.msg`, `FooSplit.msg`와 Time 변형
   `FooStamped.msg`, `FooStampedArray.msg`, `FooStampedSplit.msg`를 실행 중에 생성한다.
   `rosidl_default_generators`로 `/var/tmp/foo_ws`에서 cmake configure → compile → install을 한다.
   하네스 `/tmp`는 noexec라서 빌드 위치로 쓰지 않는다. maintainer email은 `user@example.com`이다.
   단계별 시간을 `build` 줄에 남긴다. 그다음 설치 경로를 `AMENT_PREFIX_PATH`·`LD_LIBRARY_PATH`·`PYTHONPATH`에
   더한 환경에서 같은 스크립트를 `--measure`로 다시 실행한다.
2. **size**(N = 0, 1, 2, 3, 10000): 같은 난수 값을 네 타입에 담는다.
   - `non_primitive`: 메시지 객체를 실제로 순회하며 중첩 메시지 인스턴스를 센다.
   - `field_bytes`: 선언 기본형 필드 폭(uint64 8, uint32/int32 4)의 합이다.
   - `serialized_bytes`: `len(serialize_message(msg))`이다.
   - `same_values`: 두 구조가 같은 값 튜플을 담았는지 확인한다.
   - `roundtrip_equal`: 역직렬화 결과가 원래 값과 같은지 확인한다.
3. **construct**(N=10000, 9회, 워밍업 1회 제외): 같은 Python int 리스트로 메시지를 만드는 시간이다.
   FooArray는 `Foo` 객체 N개를 만든다. FooSplit은 `array.array('Q'/'I')`로 만든다. 비교용 `FooSplit(list)`는 리스트를 그대로 넣는다.
   `time.perf_counter_ns`로 재고 중앙값·p90(µs)을 보고한다.
4. **serdes**(N=10000, 9회): `serialize_message`(= `convert_from_py` + `rmw_serialize`)와 `deserialize_message` 시간이다.
5. **publish_solo**: 구독자 프로세스 두 개(raw 전용, 역직렬화 전용)를 띄우고 매칭(`get_subscription_count`)을 확인한다.
   이어서 raw 구독자만 듣는 `solo_*` 토픽에 미리 만든 메시지를 30 Hz 간격으로 10번 발행한다.
   각 `publish()` 호출 시간을 잰다. 수신 측 Python 역직렬화가 없는 조건에서 발행 경로 비용을 본다.
6. **publish_paced**: raw와 역직렬화 구독자가 모두 듣는 `rate_*` 토픽에 30 Hz 목표로 1.2초 발행한다.
   `publish()` 시간, 실제 발행 횟수와 주기, `budget_share_median`(= 중앙값 publish 시간 × 30, 30 Hz 주기 중 몇 배를 쓰는지)을 기록한다.
   1 CPU를 발행자와 두 구독자가 나눠 쓰는 조건이다.
7. **receive**: 구독자가 받은 개수와 주기다. raw 모드는 `ros2 topic hz` 기본 모드처럼 `raw=True`로 받는다.
   역직렬화 모드는 `--filter` 모드처럼 Python 메시지로 받는다. CLI `ros2 topic hz`는 띄우지 않고 이 두 구독으로 대체했다.
   QoS는 hz와 같은 `qos_profile_sensor_data`(best effort)다. `count`·`rate_hz`는 첫 도착(보통 워밍업 발행)을 뺀 값이다.
   `arrived_incl_warmup`은 워밍업을 포함한 전체 도착 수이며 `sent + 1`과 비교한다.

## 판정 기준

- 크기: 실측이 위 예측식과 다르면 식을 고치지 않고 차이를 그대로 보고한다. `same_values`와 `roundtrip_equal`이 false면 비교 자체를 무효로 본다.
- 시간: 하네스 5회 실행의 각 중앙값을 모아 범위로 쓴다. 변동이 크면 범위를 함께 쓴다.
- 수신: 한 실행 안의 상대 비교로만 읽는다. best effort 손실, CPU 경합, 발행 측 정체가 섞인 결과다.
  `publish_solo`와 `publish_paced`를 함께 봐야 원인을 나눌 수 있다.
- 실패: 빌드 실패, 매칭 20초 초과, 구독자 결과 누락이면 0이 아닌 종료 코드로 끝난다.

## 한계

- rclpy와 `rmw_fastrtps_cpp`만 다룬다. rclcpp, Cyclone DDS, Zenoh, 다중 호스트·WiFi, 저전력 ARM 보드로 일반화하지 않는다.
- 한 컨테이너, 네트워크 없음, 1 CPU 조건이다. 발행자와 구독자가 같은 CPU를 나눠 쓰므로 `publish_paced`의 시간에는 경합이 포함된다.
- 시간 표본 수가 작다(9~37개). 중앙값과 p90만 보고한다.
- 빌드는 매 실행마다 새로 하며, 빌드 시간은 실험 질문의 측정값이 아니다.

## 시행착오(시험 실행에서 실제로 겪은 것)

1. **첫 시험 실행 실패.** 구독자 프로세스의 stdin을 먼저 닫은 뒤 `communicate()`를 불러 `ValueError: I/O operation on closed file`이 났고 종료 코드 1로 끝났다.
   전체 시간도 하네스 기준 약 61초로 60초 예산을 넘었다.
   → stdin을 닫고 stdout을 읽는 방식으로 고쳤다.
2. **raw와 역직렬화 구독을 한 프로세스에 두었더니 두 모드가 구분되지 않았다.**
   단일 executor에서 역직렬화 콜백이 raw 콜백까지 늦춰 두 모드의 수신 개수가 똑같이 낮게 나왔다.
   → raw 전용과 역직렬화 전용 구독자를 별도 프로세스로 나눴다. hz도 별도 프로세스로 뜨는 상황에 더 가깝다.
3. **빌드 시간 단축 시도 실패.** C 타입서포트 생성기만 `find_package`하면 C++ 생성을 건너뛸 수 있을지 시험했다.
   결과는 configure 단계의 `Unknown CMake command "rosidl_generate_interfaces"` 오류였다.
   로그에는 `builtin_interfaces`를 찾는 과정에서 C++ 타입서포트도 등록된다고 나왔다.
   → 문서 튜토리얼과 같은 `rosidl_default_generators`로 되돌렸다. colcon 대신 cmake를 직접 불러 단계별 시간을 기록하게 했지만 시간 절감 효과는 작았다.
   빌드의 대부분은 compile 단계였다.
4. **60초 예산.** 구독자를 두 프로세스로 나누자 매칭 대기가 늘어 전체가 약 57초가 됐다.
   → 반복 수를 11에서 9로, 30 Hz 발행 시간을 1.5초에서 1.2초로, solo 발행 수를 12에서 10으로 줄였다. 토픽 사이 대기도 줄였다.
   마지막 시험 실행은 약 52.5초에 종료 코드 0으로 끝났다.
5. **워밍업 손실과 측정 손실을 구분할 수 없었다.** 한 시험 실행에서 solo FooArray의 수신 수가 발행 수보다 하나 적었다.
   워밍업이 사라졌는지 측정 메시지가 사라졌는지 알 수 없었다.
   → 워밍업을 포함한 전체 도착 수 `arrived_incl_warmup`을 함께 출력하게 했다.
6. Research가 미리 짚은 `/tmp` noexec, maintainer email 형식 문제는 처음부터 `/var/tmp`, `user@example.com`으로 피했다. 이번 시험에서 다시 나지 않았다.
