# 실험 계획: colcon의 `--executor sequential`은 무엇을 줄이고, 그 대가로 시간이 얼마나 느는가

## 질문

1. `colcon build --executor sequential`(그리고 `--parallel-workers 1`)은 **동시에 빌드하는 패키지 수**만 줄이는가,
   아니면 패키지 안의 컴파일러 동시 실행 수(`make -jN`)도 줄이는가? `MAKEFLAGS="-j1"`을 더하면 무엇이 바뀌는가?
2. 동시 작업 수를 줄이면 벽시계 시간은 얼마나 느는가? 패키지가 일렬로 의존하면 그 손해가 사라지는가?
   컴파일이 CPU를 이미 다 쓰는 경우에도 병렬이 이득인가?
3. `/usr/bin/time`이 보여 주는 최대 RSS(= `getrusage(RUSAGE_CHILDREN).ru_maxrss`)는 동시에 돈 작업들의
   메모리 **합계**인가, **가장 큰 단일 프로세스** 값인가?

## research.md 기준 예측값

research.md의 코드 근거(colcon-parallel-executor `parallel.py`, colcon-cmake `build.py`, colcon-core
`sequential.py`, getrusage(2))에서 나온 예측이다. 실험 전 값이며 실측이 아니다.

- 동시 작업 슬롯 상한 = (동시 패키지 수 w) × (패키지당 make 작업 수 j). w와 j의 기본값은 모두 CPU 수
  (`os.cpu_count()`와 affinity 개수의 최솟값). 이 컨테이너는 하네스가 `--cpus 1`(CFS 할당량)을 주지만
  affinity는 바꾸지 않으므로, colcon은 호스트 CPU 수 2를 그대로 볼 것으로 예측한다.
  | 조건 | w | j | 예측 상한(동시 컴파일) | 예측 동시 패키지 |
  | --- | --- | --- | --- | --- |
  | 기본 `colcon build` | 2 | 2 | 4 | 2 |
  | `--executor sequential` | 1 | 2 | 2 | 1 |
  | `--executor sequential` + `MAKEFLAGS=-j1` | 1 | 1 | 1 | 1 |
  | `--parallel-workers 1` | 1 | 2 | 2 | 1 |
  | 4코어 기본값 재현(`--parallel-workers 4` + `MAKEFLAGS="-j4 -l4"`) | 4 | 4 | 16 | 4 |
  colcon이 붙이는 make 인자는 MAKEFLAGS가 없을 때 `-j2 -l2`, MAKEFLAGS에 `-j`가 있으면 없음.
  `-l`은 부하 기준의 부드러운 제동이라 실제 동시 개수는 상한보다 작을 수 있다.
- 시간(컴파일 단계만의 이론 하한, 부하가 대기일 때). 패키지당 C 파일 4개, 파일 한 개의 부하는
  research.md 교육 예제의 패키지 시간 30/40/50/60초를 200분의 1로 줄인 0.15/0.2/0.25/0.3초.
  - sequential(j=2): 패키지마다 2라운드 → 2 × (0.15+0.2+0.25+0.3) = 1.8초
  - sequential + `-j1`: 4 × 0.9 = 3.6초
  - 기본(w=2, j=2): max(전체 작업 3.6 ÷ 슬롯 4, 가장 긴 패키지 2 × 0.3) = 0.9초
  - 4코어 재현(w=4, j=4): max(3.6 ÷ 16, 0.3) = 0.3초
  - research.md는 "순차 대비 병렬 3배"가 패키지 시간이 동시성과 무관하다는 가정의 **상한**이며,
    고정 오버헤드·CPU 경쟁 때문에 실제 차이는 더 작다고 예측한다. colcon 자체의 패키지별 고정 비용은
    research.md에 수치가 없으므로 벽시계 시간 비율은 위 하한 비율보다 작을 것이라는 방향만 예측한다.
  - 일렬 의존(p30→p40→p50→p60): 기본 parallel executor도 ready 패키지가 하나뿐이라 동시 패키지 1,
    sequential과 벽시계 시간이 거의 같다(손해 0).
  - 부하를 CPU 소모로 바꾼 경우(1 CPU 할당량): 병렬로 돌려도 CPU 총량이 늘지 않으므로 기본과
    sequential의 시간 차이가 거의 없거나 병렬이 더 느릴 수 있다.
