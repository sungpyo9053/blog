# 실험 계획: colcon build에서 "다시 빌드할 일"을 줄이는 수단을 Jazzy 컨테이너에서 확인하기

## 질문

글의 핵심 질문은 "colcon build가 느릴 때 overlay·COLCON_IGNORE·`--symlink-install`이 각각 무엇을 줄이는가"다.
이 실험은 research.md의 "Experiment 단계로 넘길 측정 질문" Q1~Q4를 한 번의 실행으로 확인한다.

- Q1 바꾼 것이 없어도 colcon build는 선택된 패키지마다 시간을 쓰는가? 선택 패키지 수를 줄이면(`--packages-select`) 시간이 줄어드는가?
- Q2 `COLCON_IGNORE` 파일을 두면 colcon이 찾는 패키지 수가 그만큼 줄고, 무변경 빌드 시간도 줄어드는가?
- Q3 `--symlink-install`로 빌드한 ament_python 패키지는 Python 파일 수정이 다시 빌드 없이 설치본에 반영되는가? symlink 없이 빌드하면 반영되지 않는가?
- Q4 `--cmake-args -DBUILD_TESTING=0`이나 `--symlink-install`을 직전 실행과 다르게 주면 ament_cmake 패키지의 CMake 재구성(configure)이 다시 도는가? 같은 인자를 유지하거나 `colcon_defaults.yaml`로 고정하면 재구성이 멈추는가?

## research.md 기준 예측값

- Q1: 무변경 전체 재빌드와 `--packages-select` 1개 재빌드 모두 0초보다 크고, 전체 쪽이 대략 패키지 수에 비례해 크다. 근거: colcon-cmake가 매 실행 재구성 판단 → `cmake --build` → install을 밟는다.
- Q2: `colcon list` 패키지 수가 무시 파일 개수만큼 줄어든다.
- Q3: symlink 있음 = 반영됨, symlink 없음 = 반영 안 됨(다시 빌드해야 반영).
- Q4: 인자를 바꾼 실행은 configure를 다시 돌아 같은 인자 실행보다 오래 걸린다. 같은 인자 반복과 `colcon_defaults.yaml` 고정은 configure를 다시 돌지 않는다.
- research.md에 예측이 없던 항목: `-DBUILD_TESTING=0`을 뺀 뒤 BUILD_TESTING이 다시 켜지는지는 예측하지 않았다(실험에서 관찰만 한다).

## 환경

- 하네스 이미지 `ros:jazzy-ros-base`, 네트워크 없음, 1 CPU·1 GiB. 실제 버전과 이미지 다이제스트는 results.json의 `environment`에 하네스가 기록한다.
- 스크립트는 `colcon`, `cmake`, `g++`, Python 표준 라이브러리만 쓴다. 외부 패키지 설치나 네트워크 접근이 없다.
- 작업공간은 컨테이너 `/tmp/colcon_lab` 안에서 매 실행 새로 만든다. 로봇·시뮬레이터·하드웨어는 쓰지 않는다.
- 스크립트 첫 줄 출력에 `os.cpu_count()`와 `sched_getaffinity` 값을 남긴다. 하네스는 `--cpus 1`(CPU 시간 할당량)로 제한하지만 컨테이너가 보는 코어 수는 호스트 값일 수 있어, 기본(병렬) 실행기의 작업자 수와 `make -j` 값 해석에 필요하다.

## 무엇을 어떻게 재는가

작업공간 3개를 만든다.

1. `ws_cmake`: 최소 ament_cmake 패키지 4개(`cm_1`~`cm_4`). 각 패키지는 한 줄짜리 C++ 실행 파일 1개, 설치되는 YAML 1개, `if(BUILD_TESTING)` 안에 테스트용 실행 파일 타깃 1개(`<pkg>_selftest`)를 가진다. 패키지끼리 의존하지 않는다.
2. `ws_py_copy`, `ws_py_symlink`: 같은 ament_python 패키지 `py_demo`(모듈 `py_demo/core.py`에 `VALUE = 'v1'`)를 각각 둔다. 복사 설치와 symlink 설치를 섞지 않으려고 작업공간을 나눴다.

측정 항목(모두 실행 중에 측정해 JSON 한 줄씩 출력):

- 시간: 각 `colcon build` 명령의 벽시계 시간(`time.monotonic()` 차이, 초). 무변경 재빌드처럼 1초 안팎으로 짧은 항목은 같은 명령을 3번 재서 `samples_seconds`와 중앙값 `median_seconds`를 남긴다.
- `packages_finished`: colcon 출력의 `Finished <<<` 줄 수(이번 실행에서 처리한 패키지 수).
- `packages_found`: `colcon list --names-only`가 찾은 패키지 수와 이름.
- `cmake_configure_invoked`: colcon이 남긴 `log/latest_build/<pkg>/command.log`에서 이번 실행에 `cmake <src>` 형태의 configure 호출이 있었던 패키지 수. `cm_1_commands`는 `cm_1`에서 실제 호출된 단계(configure/build/install) 목록이다.
- `cmake_cache_rewritten`: `build/<pkg>/CMakeCache.txt` 수정 시각이 바뀐 패키지 수(보조 지표).
- `cm_1_BUILD_TESTING_in_cache`, `cm_1_AMENT_CMAKE_SYMLINK_INSTALL_in_cache`: `cm_1` CMakeCache.txt에 저장된 값.
- `cm_1_selftest_in_generated_makefile`: 생성된 `build/cm_1/Makefile`에 테스트용 타깃이 있는지(테스트 트리가 구성됐는지).
- `ament_cmake_installed_yaml`: `--symlink-install` 뒤 ament_cmake가 설치한 YAML이 심볼릭 링크이고 src를 가리키는지.
- Q3: install 환경을 source한 새 bash에서 `import py_demo.core`로 읽은 값. 소스를 `v2`로 고친 뒤 **다시 빌드하지 않고** 읽은 값(`after_edit_no_rebuild`)과 반영 여부(`reflected`). 복사 설치 쪽은 다시 빌드한 뒤의 값도 읽는다.

