# 실험 계획: topic list에는 보이는데 일부 토픽만 받아질 때, QoS 불일치와 조각 손실을 토픽별 수신 수로 가르기

## 질문

`ros2 topic list`에 토픽이 모두 보이는데 일부 토픽만 받아질 때 원인은 두 가지로 의심된다.
하나는 reliability 불일치이고, 다른 하나는 큰 메시지의 IP 조각 손실이다.
같은 측정 창에서 **토픽별 기대 수신 수와 실제 수신 수**를 세면 둘의 모양이 다르게 나오는가?

- 불일치라면 크기와 무관하게 0건이고 incompatible QoS 경고가 뜰 것이다.
- 조각 손실이라면 작은 토픽은 거의 다 오고 큰 토픽만 크게 모자랄 것이다. 링크만 바꾼 대조(손실 0)에서는 모두 올 것이다.

옵션 없는 `ros2 topic echo`가 정말 발행자에 맞춰 reliability를 고르는지도 Jazzy 코드와 CLI로 확인한다.

## 환경과 범위

- 하네스 컨테이너 `ros:jazzy-ros-base`, `rmw_fastrtps_cpp`(이미지에 Cyclone DDS 없음), `--network none`, 1 CPU, 1 GiB.
- 발견 범위는 `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`로 둔다. 공유 메모리 대신 UDP 루프백을 쓰도록 `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`로 둔다.
- **실제 와이파이와 실제 IP 조각화는 없다.** 루프백 MTU는 65536이다. 컨테이너에는 NET_ADMIN 권한과 `ip` 명령이 없어 MTU나 손실(tc netem)을 바꿀 수 없다.
  - 그래서 갈래 2는 중계 노드가 손실 *모델*을 적용해 흉내 낸다. 측정값은 "모델을 넣은 ROS 파이프라인의 수신 수"이지 와이파이 실측이 아니다.
  - 실제 IP 조각화가 없었다는 사실은 커널 카운터(`/proc/net/snmp`의 `Frag*`, `Reasm*`) 전후 차이로 함께 기록한다.
- 시뮬레이션·하드웨어 로봇은 쓰지 않는다. 로봇을 움직이는 명령도 없다.

## research.md 기준 예측값

- 공식 QoS 표 기준: best effort 발행 × reliable 구독은 호환되지 않는다. 수신 0건이며 토픽 크기와 무관하다. best effort 구독은 정상 수신한다.
- 발견과 데이터 전달은 별개 단계다. 0건인 구독자 쪽에서도 토픽은 목록에 보일 것이다.
- Jazzy echo(소스 확인 사항): 옵션이 없으면 발견한 발행자가 모두 best effort일 때 BEST_EFFORT를 고른다. `--qos-reliability reliable`을 주면 RELIABLE이 되어 0건이고, `offering incompatible QoS` 경고가 뜰 것이다.
- 조각 산술(MTU 1500, IPv4 헤더 20 B, UDP 헤더 8 B → 조각당 1480 B):
  - 1472 B 이하 페이로드는 1조각, 14720 B 데이터그램은 10조각이다.
  - 조각당 독립 손실 1/32에서 데이터그램이 온전히 올 확률은 1조각 0.96875, 10조각 약 0.728이다.
- 이 실험에서 추가로 둔 가정(research.md는 샘플 단위 계산을 하지 않았다):
  - 샘플 하나를 `MaxMessageSize` 14720 B 이하 데이터그램으로 나누고, 데이터그램마다 위 식으로 조각을 낸다고 가정한다.
  - 약 320 KB `/points` 샘플은 약 22개 데이터그램, 약 218조각이다. 온전히 올 확률은 (31/32)^218로 약 0.001이므로 창 안에서 거의 0건이 예상된다.
  - IMU(수백 B)는 1조각이라 약 97%가 예상된다.

## 무엇을 어떻게 재는가

한 프로세스에 `robot`(발행), `laptop`(구독), `wifi_model`(중계) 노드를 MultiThreadedExecutor로 돌린다.
발행 토픽은 세 개이며 모두 sensor_data와 같은 best effort, keep last 5 프로필이다.

- `/imu/data`(Imu, 20 Hz)
- `/scan`(LaserScan 720개 거리, 10 Hz)
- `/points`(PointCloud2 20000점 × 16 B, 10 Hz)

각 메시지의 `header.frame_id`에 `seq=N`을 넣는다. 창 시작·끝의 발행 seq로 기대 수신 수를 정하고, 창 안의 seq만 수신 수로 센다(창 4초, 끝난 뒤 0.6초 도착 유예).

1. `qos`: 토픽마다 reliable 구독자와 best effort 구독자를 하나씩 만든다. 다음 값을 출력한다.
   - 기대/실제 수신 수
   - `incompatible_qos` 이벤트 누적 수
   - `get_publishers_info_by_topic`으로 본 발행자 reliability
   - `get_topic_names_and_types`(= `ros2 topic list`가 보는 목록)에 토픽이 있는지
