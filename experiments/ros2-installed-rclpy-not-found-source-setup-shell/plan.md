# 실험 계획: 새 터미널마다 source한 setup 파일과 셸 종류에 따라 `import rclpy`가 성공하는가

## 질문

ROS 2를 설치했는데 `import rclpy`가 실패한다. 이것이 설치 문제인지, 아니면 **지금 연 터미널의 환경 상태**(source 여부, 셸 종류와 setup 파일의 짝, Python이 ROS 경로를 보는지) 문제인지 종료 코드로 가를 수 있을까?

- 갈래 ① `No module named 'rclpy'`: 셸·source 조합만 바꿔 재현되고, `PYTHONPATH`가 원인 경로인지 확인한다.
- 갈래 ② `No module named 'rclpy._rclpy_pybind11'`(인터프리터 불일치): 다른 버전의 인터프리터는 이미지에 없으므로 import로 재현하지 않는다. 대신 현재 인터프리터의 `EXT_SUFFIX`와 rclpy 폴더 안 C 확장 파일 이름의 태그가 맞는지를 파일로 확인한다.

## 환경

- 하네스: `ros:jazzy-ros-base` 컨테이너, `--network none`, 1 CPU, 1 GiB. Humble이 아니라 Jazzy(Python 3.12)다. research.md 기준으로 setup.bash/zsh/sh 템플릿 원문은 humble과 jazzy가 같다. Humble의 Python 3.10·`cpython-310` 값은 실행 근거가 아니다.
- 하네스는 `source /opt/ros/jazzy/setup.bash` 후 이 스크립트를 실행한다. 그래서 "새 터미널"은 `env -i`와 같은 방식으로 흉내 낸다. 환경을 `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`, `HOME=/tmp`만으로 비운 자식 셸을 쓴다(cwd=/tmp).
- `sh`는 dash로 연결되고 zsh는 이미지에 없다(실행 중 확인해 `env` 줄에 기록).

## research.md 기준 예측값 (실행 전 선언)

| 경우 | 셸 | source | python | 예측 |
|---|---|---|---|---|
| A | bash | 없음 | `python3 -c 'import rclpy'` | 실패, `No module named 'rclpy'` |
| B | bash | `source setup.bash` | 같음 | 성공 |
| C | sh(dash), 비대화형 | `. setup.bash` | 같음 | source 단계에서 `Bad substitution`. 비대화형이라 셸이 종료되고 python 미실행, 비0 종료 |
| C2 | sh(dash), 대화형(tty) | `. setup.bash` | 같음 | 같은 오류가 나지만 셸은 종료하지 않음(POSIX 2.8.1). 다음 줄의 python이 실행되고 `PYTHONPATH`가 비어 있어 `No module named 'rclpy'` |
| D | sh(dash) | `. setup.sh` | 같음 | 성공(고정 prefix) |
| E | bash | `source setup.sh` | 같음 | 성공 |
| F | bash | `source setup.bash` | `python3 -I -c 'import rclpy'` | 실패, `No module named 'rclpy'`(`-I`가 PYTHON* 무시). PYTHONPATH가 원인 경로라는 대조군 |
| I | bash, **환경 상속**(비우지 않음) | 없음 | `python3 -c 'import rclpy'` | 성공(부모가 이미 source한 환경을 물려받음). env -i가 왜 필요한지와 "이미 source한 터미널에서 연 프로그램"을 보여 주는 대조군 |
| J | bash | `source setup.bash` | `rclpy.init()` → `create_node` → `shutdown()` | 성공. ros-base에 없는 `demo_nodes_py listener`를 대신하는 최소 Python API 검사(공식 listener 테스트와 같지 않음) |

- 집계 예측: 환경을 비운 새 셸 A–F 여섯 개 중 import 성공 3개(B, D, E). 전체 9개 경우 중 성공 5개(B, D, E, I, J). 이 3/6은 산술 예제의 3/6과 다른 시나리오다.
- G: `site-packages/rclpy/_rclpy_pybind11<EXT_SUFFIX>` 있음. 같은 폴더에 `cpython-310`·`cpython-311` 태그 파일 없음.
- H: rpyutils 오류 메시지가 계산하는 경로 `site-packages/_rclpy_pybind11<EXT_SUFFIX>`는 정상 설치에서도 없음.
- K: `SHELL=/bin/bash`를 준 채 dash를 실행하면 `$SHELL`과 실제 실행 중인 셸(`readlink /proc/$$/exe`)이 다름.
- L: ros-base 이미지에 `demo_nodes_py` 없음, `/opt/ros/jazzy/bin/python3` 없음.

## 무엇을 어떻게 재는가

