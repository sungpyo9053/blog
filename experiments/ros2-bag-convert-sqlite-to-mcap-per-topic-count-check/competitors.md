# 경쟁 글 대비 차별점: ros2-bag-convert-sqlite-to-mcap-per-topic-count-check

1. https://api.stackexchange.com/2.3/questions/104976/answers?site=robotics&filter=withbody&sort=votes (Robotics Stack Exchange 질문 104976의 답변. HTML 페이지는 이 runner에서 403이라 같은 원문을 공식 API로 읽었다)
   - 다루는 것: Foxglove `mcap convert` 빌드·사용, `ros2 bag convert` + `output_bags: - uri, storage_id: mcap, all: true`, `mcap info`로 총 messages 확인. Iron에서 알 수 없는 타입 토픽이 경고 후 빠진 사례, 압축 키 차이.
   - 빠졌거나 틀린 것: 검증이 `mcap info`의 **총 messages** 한 줄이다("모든 메시지가 있는지 본다"). 토픽별 대조가 없다. 본인이 토픽이 빠지는 사례를 보고했는데도 그 토픽이 빠졌는지 수로 확인하는 절차가 없다. 출력 경로를 명령줄로 못 준다는 점은 맞지만 Jazzy·Humble 키 차이는 언급하지 않는다.
   - 이 글이 더할 것: Jazzy 컨테이너에서 변환 전후 `ros2 bag info`의 토픽별 Count를 측정해 차이·손실 비율 표로 판정하고, 토픽 선택 누락·숨김 토픽처럼 총합으로는 덜 드러나는 누락을 실측으로 보여 준다.
2. https://mcap.dev/guides/getting-started/ros-2 (MCAP 공식 가이드, Foxglove)
   - 다루는 것: `ros2 bag convert -i ros2_input.db3 -o convert.yaml`, `all: true`, 압축은 `storage_config_uri`로 지정하고 `compression_mode`/`compression_format`을 쓰면 "재생할 수 없는 bag"이 된다는 경고(issue #1920 링크), `mcap convert`와 Iron 이전 bag의 메시지 정의 문제.
   - 빠졌거나 틀린 것: 변환 뒤 토픽·메시지 수 확인 단계가 없다. `all: true`가 왜 필요한지(없으면 빈 bag)를 설명하지 않는다. "unplayable"은 링크된 issue #1920 본문(Humble에서 재생 전에 전체 파일을 먼저 푸는 문제)보다 강한 표현이다.
   - 이 글이 더할 것: 토픽 선택 키를 뺐을 때와 넣었을 때의 토픽별 Count를 같은 입력으로 실측 비교하고, 압축 키 선택의 근거를 rosbag2 README 문장(색인 가능 여부)으로 좁혀 설명한다.
3. https://jonasotto.com/posts/ros_bag_convert/ (Jonas Otto, 2024-05-20, ROS 2 Jazzy)
   - 다루는 것: `all_topics: true`가 없으면 출력에 데이터가 없다는 경고, 시간 자르기(`start_time_ns`/`end_time_ns`), 시간 기준 분할, 특정 토픽 추출. `ros2 bag info` 출력을 전후로 보여 준다.
   - 빠졌거나 틀린 것: 입력이 이미 MCAP인 단일 토픽(`/chatter`) bag이다. sqlite3→MCAP 변환과 다중 토픽 대조가 없다. 숨김 토픽 제외, 배포판 차이도 없다.
   - 이 글이 더할 것: sqlite3 입력에서 출발해 서로 다른 주기의 토픽 3개 이상으로 토픽별 표를 만들고, 총합과 토픽별 판정이 갈리는 지점을 실측과 산술로 보여 준다.
4. https://merklebot.com/blog/ros2-data-logging-rosbag2-mcap-pipeline.html (MerkleBot Engineering, 2026-09-22)
   - 다루는 것: 플릿 규모 로깅 파이프라인의 한 단락으로 레거시 sqlite3→MCAP 변환 YAML(`storage_preset_profile: zstd_small`, `max_bagfile_duration: 300`, `all_topics: true  # use "all: true" on Humble`). 다른 단락에서 MCAP summary의 채널별 메시지 수를 읽는 Python 코드를 보여 준다.
   - 빠졌거나 틀린 것: 변환 전후 토픽별 비교 절차가 없다. 채널별 수 읽기는 추출 파이프라인용이지 변환 검증용이 아니다. 숨김 토픽과 서비스 이벤트(`all_services`)는 언급하지 않는다.
   - 이 글이 더할 것: 변환 전(sqlite3)과 후(MCAP)를 같은 `ros2 bag info` 명령으로 토픽별로 맞추고, 모든 토픽의 차이가 0일 때만 통과로 보는 재사용 가능한 판정 절차를 준다.
5. https://brunob81hk.github.io/ros2_cookbook/other/pages/bag.html (ROS 2 Cookbook 미러)
   - 다루는 것: ROS 1 bag을 `rosbags`로 sqlite3로 바꾼 뒤 `ros2 bag convert` + `all: true` + `compression_mode: file`, `compression_format: zstd`로 `.mcap.zstd`를 만드는 예.
   - 빠졌거나 틀린 것: rosbag2 README가 색인 가능하지 않다고 적은 rosbag2 파일 압축을 권하는 셈이다. 변환 전후 토픽별 수 대조가 없다.
   - 이 글이 더할 것: 압축은 MCAP `storage_preset_profile`로 고르는 근거를 README로 제시하고, 변환 결과를 토픽별 Count로 판정한다.
6. https://velog.io/@jk01019/ros2-bah (한국어 velog)
   - 다루는 것: rosbag2_py `SequentialWriter`/`SequentialReader`로 sqlite3 bag 쓰기·특정 토픽 읽기.
   - 빠졌거나 틀린 것: `ros2 bag convert`, MCAP 변환, 변환 검증을 다루지 않는다. 한국어 검색에서 이 질문에 직접 답하는 글을 찾지 못했다는 근거다.
   - 이 글이 더할 것: 한국어로 Jazzy 기준 변환 명령, YAML 키의 의미, 토픽별 검증 절차를 한 글에 묶는다.

판정: 더할 것이 있다(토픽별 판정 절차, 소스 근거, 실측 예정). INSUFFICIENT 아님.