실행 순서(`ws_cmake`, 모든 빌드는 `--executor sequential`. 기본 실행기 비교 항목만 예외):

1. `colcon list` → 클린 빌드
2. 무변경 전체 재빌드 3회 → `--packages-select cm_1` 무변경 재빌드 3회 → 기본 실행기(`colcon build`) 무변경 재빌드 3회
3. `cm_3`, `cm_4`에 `COLCON_IGNORE` 생성 → `colcon list` → 무변경 재빌드 3회 → 무시 파일 삭제 후 `colcon list`
4. `--cmake-args -DBUILD_TESTING=0`(인자 변경) → 같은 인자 반복 → 인자 없이(기본으로 되돌림) → `--symlink-install` 추가 → 같은 인자 반복 → `colcon_defaults.yaml`에 `symlink-install: true`를 적고 명령줄에서는 인자 없이
5. Python: 복사 설치 빌드 → 수정 → 재빌드 없이 읽기 → 재빌드 → 읽기 / symlink 설치 빌드 → 수정 → 재빌드 없이 읽기

판정 기준:

- Q1 확인: 무변경 재빌드에서도 `cm_1_commands`에 build·install 호출이 남고, 시간이 0보다 크며, 4개 > 2개(COLCON_IGNORE 후) > 1개(`--packages-select`) 순서가 유지되면 "선택 패키지 수가 무변경 빌드 시간의 손잡이"라는 예측과 일치.
- Q2 확인: `packages_found`가 무시 파일 수만큼 줄어들면 일치.
- Q3 확인: symlink 쪽 `reflected=true`, 복사 쪽 `reflected=false`이고 재빌드 후 `v2`면 일치.
- Q4 확인: 인자를 바꾼 실행의 `cmake_configure_invoked`가 패키지 수와 같고, 같은 인자 반복·`colcon_defaults.yaml` 고정 실행에서 0이면 일치.
- 실패 판정: colcon 명령이 0이 아닌 코드로 끝나면 `error` 줄을 출력하고 `summary.failures`에 남긴 뒤 스크립트가 종료 코드 1로 끝난다.

## 해석상 한계

- 패키지가 한 줄짜리 C++ 파일뿐인 최소 패키지다. 시간 크기는 실제 프로젝트의 패키지 시간이 아니라 colcon·CMake가 패키지마다 쓰는 고정 비용의 크기 감각만 준다. 실제 작업공간의 컴파일 시간은 측정하지 않았다.
- 1 CPU 할당량의 컨테이너 한 대에서 잰 값이다. 기본 병렬 실행기와 순차 실행기의 차이는 이 조건에만 해당한다.
- overlay 자체(underlay 위에 작업공간을 얹는 구성)는 따로 만들지 않았다. overlay가 줄이는 몫은 "이번 실행에 선택되는 패키지 수 감소"이며, 이 실험에서는 `--packages-select`와 `COLCON_IGNORE`로 같은 몫(패키지 수 감소)을 측정했다.
- C++ 소스 수정 뒤의 재컴파일, 새 Python 파일 추가, `setup.py` 변경 시 symlink 동작은 측정하지 않았다.

## 시행착오(시험 실행에서 실제로 실패하거나 고친 점)

1. 첫 시험 실행은 재구성 여부를 `CMakeCache.txt` 수정 시각 변화로만 판정했다. 그런데 `-DBUILD_TESTING=0`을 뺀 실행이 같은 인자 반복보다 눈에 띄게 오래 걸렸는데도 "재구성 0"으로 나왔다. 값이 바뀌지 않으면 캐시 파일 수정 시각이 그대로일 수 있어, 수정 시각만으로는 configure 실행 여부를 알 수 없었다. colcon이 패키지별로 남기는 `log/latest_build/<pkg>/command.log`의 호출 기록으로 판정 기준을 바꾸고, 수정 시각은 보조 지표(`cmake_cache_rewritten`)로만 남겼다.
2. 두 번째 시험 실행에서 command.log 판별이 0으로 나왔다. 로그의 실제 형식이 `CMAKE_PREFIX_PATH=... /usr/bin/cmake <src> ...`여서 `" cmake "`(앞뒤 공백) 문자열 검사가 맞지 않았다. 디버그 출력으로 실제 로그 줄을 확인한 뒤 `bin/cmake ` 기준으로 고쳤고, 디버그 출력은 삭제했다.
3. 같은 무변경 재빌드를 한 번만 재면 첫 시험에서 연속 두 번의 값 차이가 컸다. 1초 안팎 항목은 3회 측정과 중앙값으로 바꿨다.
4. 처음에는 테스트 트리가 사라졌는지를 `build/cm_1/cm_1_selftest` 파일 존재로 판정했는데, 이전 빌드에서 만든 실행 파일이 남아 있어 항상 참이었다. 생성된 `Makefile`에 해당 타깃이 있는지로 바꿨다.
5. 시험 실행에서 관찰된 예측 밖 현상: `-DBUILD_TESTING=0`을 명령줄에서 빼면 configure는 다시 돌지만, CMakeCache.txt의 BUILD_TESTING 값은 0으로 남고 테스트 타깃도 돌아오지 않았다. 이 항목은 정식 5회 실행의 results.json으로만 확정한다.
