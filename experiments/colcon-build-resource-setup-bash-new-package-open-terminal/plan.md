# 실험 계획: 빌드 전에 source한 터미널은 colcon build 뒤 새 패키지를 보는가 (기본 설치 vs `--merge-install`)

## 질문

글의 핵심 질문은 "이미 열어 둔 터미널에서 `colcon build`를 할 때마다 다시 source해야 하는가, 아니면 새 패키지를 추가했을 때만 하면 되는가"다.
이 실험은 research.md의 "Experiment Agent용 측정 설계 제안"을 한 번의 실행으로 확인한다.

- Q1 기존 패키지 파일만 고쳐 다른 터미널에서 다시 빌드하면, 빌드 전에 source한 터미널 T는 다시 source하지 않고도 바뀐 결과를 실행하는가? 패키지 수와 `AMENT_PREFIX_PATH` 항목 수는 그대로인가?
- Q2 새 패키지를 추가해 빌드하면, T는 다시 source하지 않고도 `ros2 pkg list`·`ros2 pkg prefix`·`ros2 run`에서 그 패키지를 찾는가? 기본(isolated) 설치와 merged 설치에서 결과가 다른가?
- Q3 T에서 다시 source하면 무엇이 늘고, 같은 경로가 중복으로 쌓이는가?

## research.md 기준 예측값

소스 코드 읽기에서 나온 예측이다(research.md "핵심 요약", "측정 설계 제안", 소스 2·3·4·8번).

- underlay(`/opt/ros/jazzy`)만 source했을 때 `AMENT_PREFIX_PATH`의 underlay 항목: 1 (example.py 가정, 실측으로 확인할 값)
- 기본 설치(가설 A)
  - T가 source한 직후: overlay 패키지(probe_*) 3, overlay 경로 항목 3 (= 1 + 3 = 4 중 overlay 몫)
  - 기존 패키지만 고쳐 다시 빌드한 뒤(다시 source 없음): 3, 항목 3. 바뀐 출력이 그대로 보임(공식 Creating-A-Workspace 7단계와 같은 흐름)
  - 새 패키지 빌드 직후(다시 source 없음): T가 보는 overlay 패키지 3 (디스크에는 색인 파일 4), `ros2 pkg prefix probe_d` 실패(`Package not found`), 보는 비율 3/4 = 0.75
  - 같은 T에서 다시 source한 뒤: 4, 항목 +1(= 4), 중복 0, 비율 4/4 = 1
- merged 설치(가설 B)
  - source 직후 3 / 고쳐 다시 빌드한 뒤 3 / 새 패키지 빌드 직후(다시 source 없음) 4 / 다시 source한 뒤 4
  - overlay 경로 항목은 네 시점 모두 1 (merged 예상 항목 수 1 + 1 = 2)
  - 새 패키지 `ros2 run`: research.md 소스 8번의 추론대로, 기존 ament_python 패키지 때문에 merged `install/lib/python3.12/site-packages`가 이미 PYTHONPATH에 있으므로 다시 source하지 않아도 성공할 것으로 예측한다(research.md는 이 항목을 미측정 추론으로 남겼다).
- 기본 설치에서 다시 source하기 전 새 패키지 `ros2 run`: research.md에 직접 예측은 없다. `ros2 pkg prefix`와 같은 이유로 실패할 것으로 예측한다.

## 환경

- 하네스 이미지 `ros:jazzy-ros-base`, 네트워크 없음, 1 CPU·1 GiB. 실제 이미지 다이제스트와 rclpy 버전은 results.json의 `environment`에 하네스가 기록한다.
- 스크립트는 첫 줄(`event: env`)에 실행 중 `dpkg-query`로 읽은 colcon-core·colcon-ros·ros2pkg·ament_index_python 버전과, `/proc/mounts`에서 읽은 `/`와 `/tmp`의 파일시스템 종류·`noexec` 여부를 남긴다.
- 쓰는 도구는 `ros2 pkg create`, `colcon build`, `ros2 pkg list`, `ros2 pkg prefix`, `ros2 run`, bash, Python 표준 라이브러리뿐이다. 외부 패키지 설치나 네트워크 접근이 없다.
- 작업공간은 컨테이너 자체 파일시스템의 `/var/tmp/source_lab` 아래에 매 실행 새로 만든다(이유는 시행착오 1번). 컨테이너는 `--rm`이라 실행 뒤 사라진다. 로봇·시뮬레이터·하드웨어는 쓰지 않는다.