- 경우마다 자식 셸 하나를 띄운다. 스크립트는 `<source 명령>` → `echo "SOURCE_STEP_DONE PYTHONPATH=$PYTHONPATH"` → `<python 명령>` 순서다.
  - `exit_code`: 셸의 종료 코드. 대화형 C2는 마지막에 `exit $?`를 입력해 python의 종료 코드로 끝낸다.
  - `shell_survived_source`: source 다음 줄의 표식이 출력됐는지(셸이 source 오류 뒤에도 살아 있었는지).
  - `ros_site_in_pythonpath`: 표식 줄의 `PYTHONPATH`에 `/opt/ros/jazzy/lib/python3.12/site-packages`가 있는지(경로는 실행 중 `sys.version_info`로 만든다).
  - `import_ok`/`api_ok`: python이 출력한 `RCLPY_OK`/`API_OK` 표식 유무.
  - `error_class`·`stderr_first`·`stderr_last`: 오류 문구 분류(`no_module_rclpy`, `c_extension_missing`, `bad_substitution` 등). source 단계에서 오류가 난 경우는 `stderr_all`에 오류 줄을 모두 남긴다.
  - `elapsed_ms`: 자식 셸 실행 시간(참고값).
- 대화형 C2는 표준 라이브러리 `pty`로 의사 터미널을 만들고 그 위에서 `sh -i`를 실행한다. 명령을 tty로 입력하므로 한 줄씩 읽힌다. 입력 에코는 termios로 끄고, 표식은 `'RCLPY' + '_OK'`처럼 이어 붙여 출력해 입력 원문이 표식으로 오인되지 않게 했다. tty에서는 stdout·stderr가 섞이므로 오류 줄은 프롬프트(`$ `, `# `)와 표식 줄을 뺀 나머지다.
- G/H/L은 파일 존재 확인, K는 `sh -c 'echo "$SHELL"; readlink /proc/$$/exe'` 실행 결과다.
- `summary` 줄: 새 셸 A–F 중 성공 수, 전체 성공 수, 예측과 일치한 경우 수, 불일치 목록, 총 소요 시간. 예측표는 코드에 있지만 성공 여부는 위 측정값으로만 계산한다. 결과 숫자를 코드에 미리 적어 두지 않았다.
- 한계: zsh 조합, 실제 사람이 쓰는 터미널 에뮬레이터, conda 같은 다른 버전 인터프리터의 import, `demo_nodes_py listener`, Humble은 측정하지 않는다. C2는 pty 위의 dash 대화형 모드이며 bash 대화형이나 GUI 터미널과 같다고 일반화하지 않는다.

## 시행착오 (시험 실행에서 실제로 실패하거나 고친 점)

1. **대화형 sh를 `sh -i -c '...'`로 재려다 실패했다.** 첫 시험 실행에서 C2는 셸이 source 다음 줄로 넘어가지 못하고 비0으로 끝났고, stderr 마지막 줄은 프롬프트 `# `였다. 원인은 `-c` 문자열이 한 번에 읽히는 입력이라는 점이다. 대화형 dash는 오류가 나면 그 입력을 통째로 버리고 프롬프트로 돌아간다. 그 뒤 stdin이 비어 있어 바로 끝났다. "대화형 셸은 종료하지 않는다"를 재지 못한 측정이었다.
2. **명령을 파이프 stdin으로 넣는 방식도 실패했다.** 두 번째 시험 실행에서 `sh -i`에 파이프로 명령을 한꺼번에 넣었다. 결과는 비대화형 C와 같았다(표식 미출력, 비0 종료). dash는 오류 처리 때 입력 버퍼를 비우는데, 파이프로 미리 읽혀 버퍼에 들어 있던 다음 줄들까지 버려진 것으로 판단했다. 이 판단은 dash 소스(입력 reset)에 근거한 추론이며 따로 검증하지 않았다. 실제 터미널(tty)에서는 한 줄씩 읽히므로 같은 상황이 아니다.
3. **pty로 바꿔 해결했다.** 세 번째 시험 실행부터 C2는 예측대로 동작했다. 오류 3줄(`Bad substitution`, `builtin: not found`, `cannot open /setup.sh`)을 출력한 뒤 셸이 살아 있었고, `PYTHONPATH`가 빈 채로 `No module named 'rclpy'`로 끝났다. 이때 에코된 입력 줄이 표식으로 잡히지 않도록 에코 끄기와 표식 분리를 함께 넣었다.
4. 하네스 stdout 보관 한도(뒤쪽 8000자) 안에 들도록 경우별 python 명령 원문 대신 짧은 이름(`python3`, `python3 -I`, `python3 api`)을 기록하게 바꿨다. source 오류 줄 전체(`stderr_all`)는 `Bad substitution`이 난 경우에만 남긴다.
