#!/usr/bin/env python3
"""rclpy import 성공 여부를 '새 터미널'(환경을 비운 셸)마다 실제로 세어 본다.

하네스는 이미 setup.bash를 source한 상태로 이 스크립트를 실행한다.
그래서 각 경우는 env -i 로 환경을 비운 자식 셸에서 실행해 '방금 연 터미널'을 흉내 낸다.
모든 값은 실행 중에 측정해 JSON 한 줄씩 출력한다.
"""
import glob
import json
import os
import pty
import re
import select
import shutil
import subprocess
import sys
import sysconfig
import termios
import time

DISTRO = os.environ.get("ROS_DISTRO", "jazzy")
PREFIX = f"/opt/ros/{DISTRO}"
PYVER = f"python{sys.version_info.major}.{sys.version_info.minor}"
SITE = f"{PREFIX}/lib/{PYVER}/site-packages"
CLEAN_ENV = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/tmp"}
MARK = "SOURCE_STEP_DONE"
# 표식은 이어 붙여 출력한다: 터미널에 다시 찍힌 명령 원문이 표식으로 오인되지 않게 한다.
IMPORT = "import rclpy, sys; print('RCLPY' + '_OK', rclpy.__file__)"
API = ("import rclpy; rclpy.init(); n = rclpy.create_node('probe_node'); "
       "print('API' + '_OK', n.get_name()); n.destroy_node(); rclpy.shutdown()")


def classify(stderr: str) -> str:
    if "_rclpy_pybind11" in stderr:
        return "c_extension_missing"
    if "No module named 'rclpy'" in stderr:
        return "no_module_rclpy"
    if "Bad substitution" in stderr or "bad substitution" in stderr:
        return "bad_substitution"
    if re.search(r"(can't open|not found|No such file)", stderr):
        return "file_not_found"
    return "none" if not stderr.strip() else "other"


def run_in_pty(argv, env, script, timeout=30):
    """사람이 쓰는 터미널처럼 tty에서 한 줄씩 읽히게 실행한다. stdout·stderr는 한데 섞인다."""
    master, slave = pty.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~termios.ECHO  # 입력 에코 끔
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    proc = subprocess.Popen(argv, env=env, cwd="/tmp", stdin=slave, stdout=slave, stderr=slave,
                            start_new_session=True)
    os.close(slave)
    os.write(master, script.encode())
    chunks, deadline = [], time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([master], [], [], 0.2)
        if ready:
            try:
                data = os.read(master, 4096)
            except OSError:  # 자식이 tty를 닫으면 EIO
                break
            if not data:
                break
            chunks.append(data)
        elif proc.poll() is not None:
            break
    os.close(master)
    code = proc.wait(timeout=5)
    out = b"".join(chunks).decode(errors="replace").replace("\r\n", "\n")
    return code, out, out


def run_case(case, shell, source_cmd, python_cmd, *, clean=True, interactive=False):
    script = (f"{source_cmd}\n" if source_cmd else "") + \
        f'echo "SOURCE_STEP""_DONE PYTHONPATH=${{PYTHONPATH:-}}"\n{python_cmd}\n'
    env = dict(CLEAN_ENV) if clean else dict(os.environ)
    t0 = time.monotonic()
    if interactive:
        # 대화형 셸: 명령을 tty로 한 줄씩 입력하고 마지막에 python의 종료 코드로 셸을 끝낸다.
        code, out, err = run_in_pty([shell, "-i"], env, script + "exit $?\n")
    else:
        done = subprocess.run([shell, "-c", script], env=env, cwd="/tmp", capture_output=True,
                              text=True, timeout=30, stdin=subprocess.DEVNULL)
        code, out, err = done.returncode, done.stdout, done.stderr
    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    pp = re.search(rf"{MARK} PYTHONPATH=(.*)", out)
    pythonpath = pp.group(1).strip() if pp else None
    # 대화형 셸의 프롬프트("$ ", "# ")와 tty 안내, 표식·정상 출력 줄은 오류 줄에서 뺀다.
    err_lines = [ln for ln in re.sub(r"(?m)^(?:[$#] )+", "", err).splitlines()
                 if ln.strip() and "job control turned off" not in ln
                 and MARK not in ln and "RCLPY_OK" not in ln and "API_OK" not in ln]
    import_ok = "RCLPY_OK" in out or "API_OK" in out
    print(json.dumps({
        "kind": "case", "case": case, "shell": shell, "interactive": interactive,
        "clean_env": clean, "source": source_cmd or "(none)",
        "python": "python3 -I" if " -I " in python_cmd else ("python3 api" if "create_node" in python_cmd else "python3"),
        "exit_code": code,
        "shell_survived_source": pp is not None,
        "ros_site_in_pythonpath": bool(pythonpath) and SITE in pythonpath.split(":"),
        "import_ok": import_ok,
        "api_ok": "API_OK" in out,
        "error_class": classify("\n".join(err_lines)),
        "stderr_lines": len(err_lines),
        "stderr_first": err_lines[0][:240] if err_lines else "",
        "stderr_last": err_lines[-1][:240] if err_lines else "",
        # source 단계 오류는 중간 줄(builtin 등)까지 보여야 원인이 읽히므로 모두 남긴다.
        "stderr_all": [ln[:160] for ln in err_lines[:6]] if "Bad substitution" in err else [],
        "elapsed_ms": elapsed_ms,
    }, ensure_ascii=False), flush=True)
    return code == 0 and import_ok