## 무엇을 어떻게 재는가

준비: `ros2 pkg create --build-type ament_python --license Apache-2.0 --node-name <pkg>_node <pkg>`로 `probe_a`~`probe_d` 4개 패키지 원본을 한 번 만든다. 각 노드는 `Hi from <pkg>. edit=<번호>` 한 줄을 출력하도록 print 줄만 바꾼다.

작업공간 2개를 만든다. 같은 `install/`에서 레이아웃을 바꾸면 colcon이 오류로 멈추기 때문이다(research.md 소스 6번).

1. `ws_iso`: 기본 설치 `colcon build`
2. `ws_mrg`: `colcon build --merge-install`

두 종류의 셸을 구분한다.

- 빌드 셸: 매번 새로 띄우는 `bash --noprofile --norc`. 깨끗한 환경(`HOME`, `PATH`, `LANG`, `ROS_LOG_DIR`만)에서 underlay만 source한 뒤 `colcon build`를 실행한다. 공식 권고처럼 overlay가 source된 터미널에서 빌드하지 않는다.
- 터미널 T("빌드 전에 연 터미널"): 실험 내내 살아 있는 `bash` 프로세스 하나다. 같은 깨끗한 환경에서 시작해 `source /opt/ros/jazzy/setup.bash`와 `source <ws>/install/setup.bash`를 차례로 실행한다. 이후 명령은 같은 프로세스에 차례로 보내므로 환경변수가 명령 사이에 유지된다. 빌드 셸과는 부모·자식 관계가 아니어서 빌드 셸의 환경을 물려받지 않는다.

레이아웃마다 순서:

1. 빌드 셸: `probe_a`·`probe_b`·`probe_c` 첫 빌드. `install/.colcon_install_layout` 내용을 기록한다.
2. T: source 2회 → 관측 `T_sourced_before_any_rebuild`
3. 대조군: `probe_a` 노드의 print 줄을 `edit=2`로 고침 → 빌드 셸: `colcon build [--merge-install] --packages-select probe_a` → T: 다시 source 없이 관측 `after_edit_rebuild_no_resource`
4. 새 패키지: `probe_d`를 `src/`에 복사 → 빌드 셸: `colcon build [--merge-install] --packages-select probe_d` → T: 다시 source 없이 관측 `after_new_pkg_build_no_resource`
5. T: `source <ws>/install/setup.bash` 한 번 더 → 관측 `after_resource_same_terminal`

관측 한 번에 T 안에서 실행해 그대로 세는 값(모두 실행 중 측정, JSON 한 줄):

- `pkg_total`: `ros2 pkg list` 출력 줄 수(underlay 포함 전체)
- `probe_count`, `probe_pkgs`: 그중 `probe_`로 시작하는 이름(overlay 패키지)
- `probe_index_files_on_disk`: T와 무관하게 디스크의 `install/**/share/ament_index/resource_index/packages/probe_*` 파일 수. "디스크에는 있지만 T가 못 보는" 상태를 구분하는 대조값
- `ament_prefix_entries`, `overlay_entries`, `underlay_entries`, `duplicate_entries`, `overlay_entry_paths`: T의 `$AMENT_PREFIX_PATH`를 `:`로 나눈 항목 수, 작업공간 경로로 시작하는 항목 수, `/opt/ros/`로 시작하는 항목 수, 중복 항목 수, overlay 항목의 작업공간 기준 상대 경로
- 2·3단계: `ros2 run probe_a probe_a_node`의 종료 코드와 출력(`edit=1` → `edit=2`로 바뀌었는지)
- 4·5단계: `ros2 pkg prefix probe_d`와 `ros2 run probe_d probe_d_node`의 종료 코드와 출력
- 각 빌드의 종료 코드와 벽시계 시간(`time.monotonic()` 차이, 초), 관측 한 번에 걸린 시간

