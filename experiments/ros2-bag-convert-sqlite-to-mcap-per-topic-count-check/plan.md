# 실험 계획: sqlite3 bag → MCAP 변환 전후 토픽별 Count 비교 (ROS 2 Jazzy)

## 질문

ROS 2 Jazzy에서 sqlite3(.db3) bag을 `ros2 bag convert`로 MCAP으로 바꿀 때 다음 두 가지를 확인한다.

1. 출력 YAML의 토픽 선택 키에 따라 어떤 토픽이 빠지는가. 이때 명령의 종료 코드로 그 누락을 알 수 있는가.
2. 변환 전후 `ros2 bag info`의 총 `Messages`만 비교할 때와 토픽별 `Count`를 비교할 때 판정이 갈리는가.

## research.md 기준 예측값 (실측 아님)

입력 토픽은 `/imu`(200 Hz), `/scan`(10 Hz), `/camera/image_raw`(15 Hz)에 숨김 토픽 `/camera/_debug`(1 Hz)를 더한 4개다. 60 s 구간이다.

| 케이스 | 출력 YAML 키 | research.md 근거 | 예측 |
| --- | --- | --- | --- |
| a | `storage_id: mcap`, `all_topics: true` | topic_filter.cpp L177-L182 | 비숨김 토픽 3개는 차이 0, `/camera/_debug`는 출력에 없음, 종료 코드 0 |
| b | a + `include_hidden_topics: true` | 같은 파일 | 4개 토픽 모두 차이 0 |
| c | `storage_id: mcap`, `storage_preset_profile: fastwrite`(토픽 선택 없음, MCAP README 예시 형태) | README L253, topic_filter.cpp L134-L143 | 출력 메시지 0, 종료 코드 0 |
| d | `storage_id: mcap`, `all: true` | record_options.cpp L90-L97 | a와 같은 토픽 구성 |
| e | `storage_id: ""`, `all_topics: true` | default_storage_id.cpp L21(Jazzy 기본 mcap) | 출력 Storage id mcap, 토픽 구성은 a와 같음 |

이 밖의 예측은 다음과 같다.
- 숨김 토픽 하나만 빠지면 총합 감소 비율은 작은데(설계상 60/13560, 1% 미만) 그 토픽의 손실 비율은 100%다. 총합 비교는 이 누락을 거의 드러내지 못한다.
- `ros2 bag info`의 Count(메타데이터 값)와 SequentialReader로 끝까지 읽어 센 개수가 같다.

## 무엇을 어떻게 재는가

환경: 하네스 컨테이너 `ros:jazzy-ros-base`, 네트워크 없음, 1 CPU, 1 GiB. 추가 패키지를 설치하지 않는다(rosbag2_py, sensor_msgs, std_msgs, ros2bag CLI만 사용).

1. **입력 bag 합성.** `rosbag2_py.SequentialWriter`로 `storage_id='sqlite3'` bag을 `/tmp` 아래에 쓴다. 각 토픽은 주기 간격으로 타임스탬프를 합성하고(Hz × 60개), 시간순으로 섞어 기록한다. 메시지는 `rclpy.serialization.serialize_message`로 CDR 직렬화한다. 이미지는 4×4 rgb8이다.
2. **입력 검증.** 입력 bag에 `ros2 bag info`를 실행해 Storage id, Messages, 토픽별 Count를 파싱한다. `SequentialReader`로 끝까지 읽은 토픽별 개수도 함께 구한다. 둘 중 하나라도 실제로 쓴 개수와 다르면 `input_ok=false`를 출력하고 종료 코드 2로 실패한다(입력 생성 문제이므로 실험 무효).
3. **변환.** 케이스 a~e마다 YAML(`output_bags:` 한 항목)을 쓰고 `ros2 bag convert -i <입력> -o <yaml>`를 subprocess로 실행한다. 종료 코드, 소요 시간, 로그의 WARN/ERROR/hidden 줄(최대 3줄)을 기록한다.
4. **변환 후 측정.** 출력 bag마다 `ros2 bag info`의 Storage id, Messages, 토픽별 Count를 파싱하고, 출력 저장 파일 이름을 기록한다. `SequentialReader`로 출력 메시지를 직접 센다. 출력에 없는 토픽의 Count는 0으로 둔다.
5. **판정 계산.** 토픽별로 [전 Count, 후 info Count, 후 reader 개수, 손실 비율=(전−후)/전]을 기록한다. 총합 감소량과 감소 비율을 함께 계산한다. `per_topic_pass`는 모든 토픽의 차이가 0이고 토픽 집합이 같을 때만 true다. `info_equals_reader`는 info Count와 reader 개수가 같은지다.
6. **출력.** `input_bag` 1줄, `convert_case` 5줄, `summary` 1줄을 JSON 줄로 낸다. 케이스 a와 입력 bag에는 `ros2 bag info` 원문 줄(Storage id·Messages·Topic)을 남긴다. 숫자는 모두 실행 중에 센 값이며 코드에 결과 숫자를 적지 않는다. 입력 개수(Hz × 60)는 입력 설계값이고 결과가 아니다.

실패 판정은 다음과 같다. 입력 검증 실패, 변환 명령의 subprocess 타임아웃(40 s), 또는 스크립트 예외가 나면 실행 실패다. 케이스의 종료 코드가 0이 아니어도 실험은 계속하고 그 값을 그대로 기록한다.

한계는 다음과 같다. 개수만 비교하며 메시지 내용, 타임스탬프, QoS, 메시지 정의의 동일성은 보지 않는다. 합성 bag이며 실제 센서 녹화나 대용량 bag이 아니다. Jazzy만 확인했고 Humble 동작은 확인하지 않았다. 서비스 이벤트 토픽(`all_services`)과 알 수 없는 메시지 타입 토픽은 다루지 않는다. 시뮬레이터나 실물 하드웨어와도 무관하다.

## 시행착오

- 1차 시험 실행에서 실행 자체는 성공했지만, 케이스마다 `ros2 bag info` 원문과 YAML 전문을 출력하자 stdout이 하네스 보관 한도(stdout 끝 8000자)를 넘었다. 그 결과 `results.json`에서 앞쪽의 `input_bag` 줄과 초반 케이스 줄이 잘렸다. 그래서 케이스 줄을 짧게 바꿨다. YAML은 키 목록만 남기고, 토픽별 값은 배열로 줄이고, info 원문은 입력 bag과 케이스 a에만 남기고, 로그 줄에서 타임스탬프를 지웠다. 2차 시험 실행에서는 7줄이 모두 보관되는 것을 확인했다.
- 그 밖에 API 오류나 변환 실패는 없었다(TopicMetadata는 Jazzy 시그니처인 `id` 인자를 먼저 시도하고, 실패하면 `id` 없이 만드는 대체 경로를 둔다).
