# 실험 계획: ros2 bag record에 -b와 -d를 함께 주면 어느 쪽이 먼저 자르는가

## 질문

1. 같은 `-b 8000000 -d 6` 설정에서 데이터율만 다르면 정말 `T_size = B / R`과 `D`의 대소대로
   다른 기준이 분할을 결정하는가? 몇 초마다, 몇 개 파일로 나뉘는가?
2. 크기 기준으로 닫힌 파일은 `-b`보다 얼마나 커지는가?
3. 녹화 시작 전에 한 번만 발행한 `/tf_static`(transient local)은 분할된 뒤의 파일에도 남는가?
4. 저장 플러그인별 `-b` 하한(MCAP 1024, sqlite3 86016)은 Jazzy에서 실제로 그 값인가?
   Jazzy CLI에 `--repeat-transient-local`이 있는가?

## research.md 기준 예측값

- 판정식: `T_size = B / R`. `T_size < D`이면 크기, `T_size > D`이면 시간이 먼저 자른다(OR 판정).
- high(200,000 B 페이로드 × 20 Hz): 직렬화 크기 약 200,016 B → R ≈ 4,000,320 B/s →
  T_size ≈ 2.0 s < D = 6 s → **크기 기준**. 9초 녹화면 약 2초마다 분할, 닫힌 파일 4개 + 마지막 파일 1개.
- low(1,000 B 페이로드 × 50 Hz): 직렬화 크기 약 1,016 B → R ≈ 50,800 B/s →
  T_size ≈ 157.5 s > 6 s → **시간 기준**. 시간 비교가 `>`이고 메시지 도착 시 판정하므로
  분할 간격은 6초 직후 첫 메시지(최대 20 ms 늦음). 14초 녹화면 닫힌 파일 2개 + 마지막 파일 1개.
- 크기 기준으로 닫힌 파일은 `-b` 이상. 초과분은 메시지 하나(약 200,016 B) + 저장 형식 오버헤드 수준,
  Jazzy는 캐시 미반영이라 이론상 상한은 기본 캐시 크기 104,857,600 B까지.
- `/tf_static`은 첫 파일에만 1개 있고 이후 파일에는 0개.
- 하한: mcap 1023 거부 / 1024 허용, sqlite3 86015 거부 / 86016 허용(검사식이 `<`).
- Jazzy `ros2 bag record --help`에는 `--repeat-transient-local`과 `--max-bag-files`가 없다.

## 무엇을 어떻게 재는가

환경: 하네스의 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB, `/tmp`는 tmpfs).
기본 저장 형식 `mcap`, 기본 캐시(`--max-cache-size` 미지정), 기본 RMW.

1. 하한 검사: `rosbag2_py.SequentialWriter.open()`에 `max_bagfile_size`를 1023/1024(mcap),
   86015/86016(sqlite3)으로 넣고 예외 여부와 오류 문구를 기록한다.
2. CLI 옵션 검사: `ros2 bag record --help` 출력에 옵션 문자열이 있는지 확인한다.
3. 녹화: 같은 rclpy 노드가 `tf2_ros.StaticTransformBroadcaster`로 `/tf_static`을 한 번 발행한 뒤,
   시나리오마다 실제 `ros2 bag record -o ... -s mcap -b 8000000 -d 6 <data 토픽> /tf_static`을
   하위 프로세스로 띄운다. 녹화기가 data 토픽을 구독한 것을 확인하고 0.5초 기다린 다음
   `std_msgs/UInt8MultiArray`를 단조 시계 기준 일정 주기로 발행한다. 끝나면 SIGINT(Ctrl+C와 같음)로 멈춘다.
4. 측정(모두 실행 중 계산):
   - 데이터율 R = 직렬화 크기(`rclpy.serialization.serialize_message`) × 실제 발행 수 / 실제 발행 시간
   - `metadata.yaml`의 파일별 `starting_time`으로 분할 간격, 디스크 파일 크기와 `-b`의 차이
   - 분할 파일 하나씩 `rosbag2_py.SequentialReader`로 열어 토픽별 메시지 수(`/tf_static` 포함),
     파일 시작에서 첫 data 메시지까지의 시간
   - 닫힌 파일마다 "크기 ≥ B"와 "간격 > D" 중 어느 쪽이 참인지로 실제 분할 기준을 판정해
     예측(`T_size`와 `D` 비교)과 나란히 출력
   - 발행 수와 녹화된 data 메시지 수(손실 여부)
5. 마지막 파일은 SIGINT로 닫혔으므로 분할 기준 판정과 크기 초과 계산에서 뺀다.

## 해석할 때의 한계

- `/tmp`는 메모리 기반 tmpfs라 디스크 쓰기가 매우 빠르다. 느린 디스크에서는 Jazzy의 캐시 미반영 때문에
  파일이 더 크게 넘칠 수 있으며, 이 실험은 그 상한을 재지 않는다.
- 첫 파일의 시작 시각은 첫 메시지(여기서는 먼저 들어온 `/tf_static`) 기준이라 첫 분할 간격만
  data 발행 전 대기 시간만큼 길어진다.
- 실물 센서·로봇이 아니라 같은 컨테이너 안의 합성 토픽이다. 압축은 쓰지 않았다.

## 시행착오

- 첫 시험 실행은 실패 없이 끝났다. 다만 두 시나리오 모두 첫 분할 간격만 나머지보다 길게 나왔다.
  원인을 확인하려고 파일별 "파일 시작 → 첫 data 메시지" 시간(`first_data_after_file_start_s`)을
  출력에 추가했고, 두 번째 시험 실행에서 첫 파일의 시작 시각이 data보다 먼저 녹화된 `/tf_static`의
  수신 시각이라는 것을 확인했다. 분할 판정 코드에는 손대지 않았다.
- `ROS_AUTOMATIC_DISCOVERY_RANGE` 같은 탐색 설정 없이도 네트워크 없는 컨테이너에서 같은 호스트 내
  발행자·녹화기 탐색이 됐으므로 기본값을 그대로 두었다.
