#!/usr/bin/env python3
"""LaunchConfiguration 값이 언제, 어떤 문자열·타입으로 풀리는지 ROS 2 Jazzy에서 직접 잰다.

A부: launch API를 직접 호출해 substitution 리스트 연결, PythonExpression, IfCondition,
     Node 파라미터 타입 변환, 계획 단계 오류를 측정한다.
B부: /tmp에 launch 파일과 파라미터 확인 노드를 써서 실제 `ros2 launch`를
     기본값과 명령줄 값(a:=3 b:=4 r:=199)으로 실행하고 로그와 노드가 받은 파라미터를 기록한다.

모든 결과는 실행 중에 계산된 값이며 JSON 한 줄씩 stdout으로 출력한다.
"""
import json
import os
import platform
import re
import subprocess
import sys
import time

from launch import LaunchContext
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.utilities import evaluate_parameters, normalize_parameters


def emit(**record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


def context(**values):
    ctx = LaunchContext()
    for name, value in values.items():
        ctx.launch_configurations[name] = value
    return ctx


def attempt(fn):
    """Run fn and return (value, None) or (None, 'ExceptionClass: message')."""
    try:
        return fn(), None
    except Exception as exc:  # 오류 종류와 문구 자체가 측정 대상이다
        return None, f"{type(exc).__name__}: {exc}"


def api_case(case, code, fn):
    started = time.perf_counter()
    value, error = attempt(fn)
    emit(part="A", case=case, code=code, result=repr(value) if error is None else None,
         result_type=type(value).__name__ if error is None else None, error=error,
         elapsed_ms=round((time.perf_counter() - started) * 1000, 3))


a, b = LaunchConfiguration("a"), LaunchConfiguration("b")


def part_a():
    ctx = context(a="2", b="5", idx="2", r="200", u="True", name="robot1")
    idx, r, u, name = (LaunchConfiguration(n) for n in ("idx", "r", "u", "name"))

    # 1) 계획 단계: generate_launch_description() 안에서 값처럼 쓰려 할 때
    api_case("plan_str", "str(LaunchConfiguration('a'))", lambda: str(a))
    api_case("plan_int", "int(LaunchConfiguration('a'))", lambda: int(a))
    api_case("plan_add", "LaunchConfiguration('a') + LaunchConfiguration('b')", lambda: a + b)
    api_case("plan_perform_empty_ctx", "LaunchConfiguration('a').perform(LaunchContext())",
             lambda: a.perform(LaunchContext()))

    # 2) 실행 단계: context 안에서 꺼내기
    api_case("perform_a", "a.perform(ctx)", lambda: a.perform(ctx))
    api_case("concat_list", "perform_substitutions(ctx, [a, b])",
             lambda: perform_substitutions(ctx, normalize_to_list_of_substitutions([a, b])))
    api_case("concat_list_with_text", "perform_substitutions(ctx, ['robot_', a, b])",
             lambda: perform_substitutions(ctx, normalize_to_list_of_substitutions(["robot_", a, b])))

    # 3) PythonExpression: 연결한 뒤 eval
    api_case("pyexpr_no_operator", "PythonExpression([a, b])", lambda: PythonExpression([a, b]).perform(ctx))
    api_case("pyexpr_plus", "PythonExpression([a, ' + ', b])",
             lambda: PythonExpression([a, " + ", b]).perform(ctx))
    api_case("pyexpr_scale", "PythonExpression([idx, ' * 1.5'])",
             lambda: PythonExpression([idx, " * 1.5"]).perform(ctx))
    api_case("pyexpr_string_no_quotes", "PythonExpression([name, \" == 'robot1'\"])",
             lambda: PythonExpression([name, " == 'robot1'"]).perform(ctx))
    api_case("pyexpr_string_quoted", "PythonExpression([\"'\", name, \"' == 'robot1'\"])",
             lambda: PythonExpression(["'", name, "' == 'robot1'"]).perform(ctx))

    # 4) IfCondition: true/1/false/0 문자열만 받는다
    api_case("if_compare_200", "IfCondition(PythonExpression([r, ' == 200', ' and ', u])), r='200'",
             lambda: IfCondition(PythonExpression([r, " == 200", " and ", u])).evaluate(ctx))
    ctx_199 = context(a="2", b="5", r="199", u="True")
    api_case("if_compare_199", "IfCondition(PythonExpression([r, ' == 200', ' and ', u])), r='199'",
             lambda: IfCondition(PythonExpression([r, " == 200", " and ", u])).evaluate(ctx_199))
    api_case("if_raw_200", "IfCondition(LaunchConfiguration('r')), r='200'",
             lambda: IfCondition(r).evaluate(ctx))
    for raw in ("1", " TRUE ", "yes"):
        api_case(f"if_raw_{raw.strip().lower()}", f"IfCondition(LaunchConfiguration('r')), r={raw!r}",
                 lambda raw=raw: IfCondition(r).evaluate(context(r=raw)))

    # 5) Node 파라미터 경로: 연결된 문자열을 YAML로 읽어 타입이 정해진다
    def params(spec):
        evaluated = evaluate_parameters(ctx, normalize_parameters([spec]))
        return {k: (v, type(v).__name__) for item in evaluated for k, v in item.items()}

    api_case("param_concat", "parameters=[{'offset': [a, b]}]", lambda: params({"offset": [a, b]}))
    api_case("param_pyexpr_plus", "parameters=[{'offset': PythonExpression([a, ' + ', b])}]",
             lambda: params({"offset": PythonExpression([a, " + ", b])}))
    api_case("param_pyexpr_scale", "parameters=[{'scale': PythonExpression([idx, ' * 1.5'])}]",
             lambda: params({"scale": PythonExpression([idx, " * 1.5"])}))
    api_case("param_value_str", "parameters=[{'offset': ParameterValue([a, b], value_type=str)}]",
             lambda: params({"offset": ParameterValue([a, b], value_type=str)}))


LAUNCH_FILE = r'''
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def opaque(context):
    a = LaunchConfiguration('a').perform(context)
    b = LaunchConfiguration('b').perform(context)
    return [LogInfo(msg=f'OUT opaque_types={type(a).__name__},{type(b).__name__}'),
            LogInfo(msg=f'OUT opaque_sum={int(a) + int(b)}')]


def generate_launch_description():
    a, b = LaunchConfiguration('a'), LaunchConfiguration('b')
    idx, r, u = LaunchConfiguration('idx'), LaunchConfiguration('r'), LaunchConfiguration('u')
    print(f'PLAN_TIME type={type(a).__name__} is_str={isinstance(a, str)}', flush=True)
    return LaunchDescription([
        DeclareLaunchArgument('a', default_value='2'),
        DeclareLaunchArgument('b', default_value='5'),
        DeclareLaunchArgument('idx', default_value='2'),
        DeclareLaunchArgument('r', default_value='200'),
        DeclareLaunchArgument('u', default_value='True'),
        LogInfo(msg=['OUT concat=', a, b]),
        LogInfo(msg=['OUT pyexpr_no_operator=', PythonExpression([a, b])]),
        LogInfo(msg=['OUT pyexpr_sum=', PythonExpression([a, ' + ', b])]),
        OpaqueFunction(function=opaque),
        LogInfo(msg='OUT if_branch=ran', condition=IfCondition(PythonExpression([r, ' == 200', ' and ', u]))),
        # /tmp는 noexec tmpfs라서 스크립트를 직접 실행하지 않고 python3의 인자로 넘긴다.
        Node(executable='python3', arguments=['/tmp/param_probe.py'], name='param_probe', output='screen', parameters=[{
            'offset_concat': [a, b],
            'offset_sum': PythonExpression([a, ' + ', b]),
            'scale': PythonExpression([idx, ' * 1.5']),
            'offset_str': ParameterValue([a, b], value_type=str),
        }]),
    ])
'''

PROBE_NODE = r'''import json
import sys

import rclpy
from rclpy.node import Node

rclpy.init(args=sys.argv)
node = Node('param_probe', automatically_declare_parameters_from_overrides=True)
report = {}
for name in ('offset_concat', 'offset_sum', 'scale', 'offset_str'):
    p = node.get_parameter(name)
    report[name] = {'value': p.value, 'ros_type': p.type_.name, 'py_type': type(p.value).__name__}
print('PROBE ' + json.dumps(report), flush=True)
node.destroy_node()
rclpy.shutdown()
'''


def part_b():
    with open("/tmp/args_demo.launch.py", "w") as fh:
        fh.write(LAUNCH_FILE)
    with open("/tmp/param_probe.py", "w") as fh:
        fh.write(PROBE_NODE)

    for label, extra in (("default", []), ("cli_override", ["a:=3", "b:=4", "r:=199"])):
        cmd = ["ros2", "launch", "/tmp/args_demo.launch.py", *extra]
        started = time.monotonic()
        try:
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            code, out, err = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as exc:
            code, out, err = "timeout", exc.stdout or "", exc.stderr or ""
            out = out.decode() if isinstance(out, bytes) else out
            err = err.decode() if isinstance(err, bytes) else err
        seconds = round(time.monotonic() - started, 3)
        text = out + "\n" + err
        logs = dict(re.findall(r"OUT (\w+)=(\S+)", text))
        plan_line = re.search(r"PLAN_TIME (.*)", text)
        probe = re.search(r"PROBE (\{.*\})", text)
        emit(part="B", case=f"ros2_launch_{label}", command=" ".join(cmd[1:]), exit_code=code, seconds=seconds,
             plan_time=plan_line.group(1).strip() if plan_line else None,
             logs=logs, if_branch_ran="if_branch" in logs,
             node_params=json.loads(probe.group(1)) if probe else None,
             log_lines=[line.strip() for line in text.splitlines() if "OUT " in line or "PROBE " in line],
             process_lines=[line.strip()[:300] for line in text.splitlines()
                            if "param_probe" in line and "PROBE " not in line or "ERROR" in line][:12],
             stderr_tail=err[-600:] if code != 0 else "")


def main():
    emit(part="env", python=platform.python_version(), ros_distro=os.environ.get("ROS_DISTRO"),
         rmw=os.environ.get("RMW_IMPLEMENTATION", "default"))
    part_a()
    part_b()
    return 0


if __name__ == "__main__":
    sys.exit(main())
