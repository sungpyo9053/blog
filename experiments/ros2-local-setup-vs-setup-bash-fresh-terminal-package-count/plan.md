# 실험 계획: 새 터미널에서 overlay의 스크립트 하나만 source하면 underlay 패키지도 보이는가

## 질문

기존 ROS 2 설치(underlay, `/opt/ros/jazzy`) 위에 내 작업공간(overlay, `/tmp/ws`)을 colcon으로 빌드했다.
아무것도 source하지 않은 새 터미널에서 overlay의 `install/setup.bash` **또는** `install/local_setup.bash`
하나만 source하면 underlay 패키지와 내 패키지가 함께 보이는가?

## research.md 기준 예측값 (문서·코드에서 도출, 기호로만)

기호: U = underlay만 source한 셸에서 보이는 패키지 수, M = overlay 패키지 수.
U의 숫자는 미리 예측하지 않는다.

| 새 셸 | source 줄 | 예측 |
|---|---|---|
| T0 | 없음 | `ros2` 없음(종료 코드 127), 색인 0개 |
| T1 | `/opt/ros/jazzy/setup.bash` | U개, overlay 패키지 0개 |
| T2 | `/tmp/ws/install/setup.bash` | U+M개 (가설 1: underlay까지 불러옴) |
| T3 | `/tmp/ws/install/local_setup.bash` | `ros2` 없음(종료 127), 색인 M개 (가설 2: overlay만) |
| T4 | underlay `setup.bash` → overlay `local_setup.bash` | T2와 같은 패키지 집합 (공식 note의 "동등" 주장) |

또한 생성된 `install/setup.bash`에는 `COLCON_CURRENT_PREFIX="/opt/ros/jazzy"`가 빌드 시점 경로로
적혀 있고, `install/local_setup.bash`에는 `/opt/ros/jazzy`가 없을 것으로 예측한다.

판정 기준선 = (U+M+M)/2 (가설 1 예측 U+M과 가설 2 예측 M의 중간). 셸의 개수가 기준선보다 크고
overlay 패키지 M개가 모두 보이면 "underlay와 overlay 모두 보임", 아니면 "overlay만".

## 무엇을 어떻게 재는가

환경: 하네스의 `ros:jazzy-ros-base` 컨테이너, 네트워크 없음, 1 CPU·1 GiB. 하네스는
`source /opt/ros/jazzy/setup.bash` 후 이 스크립트를 실행하므로, 부모 프로세스는 "underlay를
source한 빌드 터미널"에 해당한다.

1. **overlay 빌드**: `/tmp/ws/src`에 이름이 underlay와 겹치지 않는 최소 ament_python 패키지 3개
   (`huntlab_probe_a`, `_b`, `_c`, 실행 의존성 `rclpy`)를 파일로 직접 만들고
   `colcon build --parallel-workers 1`(기본 isolated 설치)로 빌드한다. 종료 코드·소요 시간과
   `dpkg-query`로 읽은 colcon-core/colcon-bash/colcon-ros 패키지 버전을 기록한다.
2. **생성된 스크립트 확인**: `install/setup.bash`와 `install/local_setup.bash`에서
   `COLCON_CURRENT_PREFIX=`로 시작하는 줄을 그대로 뽑고, 각 파일에 `/opt/ros/jazzy` 문자열이 있는지 기록한다.
3. **새 터미널 흉내**: `env -i HOME=/tmp PATH=/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 bash --noprofile --norc -c ...`
   로 상속 환경변수를 모두 비운 하위 셸 T0~T4를 띄워 위 표의 source 줄만 실행한 뒤 측정한다.
   - `command -v ros2`의 결과 경로(없으면 null)
   - `ros2 pkg list`의 종료 코드, 성공 시 출력 줄 수(= 서로 다른 패키지 이름 수), 실패 시 stderr 첫 줄
   - 보조 계수(ros2가 없어도 가능): 셸의 `AMENT_PREFIX_PATH`를 `:`로 나눠 각 경로의
     `share/ament_index/resource_index/packages/` 아래 점으로 시작하지 않는 파일 이름을 합집합으로 센 값
   - 그 합집합에 probe 3개와 `rclpy`가 들어 있는지, `AMENT_PREFIX_PATH` 항목 수와 `/opt/ros/jazzy` 포함 여부, `COLCON_PREFIX_PATH`
4. **판정 계산(실행 중)**: U = T1 색인 수, M = overlay `install/*/share/ament_index/resource_index/packages/`의
   실제 파일 수(T3과 독립), 이름 겹침 수 = T1 집합 ∩ overlay 집합. 기준선 (U+M+M)/2와 T2·T3 값을 비교한다.
   T2·T3에서 `ros2 pkg list`가 성공하면 그 줄 수를, 실패하면 보조 계수를 판정에 쓴다.
   `ros2 pkg list` 줄 수와 보조 계수가 일치하는지(측정 도구 교차 확인), T4 집합이 T2 집합과 같은지도 기록한다.

출력은 `kind`가 `environment`, `build`, `generated_scripts`, `terminal`(셸마다 1줄), `verdict`인 JSON 줄이다.
모든 숫자는 실행 중에 측정하며 코드에 결과값을 적지 않는다. 빌드가 실패하면 그 출력 꼬리만 남기고
종료 코드 1로 끝내며 숫자를 만들지 않는다.

## 한계

- `env -i` 하위 셸은 "환경을 비운 새 셸"이며, 실제 데스크톱 터미널은 `~/.bashrc`·`/etc/profile`이 개입할 수 있다.
- bash만 확인한다(zsh·sh·Windows, `--merge-install`, 3단 이상 체인은 범위 밖).
- overlay가 같은 이름의 underlay 패키지를 덮어쓰는지(override)는 재지 않는다(이름이 겹치지 않게 설계).
- underlay를 바꾼 뒤 재빌드가 필요한지는 재지 않는다.
- 컨테이너 안 개발 환경 측정이며 시뮬레이터·실물 로봇과 무관하다.

## 시행착오 (시험 실행 기준)

- 첫 시험 실행(`--try`)은 한 번에 성공했다(빌드·5개 셸 측정·판정 모두 완료, 한 번 실행 약 6초).
- 고친 점 1: 첫 버전은 M을 T3 셸의 색인 수로 정해, 판정 대상(T3)에서 판정 기준을 뽑는 순환이 있었다.
  M을 overlay `install` 폴더의 ament 색인 파일 수로 따로 세도록 바꿨다.
- 고친 점 2: 생성 스크립트 확인 필드 이름을 `*_chain`에서 `*_prefix_assignments`로 바꿨다.
  `setup.bash`에서 뽑히는 `COLCON_CURRENT_PREFIX=` 줄에는 상위 prefix(`/opt/ros/jazzy`) 줄뿐 아니라
  자기 디렉터리를 가리키는 줄도 함께 나오기 때문에, "체인 목록"이라는 이름이 오해를 줄 수 있었다.
- 고친 뒤 두 번째 시험 실행도 종료 코드 0으로 끝났고, 판정 방향은 첫 실행과 같았다.
  확정 수치는 하네스의 정식 5회 실행 `results.json`만 사용한다.
