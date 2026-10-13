# 경쟁 글 대비 차별점: ros2-bag-record-split-size-duration-whichever-first

검색어 `ros2 bag record split size duration`, `ros2 bag record 분할 max-bag-size`, `"ros2 bag record" "max-bag-size" 블로그`, `ros2 bag record 용량 파일 나누기 -b -d 옵션 rosbag2`로 검색하고 아래 글을 직접 열어 확인했다(2026-10-14). 한국어 결과에는 ROS 2 분할을 다루는 글을 찾지 못했다.

1. https://github.com/ros2/rosbag2 (README, 공식) — 다루는 것: `-b`, `-d` 예시, "whichever threshold is reached first", "must be greater than 86016", `--repeat-transient-local`(rolling README). 빠지거나 부정확한 것: 86016은 sqlite3 하한인데 저장 형식 구분 없이 적혀 있다(기본 MCAP 하한은 1024). 코드상 하한과 같은 값은 허용된다. 데이터율로 어느 기준이 먼저 닿는지 계산하는 방법, 캐시로 인한 크기 초과, `--repeat-transient-local`이 어느 배포판부터인지 없다. 이 글이 더할 것: 판정식·설명용 산술 예제, 저장 형식·배포판별 차이를 소스 줄 링크로 제시.
2. https://fictionlab.pl/blog/recording-and-replaying-field-data-with-ros-2-bags-a-research-workflow/ (Fictionlab, 2026-07-02, Humble·Jazzy·Kilted/Rolling 언급) — 다루는 것: `--max-bag-size 1073741824`/`2147483648`로 청크 분할하면 크래시 시 열려 있던 청크만 잃는다는 운용 이유, `--max-bag-duration 300`, MCAP+zstd. 빠진 것: 둘을 함께 줄 때의 우선순위, 데이터율 계산, 분할 파일의 `/tf_static`, 하한·캐시. 참고: 이 글의 "2 GB"는 2³¹ B(2 GiB)다. 이 글이 더할 것: 값을 고르는 계산 절차와 단위(GiB/GB, `ros2 topic bw` MB=10⁶) 정리.
3. https://docs.theairlab.org/main/docs/robot/logging/rosbags/ (AirStack, Jazzy, 날짜 표시 없음) — 다루는 것: 설정 파일 `args`에 `-b 4000000000`(약 4 GB) 예시, `--max-cache-size` 언급. 빠진 것: `-d`, 우선순위, 데이터율, latched 메시지, 저장 형식. 이 글이 더할 것: 4 GB 같은 값이 실제로 몇 초 분량인지 데이터율로 환산하는 방법과 캐시 초과 위험.
4. https://manual.ro47003.me.tudelft.nl/6_common_tools/rosbags.html (TU Delft 실습 매뉴얼) — 다루는 것: `-b` 도움말 문구, turtlesim 녹화 예시. 빠진 것: `-d`, 함께 쓸 때 동작, latched, 하한. 본문에 기본 저장 형식을 sqlite3로 적고 예시 출력에는 mcap이 보이는 불일치가 있다(Jazzy 이후 기본은 mcap). 이 글이 더할 것: 배포판별 기본 저장 형식과 그에 따른 하한 차이.
5. https://discourse.openrobotics.org/t/rosbag2-composable-record-splitting-files/50360 (Open Robotics Discourse, 2025-10-01 답변) — 다루는 것: composable recorder에서 `storage.max_bagfile_size` 파라미터로 분할 설정. 빠진 것: duration, 우선순위, latched. 이 글이 더할 것: CLI 기준 판정 규칙과 계산(파라미터 이름 대응은 짧게 언급 가능).
6. https://winterbloooom.github.io/rosbag/ (한국어, 2022-05-22) — ROS 1 rosbag 기본 명령만 다루며 분할 설명이 없다. 한국어 ROS 2 분할 해설 공백을 보여 주는 참고로만 기록.

실측으로 더할 것: 없음. 이 글은 rosbag2를 실행한 측정을 더하지 않는다. 더하는 것은 산술 검산한 판정 예제와 커밋 고정 소스·이슈/PR 대조로 확인한 배포판·저장 형식별 동작 차이이며, foundation_concept 계약(1차 자료 + 자체 예제 + 검산)의 범위다. 이 두 가지는 위 경쟁 글 어디에도 없으므로 INSUFFICIENT 사유에 해당하지 않는다고 판단했다.