def main():
    started = time.monotonic()
    py_import = f'python3 -c "{IMPORT}"'
    py_isolated = f'python3 -I -c "{IMPORT}"'
    py_api = f'python3 -c "{API}"'
    sh = shutil.which("sh")
    print(json.dumps({"kind": "env", "ros_distro": DISTRO, "python": sys.version.split()[0],
                      "sh_resolves_to": os.path.realpath(sh) if sh else None,
                      "bash": shutil.which("bash"), "zsh": shutil.which("zsh"),
                      "inherited_pythonpath_has_ros": SITE in os.environ.get("PYTHONPATH", "").split(":")},
                     ensure_ascii=False), flush=True)

    # 예측: 성공 = B, D, E, I, J  /  실패 = A, C, C2, F (C2는 셸이 살아남아 python까지 실행)
    cases = [
        ("A_bash_no_source", "bash", "", py_import, {}),
        ("B_bash_setup.bash", "bash", f"source {PREFIX}/setup.bash", py_import, {}),
        ("C_sh_setup.bash", "sh", f". {PREFIX}/setup.bash", py_import, {}),
        ("C2_sh_interactive_setup.bash", "sh", f". {PREFIX}/setup.bash", py_import, {"interactive": True}),
        ("D_sh_setup.sh", "sh", f". {PREFIX}/setup.sh", py_import, {}),
        ("E_bash_setup.sh", "bash", f"source {PREFIX}/setup.sh", py_import, {}),
        ("F_bash_setup.bash_python_-I", "bash", f"source {PREFIX}/setup.bash", py_isolated, {}),
        ("I_bash_no_source_inherited_env", "bash", "", py_import, {"clean": False}),
        ("J_bash_setup.bash_api_init_node", "bash", f"source {PREFIX}/setup.bash", py_api, {}),
    ]
    ok = {}
    for name, shell, src, py, opts in cases:
        ok[name] = run_case(name, shell, src, py, **opts)

    # G/H: C 확장 파일 이름 태그와 rpyutils 메시지가 가리키는 경로
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    rclpy_dir = f"{SITE}/rclpy"
    so_files = sorted(os.path.basename(p) for p in glob.glob(f"{rclpy_dir}/_rclpy_pybind11*.so"))
    tags = sorted({m.group(1) for f in so_files for m in [re.search(r"\.(cpython-\d+)", f)] if m})
    print(json.dumps({
        "kind": "file_check", "case": "G_ext_suffix_match", "ext_suffix": suffix,
        "rclpy_dir": rclpy_dir, "pybind_so_files": so_files, "abi_tags_present": tags,
        "matching_file_exists": os.path.isfile(f"{rclpy_dir}/_rclpy_pybind11{suffix}"),
        "cpython-310_exists": any("cpython-310" in f for f in so_files),
        "cpython-311_exists": any("cpython-311" in f for f in so_files),
    }, ensure_ascii=False), flush=True)
    msg_path = f"{SITE}/_rclpy_pybind11{suffix}"
    print(json.dumps({"kind": "file_check", "case": "H_rpyutils_message_path",
                      "message_path": msg_path, "exists": os.path.exists(msg_path)},
                     ensure_ascii=False), flush=True)

    # K: SHELL 변수와 지금 실행 중인 셸이 다를 수 있음
    probe = subprocess.run(["sh", "-c", 'echo "$SHELL"; readlink /proc/$$/exe'],
                           env=dict(CLEAN_ENV, SHELL="/bin/bash"), capture_output=True, text=True, timeout=10)
    shell_var, running = (probe.stdout.splitlines() + ["", ""])[:2]
    print(json.dumps({"kind": "shell_check", "case": "K_SHELL_vs_running", "SHELL": shell_var,
                      "running_exe": running, "same": os.path.realpath(shell_var) == running},
                     ensure_ascii=False), flush=True)

    print(json.dumps({"kind": "file_check", "case": "L_ros_base_contents",
                      "demo_nodes_py_installed": os.path.isdir(f"{PREFIX}/share/demo_nodes_py"),
                      "ros_bin_python3_exists": os.path.exists(f"{PREFIX}/bin/python3")},
                     ensure_ascii=False), flush=True)

    predicted = {"A_bash_no_source": False, "B_bash_setup.bash": True, "C_sh_setup.bash": False,
                 "C2_sh_interactive_setup.bash": False, "D_sh_setup.sh": True, "E_bash_setup.sh": True,
                 "F_bash_setup.bash_python_-I": False, "I_bash_no_source_inherited_env": True,
                 "J_bash_setup.bash_api_init_node": True}
    fresh = ["A_bash_no_source", "B_bash_setup.bash", "C_sh_setup.bash", "D_sh_setup.sh",
             "E_bash_setup.sh", "F_bash_setup.bash_python_-I"]
    print(json.dumps({
        "kind": "summary",
        "fresh_shell_cases": len(fresh),
        "fresh_shell_import_ok": sum(ok[c] for c in fresh),
        "all_cases": len(ok), "all_import_ok": sum(ok.values()),
        "prediction_matches": sum(ok[c] == predicted[c] for c in ok),
        "mismatched_cases": [c for c in ok if ok[c] != predicted[c]],
        "total_seconds": round(time.monotonic() - started, 2),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