- 메모리: `ru_maxrss`는 가장 큰 단일 자손 프로세스의 값이라 조건과 관계없이 거의 같고, 동시에 살아 있는
  컴파일 작업의 RSS 합계는 동시 작업 수에 비례해 커질 것이다(기본 → 4코어 재현에서 약 4배).

## 무엇을 어떻게 재는가

- 환경: 하네스의 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, `--cpus 1`, `--memory 1g`). 이미지에 들어 있는
  실제 colcon·CMake·GNU make·gcc만 쓴다. rclpy 노드는 쓰지 않는다(질문이 빌드 도구이기 때문).
- 작업공간: `/tmp/colcon_exp` 아래 두 개.
  - `indep`: 서로 독립인 CMake 패키지 4개(p30, p40, p50, p60, `build_type` cmake), 각 C 파일 4개.
  - `chain`: 같은 패키지를 package.xml `<depend>`로 p30→p40→p50→p60 일렬 의존시킨 것.
- 컴파일 감시: 각 패키지의 CMakeLists.txt가 `CMAKE_C_COMPILER_LAUNCHER`로 런처(`launch.py`)를 지정한다.
  런처는 컴파일 한 건마다 (1) 16 MiB 밸러스트 메모리를 실제로 써서 잡고, (2) 패키지별 부하 시간만큼
  대기(또는 CPU 소모)한 뒤, (3) 진짜 gcc를 실행하고, 시작·종료 시각(`time.monotonic`), 종료 코드,
  자기 최대 RSS(`VmHWM`)를 JSON 줄로 기록한다. 밸러스트와 부하 시간은 "무거운 C++ 파일 한 개"를 흉내 낸
  입력 조건이며 측정값이 아니다. 실제 C 파일은 아주 작다.
- 조건마다: 모든 `.c`의 수정 시각을 갱신(소스 수정 흉내) → `colcon build`를 다시 실행. 첫 빌드(CMake
  configure 포함)는 워밍업으로 기록만 하고 비교에서 뺀다. 조건 순서: default, sequential,
  sequential_makeflags_j1, parallel_workers_1, quad_core_defaults, chain_default, chain_sequential,
  cpu_default, cpu_sequential(CPU 소모 조건은 60초 한도 때문에 부하 0.5배).
- 측정 항목(모두 실행 중 측정):
  - `wall_s`: colcon build 한 번의 벽시계 시간.
  - `max_concurrent_jobs` / `max_concurrent_packages`: 런처 구간 기록을 겹쳐 센 동시 컴파일 수와 동시에
    컴파일 중이던 패키지 수의 최댓값. `sampled_peak_launchers`는 /proc 표본(20 ms)으로 본 같은 값의 교차 확인.
  - `colcon_added_make_args`: `log/latest_build/<pkg>/command.log`에서 읽은, colcon-cmake가 실제로 붙인
    `cmake --build ... -- -jN -lN` 인자.
  - `finished_s` / `sum_finished_s`: colcon 콘솔의 `Finished <<< 패키지 [시간]` 값과 그 합(순차 시간 근사치가
    병렬 실행에서 얼마나 부풀려지는지 확인).
  - `sampled_peak_launcher_rss_sum_mib`: 같은 순간 살아 있던 런처 프로세스 RSS 합의 최댓값(동시 메모리 압박).
    `sampled_peak_all_rss_sum_mib`: 컨테이너 안 모든 프로세스 RSS 합의 최댓값(공유 페이지 중복 포함).
  - `sampled_max_single_rss_mib` / `sampled_max_single_proc`: 표본에서 본 가장 큰 단일 프로세스와 그 이름.
  - `ru_maxrss_children_mib`: colcon을 자식으로 실행한 래퍼가 끝난 뒤 읽은 `getrusage(RUSAGE_CHILDREN).ru_maxrss`
    (`/usr/bin/time -v`의 "Maximum resident set size"와 같은 원천). `max_job_vmhwm_mib`: 런처 한 개의 최대 RSS.
  - `loadavg1_before`: 조건 시작 직전 1분 load average(make `-l`이 보는 값, 호스트와 공유).
  - 환경 줄: `os.cpu_count()`, affinity 개수, cgroup `cpu.max`, colcon·cmake·make·gcc 패키지 버전.
