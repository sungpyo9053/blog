# 실험 계획: LaunchConfiguration 값은 언제, 어떤 문자열·타입으로 풀리나

## 질문

Python launch 파일에서 `DeclareLaunchArgument`로 받은 `a='2'`, `b='5'`를 이어서 쓰면
실제 ROS 2 Jazzy launch가 무엇을 만드는가? 덧셈 7이 아니라 문자열 `'25'`가 되는지,
그 문자열이 Node 파라미터로 가면 노드는 어떤 타입·값을 받는지, 그리고 계산·조건 분기를
`PythonExpression`·`IfCondition`·`OpaqueFunction` 중 어디서 하면 의도한 값이 나오는지
기본값 실행과 명령줄 덮어쓰기 실행으로 확인한다.

## research.md 기준 예측값 (실행 전 기록)

A부 — launch API 직접 호출 (context: a='2', b='5', idx='2', r='200', u='True', name='robot1')

| case | 코드 | 예측 |
| --- | --- | --- |
| plan_str | `str(LaunchConfiguration('a'))` | 값 `'2'`가 아니라 객체 표현 문자열 |
| plan_int | `int(LaunchConfiguration('a'))` | `TypeError` |
| plan_add | `LaunchConfiguration('a') + LaunchConfiguration('b')` | `TypeError` |
| plan_perform_empty_ctx | 빈 `LaunchContext()`에서 `perform` | `SubstitutionFailure` (값·기본값 없음) |
| perform_a | `a.perform(ctx)` | `'2'` (str) |
| concat_list | `[a, b]` 연결 | `'25'` (str) |
| concat_list_with_text | `['robot_', a, b]` | `'robot_25'` |
| pyexpr_no_operator | `PythonExpression([a, b])` | `'25'` (str) |
| pyexpr_plus | `PythonExpression([a, ' + ', b])` | `'7'` (str) |
| pyexpr_scale | `PythonExpression([idx, ' * 1.5'])` | `'3.0'` (str) |
| pyexpr_string_no_quotes | `PythonExpression([name, " == 'robot1'"])` | `NameError` (robot1이 Python 이름으로 eval) |
| pyexpr_string_quoted | 따옴표로 감싼 비교 | `'True'` |
| if_compare_200 | `IfCondition(PythonExpression([r,' == 200',' and ',u]))`, r='200' | `True` |
| if_compare_199 | 같은 조건, r='199' | `False` |
| if_raw_200 | `IfCondition(LaunchConfiguration('r'))`, r='200' | `InvalidConditionExpressionError` |
| if_raw_1 / if_raw_true / if_raw_yes | r='1' / ' TRUE ' / 'yes' | `True` / `True` / `InvalidConditionExpressionError` |
| param_concat | `parameters=[{'offset': [a, b]}]` | `25`, int |
| param_pyexpr_plus | `{'offset': PythonExpression([a,' + ',b])}` | `7`, int |
| param_pyexpr_scale | `{'scale': PythonExpression([idx,' * 1.5'])}` | `3.0`, float |
| param_value_str | `ParameterValue([a, b], value_type=str)` | `'25'`, str |

B부 — 실제 `ros2 launch /tmp/args_demo.launch.py`

| 실행 | concat | pyexpr_no_operator | pyexpr_sum | opaque_sum | if_branch | 노드 offset_concat | offset_sum | scale | offset_str |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (가) 기본값 | 25 | 25 | 7 | 7 | 실행됨 | 25 (INTEGER) | 7 (INTEGER) | 3.0 (DOUBLE) | '25' (STRING) |
| (나) `a:=3 b:=4 r:=199` | 34 | 34 | 7 | 7 | 건너뜀 | 34 (INTEGER) | 7 (INTEGER) | 3.0 (DOUBLE) | '34' (STRING) |

계획 단계(`generate_launch_description()` 안)의 `PLAN_TIME` 줄: `LaunchConfiguration`이며 `str`이 아님(is_str=False).
`OpaqueFunction` 안에서 `perform(context)`로 꺼낸 값의 타입: `str,str`.

