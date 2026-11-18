# 실험 계획: Jazzy가 녹화·변환한 bag 4칸의 파일 형식과 Humble 판독 규칙 대입

## 질문

Jazzy에서 녹화한 sqlite3·MCAP bag과, 그 bag을 Jazzy `ros2 bag convert`로 저장 형식만 바꿔 다시 쓴 bag(합 4칸)은
Humble rosbag2 0.15.17이 읽는 형식인가? 그리고 metadata.yaml만 고치는 우회법 두 가지는 무엇을 남기고 무엇을 잃는가?

이 실험은 `ros:jazzy-ros-base` 컨테이너에서만 실행한다. **Humble을 실행하지 않는다.** "Humble 통과/실패"는
아래 두 코드 줄의 요구 조건을 Jazzy가 실제로 쓴 파일에 적용한 판정이며, Humble 실행 결과가 아니다.

- 폴더 info 규칙: rosbag2 0.15.17 `rosbag2_storage/src/rosbag2_storage/metadata_io.cpp` L70-L71
  `topic.offered_qos_profiles = node["offered_qos_profiles"].as<std::string>();`
  → metadata.yaml의 `offered_qos_profiles` YAML 노드가 스칼라(문자열)여야 통과. 목록(sequence)이면 yaml-cpp `bad conversion`.
- 재생 규칙: rosbag2 0.15.17 `rosbag2_transport/src/rosbag2_transport/qos.cpp` L85-L88
  `history`·`reliability`·`durability`·`liveliness`를 `.as<int>()`로 읽음
  → QoS 문자열을 YAML로 풀었을 때 네 정책 값이 모두 정수여야 통과. 빈 문자열이면 기본 QoS로 재생(통과, 단 녹화 QoS는 없음).
  - 폴더 재생 = 폴더 info 통과 AND metadata.yaml QoS 문자열이 재생 규칙 통과.
  - 파일 재생 = 저장 파일 안의 QoS 문자열(sqlite3 `topics` 표 `offered_qos_profiles`, MCAP 채널 metadata `offered_qos_profiles`)이 재생 규칙 통과.

## research.md 기준 예측값 (실행 전)

| 항목 | 예측 |
|---|---|
| metadata `version` (4칸 모두, convert 후 포함) | 9 |
| `offered_qos_profiles` 노드 종류 | sequence(목록) |
| 정책 값 종류 | 이름 문자열(예: `reliable`, `transient_local`) |
| `type_description_hash` 키 | 있음 |
| `ros_distro` | jazzy |
| sqlite3 `schema` 표 `schema_version` / `ros_distro` | 4 / jazzy |
| sqlite3 `topics` 표 QoS 정책 값 | 이름 문자열 |
| Humble 폴더 info 규칙 통과 칸 수 | 0/4 |
| Humble 재생 규칙 통과 칸 수(폴더·파일) | 0/4 |
| 우회법 A(`offered_qos_profiles: ""`) 폴더 info 규칙 | 통과 |
| 우회법 A 후 `/tf_static`의 `transient_local` 정보 | 파일에서 사라짐 |
| 우회법 B(정수 문자열로 다시 적기) 폴더 info·재생 규칙 | 통과(NeonVector README 보고 기준) |
| 우회법 B 후 `transient_local` 정보 | 남음(정수 값) |
| 고친 metadata를 Jazzy `ros2 bag info`가 여는지 | 예측하지 않음(research.md에서 미확인 항목) |
| 저장 파일·metadata 바이트 | 예측하지 않음 |

## 무엇을 어떻게 재는가

1. **녹화(실제 Jazzy 녹화):** rclpy 노드가 `/chatter`(`std_msgs/msg/String`, 기본 QoS, 20개)와
   `/tf_static`(`tf2_ros.StaticTransformBroadcaster`, `transient_local`, 1개)을 발행한다.
   `ros2 bag record -s sqlite3`와 `ros2 bag record -s mcap`을 동시에 띄우고, 두 녹화기가 두 토픽을 모두 구독한 것을
   `get_subscription_count()`/`count_subscribers()`로 확인한 뒤 발행하고 SIGINT로 닫는다. 발견 대기 시간을 잰다.
2. **convert(저장 형식 반대로):** `ros2 bag convert -i <원본> -o out.yaml`.
   out.yaml = `output_bags: [{uri, storage_id: <반대 형식>, all_topics: true}]`.
   mcap 원본 → sqlite3, sqlite3 원본 → mcap. 걸린 시간과 입력·출력 저장 파일 바이트를 잰다.
   (Stack Exchange 답변이 말한 "MCAP → sqlite3 convert" 경로가 칸 3이다.)