- 판정:
  - 질문 1: sequential·parallel_workers_1에서 동시 패키지 1인데 동시 컴파일이 2이고 colcon이 `-j2 -l2`를
    붙였다면 "sequential은 바깥만 줄인다"가 확인된다. MAKEFLAGS=-j1에서 동시 컴파일 1, 붙인 인자 없음이면
    안쪽 축소가 확인된다.
  - 질문 2: default·sequential·sequential_j1·quad의 `wall_s` 비교, chain 두 조건의 `wall_s` 차이,
    cpu 두 조건의 `wall_s` 비교.
  - 질문 3: `ru_maxrss_children_mib`가 `sampled_max_single_rss_mib`와 같고 조건 간 거의 변하지 않는데
    `sampled_peak_launcher_rss_sum_mib`는 동시 작업 수에 따라 커지면 "ru_maxrss는 합계가 아니다"가 확인된다.
- 한계: 부하는 대기·CPU 소모로 만든 모형이며 실제 C++ 컴파일러의 메모리·시간이 아니다. 1 CPU 할당량,
  호스트 CPU 2개 환경이며 Raspberry Pi 실물이 아니다. 4코어 기본값은 같은 인자를 명시해 재현했을 뿐
  4코어 장비에서 잰 것이 아니다. make `-l`은 컨테이너 밖 호스트 부하에도 영향을 받는다. RSS 합계는
  공유 라이브러리 페이지를 중복해서 센다. Ninja 생성기와 ament_python 패키지는 다루지 않는다.

## 시행착오

- 호스트 CPU가 2개뿐이라 `taskset`으로 4코어 보드를 흉내 낼 수 없었다. 대신 4코어에서 colcon이 쓸 기본값
  (`--parallel-workers 4`, make `-j4 -l4`)을 명시한 조건(quad_core_defaults)으로 바꿨다.
- 첫 시험 실행: 모든 조건이 성공했지만 /proc 표본기가 pid별 cmdline을 캐시해, 런처가 gcc를 띄우려고
  fork한 직후(exec 전) 부모 cmdline을 물려받은 자식까지 런처로 셌다. 그래서 quad_core_defaults에서 표본상
  런처 수가 실제 컴파일 작업 수보다 1개 많게 나왔고 RSS 합계도 부풀 수 있었다. 캐시를 없애고 매 표본마다
  `/proc/<pid>/stat`의 부모 pid를 읽어 "부모도 런처인 프로세스"를 제외하도록 고쳤다. 두 번째 시험 실행에서
  표본 런처 수와 구간 기록 동시 작업 수가 일치했다.
- 첫 시험 실행의 구간 기록 기준 동시 작업 수는 quad_core_defaults에서 예측 상한보다 1 작았고 두 번째에는
  상한과 같았다. make `-l4`와 시작 타이밍 때문에 실행마다 달라질 수 있는 값으로 본다.
- 첫 시험 실행 전체 시간이 60초 한도에 가까워 CPU 소모 조건의 부하를 0.5배로 줄였다(`CPU_HOLD_SCALE`).
- 이미지의 colcon-parallel-executor는 0.3.0(research.md가 읽은 소스는 0.4.0/master)이다. 환경 줄에 버전을
  기록하고, 기본 작업자 수는 실측 동시 패키지 수로 확인한다.