## 무엇을 어떻게 재는가

- 실행 환경: 하네스의 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB). 추가 패키지 없음. 사용 모듈은
  이미지에 들어 있는 `launch`, `launch_ros`, `rclpy`뿐이다.
- A부: `LaunchContext()`를 만들고 `launch_configurations`에 문자열 값을 넣은 뒤 각 substitution의
  `perform`/`perform_substitutions`/`Condition.evaluate`/`launch_ros.utilities.evaluate_parameters`
  (반드시 `normalize_parameters`를 거친 뒤)를 실제로 호출한다. 결과의 `repr`과 Python 타입 이름,
  또는 예외 클래스와 메시지를 그대로 기록한다. 각 호출 소요 시간(ms)도 함께 잰다.
- B부: 실험 중에 `/tmp/args_demo.launch.py`와 `/tmp/param_probe.py`(rclpy 노드)를 써서
  `ros2 launch`를 두 번 실행한다(기본값, `a:=3 b:=4 r:=199`). 각 실행의 종료 코드·소요 초,
  `LogInfo`가 찍은 `OUT 이름=값` 줄, 계획 단계 `PLAN_TIME` 줄, 그리고 노드가
  `automatically_declare_parameters_from_overrides=True`로 실제 받은 파라미터의 값·ROS 타입
  (`Parameter.Type`)·Python 타입을 `PROBE` JSON으로 수집한다. 실행마다 25초 제한을 둔다.
- 출력: 모든 측정은 `{"part": ..., "case": ...}` 형식의 JSON 한 줄씩 stdout에 쓴다.
  결과 값은 코드에 미리 적지 않고 실행 중에 계산·수집한 값만 출력한다.
- 판정: 위 예측표와 results.json의 값을 비교한다. 예측과 다르면 results.json이 맞고 본문은 실측을 따른다.

## 시행착오

시험 실행은 `scripts.experiment_runner --try`로 세 번 했다.

1. 첫 시험: A부와 B부의 `LogInfo` 줄은 모두 나왔지만 B부 `node_params`가 `null`이었다. 원인을
   알 수 있는 줄이 수집되지 않아서 `param_probe`·`ERROR`가 들어간 줄을 `process_lines`로 따로
   모으도록 고쳤다(첫 시험에서는 `OpaqueFunction` 로그 줄을 정규식 하나로 뽑다가 꼬여서
   `opaque_types`와 `opaque_sum`을 `LogInfo` 두 줄로 나눈 수정도 같이 했다).
2. 두 번째 시험: 원인이 `PermissionError: [Errno 13] Permission denied: '/tmp/param_probe.py'`로
   드러났다. 하네스가 `/tmp`를 `--tmpfs`로 붙이는데, 이 tmpfs는 실행 권한이 없는(noexec)
   마운트라서 `chmod +x`를 해도 스크립트를 직접 실행할 수 없었다. 이때 노드 프로세스는 시작조차
   못 했는데도 `ros2 launch`의 종료 코드는 0이었다. 즉 종료 코드만 보고 "노드가 파라미터를 받았다"고
   판정하면 안 되므로, 이 실험은 노드가 직접 찍은 `PROBE` 줄이 있어야만 파라미터 결과로 인정한다.
   수정: `Node(executable='python3', arguments=['/tmp/param_probe.py'], ...)`로 바꿔 python3 인터프리터가
   스크립트를 읽게 했고, 필요 없어진 shebang·`chmod`를 지웠다.
3. 세 번째 시험: 성공(1/1). A부·B부 결과가 위 예측표와 모두 같은 방향으로 나왔다. 정식 수치는
   하네스의 5회 실행 results.json만 근거로 쓴다.

참고: `str(LaunchConfiguration('a'))`와 `InvalidConditionExpressionError` 메시지에는 객체 메모리 주소
(`0x…`)가 들어가므로 실행마다 달라진다. 본문에서는 주소 부분을 값으로 인용하지 않는다.