2. `echo_choose_qos`: Jazzy ros2topic의 `EchoVerb.choose_qos`를 실제 인자 파서로 호출한다. `/points`에서 옵션 없음과 `--qos-reliability reliable` 각각의 선택 결과를 기록한다.
3. `echo_cli`: 별도 프로세스로 `ros2 topic echo <topic> <type> --no-daemon --field header.frame_id --csv`를 6~7초 실행한 뒤 SIGINT로 끊는다.
   - 실행 조합: `/imu/data` 옵션 없음, `/imu/data` `--qos-reliability reliable`, `/points` 옵션 없음
   - 출력: 실행 중 발행 수, 받은 서로 다른 seq 줄 수, 첫~마지막 seq 폭(폭과 줄 수가 같으면 중간 손실 없음), stderr의 incompatible 경고 여부
   - 발행 수와 수신 줄 수의 차이에는 CLI 기동·발견 시간이 들어간다. 그래서 중간 손실 판단은 폭과 줄 수로 한다.
4. `link_emulation`: `wifi_model`이 원 토픽을 받아 `/wifi/...`로 다시 발행한다.
   - 메시지마다 `serialize_message`로 실제 직렬화 크기를 잰다. 위 가정으로 데이터그램 수와 IP 조각 수를 계산한다.
   - 조각마다 `random.random() < p`이면 그 메시지를 버린다. 시드는 실행마다 새로 뽑아 출력한다.
   - p=0(유선 대조)과 p=1/32(손실 링크 모델)를 같은 구독자·같은 창 길이로 비교한다. 모델 생존 확률 (1-p)^n도 함께 출력한다.
5. `kernel_counters`: 실행 전후 `Reasm*`, `Frag*` 차이를 기록한다. 루프백에서 실제 IP 조각화가 있었는지 확인하는 용도다.

마지막 `done` 줄에 총 소요 시간을 남긴다. 결과 숫자는 코드에 미리 적지 않고 모두 실행 중에 센다.

## 판정

- 갈래 1 지지: reliable 구독만 크기와 무관하게 0건이고 incompatible 이벤트·경고가 뜬다. best effort 구독은 기대치만큼 받는다.
- 갈래 2 모델 지지: p=0에서는 세 토픽 모두 기대치만큼 받는다. p=1/32에서는 조각 수가 많은 토픽일수록 수신 비율이 낮다. 경고는 없다.
- 실패 판정: best effort 구독이 손실 없는 루프백에서도 기대치보다 크게 모자라면 측정 창이나 CPU 한계 문제로 보고 해석하지 않는다. 60초를 넘겨도 실패다.

## 한계

- 와이파이의 실제 손실은 몰려서 일어날 수 있다. 문서가 말하는 증상도 비율 감소가 아니라 재조립 버퍼가 차서 최대 30초 멈추는 것이다. 이 모델은 독립 손실만 흉내 내며, 재조립 버퍼 정지는 재현하지 않는다.
- Fast DDS 기준이다. 질문자의 Cyclone DDS와 데이터그램 분할 방식이 다를 수 있다. 샘플→데이터그램 분할은 가정이다.
- 한 컨테이너 안의 루프백이다. 배포판 혼용(Foxy↔Humble)은 재현하지 않는다.

## 시행착오

1. 환경 확인용 시험 실행에서 확인한 것: 이미지에는 `rmw_fastrtps_cpp`만 있고 Cyclone DDS는 없다. 루프백 MTU는 65536이고, `ip` 명령과 NET_ADMIN 권한이 없다. 그래서 실제 IP 조각 손실을 만들 수 없어 중계 노드 손실 모델로 바꿨다.
2. 첫 정식 시험 실행에서 옵션 없는 `ros2 topic echo /imu/data`가 0줄이었다. stderr는 `Could not determine the type for the passed topic`이었다(발견 전에 타입을 못 찾음). 메시지 타입을 인자로 직접 주고 `--no-daemon`을 붙여 고쳤다. 이후 시험 실행에서 정상 수신했다.
3. 첫 시험 실행에서 `link_emulation`이 p=0인데도 모든 토픽 0건이었다. stderr에는 `/wifi/...` 토픽의 incompatible QoS(RELIABILITY) 경고가 있었다.
   - 원인: 같은 프로세스에서 `EchoVerb.choose_qos`를 `--qos-reliability reliable`로 호출하자 공유 프리셋 객체 `qos_profile_sensor_data`의 reliability가 RELIABLE로 바뀌었다. 그 뒤 이 객체로 만든 구독이 reliable이 됐다.
   - 조치: 모든 끝점이 매번 새로 만든 프로필을 쓰도록 고쳤다. 프리셋의 호출 전후 reliability를 `echo_choose_qos` 줄에 기록하도록 했다. 두 번째 시험 실행에서 전후 값이 BEST_EFFORT → RELIABLE로 바뀐 것을 다시 관측했다.
   - 이 변경은 ros2cli 코드를 같은 프로세스에서 불렀을 때만 나타난다. 별도 프로세스인 `ros2 topic echo` CLI에는 영향이 없다. 어느 소스 줄에서 바뀌는지는 추적하지 않았다.
4. 두 번째 시험 실행은 종료 코드 0, 약 40초에 끝났다(60초 제한 안).