3. **칸별 측정(4칸):** `metadata.yaml`을 `yaml.compose`로 읽어 `offered_qos_profiles`의 노드 종류(scalar/sequence)를 그대로
   본다. `version`, `ros_distro`, `type_description_hash` 보유 토픽 수, 토픽별 메시지 수, 첫 QoS 프로필의 네 정책 값,
   metadata·저장 파일 바이트를 기록한다. sqlite3 칸은 Python `sqlite3`로 표 수, `schema` 표의 `schema_version`·`ros_distro`,
   `topics` 표 QoS 문자열을 읽는다. MCAP 칸은 외부 파서 없이 파일 끝 Footer → Summary 영역의 Channel 레코드(opcode 0x04)를
   직접 풀어 채널 metadata 키와 `offered_qos_profiles` 문자열을 읽는다. 위 두 Humble 규칙을 적용해 칸별·토픽별 통과 여부와
   통과 칸 수를 센다.
4. **대조군:** 원본 mcap 폴더에 Jazzy `ros2 bag info`를 실행해 종료 코드를 기록한다.
5. **우회법(원본 mcap 폴더 복사본에 적용):** metadata.yaml에서 `offered_qos_profiles` 블록만 글자 단위로 교체하고 다른 줄은 그대로 둔다.
   - A: `offered_qos_profiles: ""` (issue #1895 유지보수자 제안)
   - B: 같은 QoS 목록을 rclpy 열거형(`HistoryPolicy` 등)의 정수 값으로 바꿔 YAML 문자열 하나로 적기
     (NeonVector 방식 중 QoS 표기 변경만 재현. 다른 키 삭제는 하지 않음)
   - 각각 Humble 규칙 통과 여부, `/tf_static`의 durability가 `transient_local`로 남는지, 바이트 수, 그리고 고친 폴더를
     **Jazzy** `ros2 bag info`가 여는지(종료 코드, 첫 오류 줄, 오류 줄 번호가 가리키는 metadata.yaml 줄)를 잰다.
6. 출력: JSON 줄(`env`, `record`, `convert`×2, `cell`×4, `jazzy_control`, `metadata_excerpt`, `workaround`×2, `summary`).
   숫자는 모두 실행 중에 만든 파일에서 읽는다. 한 번 실행은 약 8초다(시험 실행 기준).

## 측정이 아닌 것 (본문 measured 구간에 넣지 않는다)

- Humble에서의 실제 info/play 결과, 재생 시 실제 QoS(PR #2553 작성자의 외부 실행 결과로만 인용).
- 위 두 줄 이외의 Humble 디코더 차이(예: deadline 형식, sqlite3 schema 4 판독)는 판정하지 않았다. 우회법이
  "규칙 통과"여도 Humble에서 열린다는 실측이 아니다.
- ARM→x86, CDR 바이트 순서, 실제 로봇 하드웨어. 이 실험은 컨테이너 안 소프트웨어 실행뿐이다.

## 시행착오 (시험 실행에서 실제로 실패하거나 고친 점)

1. **우회법 적용 방식 변경(1차 시험 후):** 처음에는 PyYAML로 metadata.yaml 전체를 읽고 다시 써서 우회법을 적용했다.
   그러자 Jazzy `ros2 bag info`가 `bad conversion`으로 실패했는데, 파일 전체가 재포맷되어 원인이 QoS 필드인지 재포맷인지
   구분할 수 없었다. 그래서 `offered_qos_profiles` 블록만 글자 단위로 바꾸고 나머지 줄은 그대로 두는 방식으로 고쳤다.
2. **yaml-cpp 줄 번호 해석 오류(2차 시험):** 오류 메시지의 "line 14"를 0부터 센 번호로 처리해서, 오류가 `type_description_hash`
   줄을 가리킨다고 출력했다. yaml-cpp는 줄과 열을 1부터 세어 출력한다. 열 번호 31이 8칸 들여쓰기 + `offered_qos_profiles: `
   다음의 `""` 위치와 일치하는 것으로도 확인했다. 수정 후에는 오류가 `offered_qos_profiles: ""` 줄을 가리킨다.
3. **출력 잘림(2차 시험):** 칸별 JSON이 길어서 전체 stdout이 하네스 보존 한도(마지막 8000자)를 넘었고, 앞쪽 `env` 줄이
   잘렸다. 칸 출력을 압축(정책 값을 한 줄 문자열로, 중복 필드 제거)해 약 6.7천 자로 줄였다.
4. **KeyError(3차 시험, 종료 코드 1):** 칸 출력의 키를 `metadata_version`에서 `version`으로 바꾸면서 summary 코드가 옛 키를
   찾아 실패했다. summary를 고쳤다.
5. **불필요한 설정 제거:** 처음에는 `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`를 `setdefault`로 넣었다. 그런데 1차 출력에서
   값이 `SUBNET`으로 나왔다. 컨테이너 환경에 이미 값이 있어서 이 줄이 아무 효과도 없었던 것이다. 그래서 줄을 지웠고,
   기본값(`SUBNET`, `--network none`)으로도 두 녹화기의 토픽 발견이 4초 안에 끝났다.