마지막 줄 `event: summary`에 레이아웃·시점별 핵심 값과 실패 목록, 전체 실행 시간을 모은다.

판정 기준:

- 가설 A 확인(기본 설치): 4단계에서 `probe_index_files_on_disk`는 4인데 `probe_count`가 3이고 `prefix_probe_d_exit`가 0이 아니며, 5단계에서 `probe_count` 4, `overlay_entries` +1, `duplicate_entries` 0이면 일치.
- 가설 B 확인(merged): 4단계에서 다시 source 없이 `probe_count` 4, `prefix_probe_d_exit` 0이고, 네 시점 모두 `overlay_entries` 1이면 일치.
- 대조군 확인: 3단계에서 두 레이아웃 모두 `probe_count`·`overlay_entries`가 2단계와 같고 `run_probe_a_output`이 `edit=2`로 바뀌면 "기존 패키지 수정 재빌드는 다시 source가 필요 없다"와 일치.
- 실패 판정: 패키지 생성이나 `colcon build`가 0이 아닌 코드로 끝나면 `error` 줄을 내고 `failures`에 남긴 뒤 종료 코드 1로 끝난다. 이 경우 측정값을 글에 쓰지 않는다. `ros2 pkg prefix`·`ros2 run`의 실패는 측정 대상이므로 스크립트 실패로 치지 않는다.

## 해석상 한계

- 최소 ament_python 패키지(노드 한 줄)만 썼다. ament_cmake 패키지, C++ 라이브러리(LD_LIBRARY_PATH), 메시지 패키지는 측정하지 않았다.
- merged에서 새 패키지 `ros2 run`이 다시 source 없이 되는지는 "이미 다른 ament_python 패키지가 있어 merged site-packages가 PYTHONPATH에 들어간 상태"에서만 확인한다. 기존 패키지가 ament_cmake뿐인 작업공간은 확인하지 않는다.
- `--symlink-install`은 쓰지 않았다. 대조군은 복사 설치에서 "고친 뒤 다시 빌드"한 경우다.
- T는 `--noprofile --norc` bash다. 실제 데스크톱 터미널의 `.bashrc`, IDE 통합 터미널, zsh는 반영되지 않는다.
- 패키지 삭제, 빌드 셸과 T를 같은 터미널로 쓰는 경우(공식 비권장)는 측정하지 않았다.
- 개발 환경 설정 측정이며 로봇 동작, 시뮬레이터, 실제 하드웨어에 대해서는 아무것도 보여 주지 않는다.

## 시행착오(시험 실행에서 실제로 실패하거나 고친 점)

1. 첫 시험 실행은 research.md 제안대로 작업공간을 `/tmp` 아래에 만들었다. 패키지 수·경로 항목 측정은 정상이었지만 `ros2 run`이 두 레이아웃·모든 시점에서 `No executable found`로 실패했다. 설치 파일 목록을 디버그로 출력해 보니 `install/lib/probe_a/probe_a_node`는 실제로 있었다. 하네스가 `/tmp`를 tmpfs로 마운트하는데 이 마운트가 `noexec`여서, `ros2 run`이 실행 가능 파일로 인정하지 않은 것으로 판단했다. 작업공간을 컨테이너 자체 파일시스템(`/var/tmp`)으로 옮기자 `ros2 run`이 동작했다. 원인을 결과에 남기려고 `env` 줄에 `/proc/mounts`의 `noexec` 여부를 기록하게 했다(시험 실행에서 `/tmp`는 `noexec: true`, `/`는 `false`). 이 실패는 실험 환경의 문제다. 독자의 일반 터미널에서 생기는 증상으로 쓰면 안 된다.
2. 같은 첫 시험 실행에서 results.json의 stdout 앞부분이 잘려 있었다. 하네스는 stdout의 마지막 8000자만 저장한다. 그래서 overlay 경로를 절대 경로 대신 작업공간 기준 상대 경로로 줄였다. `ros2 run`·`ros2 pkg prefix` 출력은 끝 80자만 남기고, 버전 문자열의 빌드 날짜 꼬리도 잘라 전체 출력이 상한 안에 들어오게 했다.
3. 디버그용 설치 파일 목록 출력은 원인을 확인한 뒤 삭제했다.
