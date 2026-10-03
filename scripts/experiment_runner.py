#!/usr/bin/env python3
"""Run an article's ROS 2 experiment in a sealed container and gate measured numbers.

The Experiment Agent only writes ``experiment/experiment.py``; this harness runs it,
so the numbers an article reports come from real executions, not from the model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

IMAGE = "ros:jazzy-ros-base"
RUNS = 5
MIN_OK_RUNS = 3
RUN_TIMEOUT = 180
MEASURED = re.compile(r"<!--\s*measured:start\s*-->(.*?)<!--\s*measured:end\s*-->", re.S)
YEAR = re.compile(r"(?:19|20)\d\d")
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)+|(?<![\w.])\d{3,}(?![\w])")


class ExperimentFailed(RuntimeError):
    pass


def _command(directory: Path) -> list[str]:
    return ["docker", "run", "--rm", "--network", "none", "--memory", "1g", "--cpus", "1",
            "--pids-limit", "256", "--tmpfs", "/tmp", "-e", "HOME=/tmp", "-e", "ROS_LOG_DIR=/tmp",
            "-v", f"{directory.resolve()}:/work:ro", IMAGE, "bash", "-c",
            "source /opt/ros/jazzy/setup.bash && cd /tmp && python3 /work/experiment.py"]


def _environment(executor) -> dict:
    probe = executor(["docker", "run", "--rm", "--network", "none", IMAGE, "bash", "-c",
                      "source /opt/ros/jazzy/setup.bash && echo $ROS_DISTRO && python3 --version && "
                      "dpkg-query -W -f='${Version}' ros-jazzy-rclpy"],
                     capture_output=True, text=True, timeout=120)
    lines = probe.stdout.split()
    digest = executor(["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", IMAGE],
                      capture_output=True, text=True, timeout=30).stdout.strip()
    return {"image": IMAGE, "image_digest": digest, "ros_distro": lines[0] if lines else "",
            "python": " ".join(lines[1:3]), "rclpy": lines[3] if len(lines) > 3 else "",
            "rmw": "rmw_fastrtps_cpp (default)", "network": "none", "limits": "1 CPU, 1 GiB"}


def run_experiment(topic_dir: Path, *, runs: int = RUNS, executor=subprocess.run) -> dict:
    directory = Path(topic_dir) / "experiment"
    script = directory / "experiment.py"
    if not script.is_file() or not (directory / "plan.md").is_file():
        raise ExperimentFailed("experiment.py 또는 plan.md 누락")
    results = []
    for index in range(1, runs + 1):
        started = time.monotonic()
        try:
            done = executor(_command(directory), capture_output=True, text=True, timeout=RUN_TIMEOUT)
            code, out, err = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired:
            code, out, err = -1, "", f"timeout after {RUN_TIMEOUT}s"
        results.append({"run": index, "exit_code": code, "seconds": round(time.monotonic() - started, 2),
                        "stdout": out[-8000:], "stderr_tail": err[-1500:]})
    record = {"script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
              "environment": _environment(executor), "runs": results,
              "ok_runs": sum(r["exit_code"] == 0 and r["stdout"].strip() != "" for r in results)}
    (directory / "results.json").write_text(json.dumps(record, ensure_ascii=False, indent=1))
    if record["ok_runs"] < min(MIN_OK_RUNS, runs):
        raise ExperimentFailed(f"성공 실행 {record['ok_runs']}/{runs}회")
    return record


def _normalize(token: str) -> str:
    return token.rstrip("0").rstrip(".") if "." in token else token


def allowed_numbers(topic_dir: Path) -> set[str]:
    directory = Path(topic_dir) / "experiment"
    record = json.loads((directory / "results.json").read_text())
    # plan.md holds the predictions written before the run; those are declared, not invented.
    plan = directory / "plan.md"
    corpus = (directory / "experiment.py").read_text() + json.dumps(record, ensure_ascii=False) + (
        plan.read_text() if plan.is_file() else "")
    return {_normalize(n) for n in NUMBER.findall(corpus)}


def check_measured_section(article: str, topic_dir: Path) -> list[str]:
    """Return problems; an empty list means every measured number exists in real output."""
    sections = MEASURED.findall(article)
    if not sections:
        return ["measured_section_missing"]
    allowed = allowed_numbers(topic_dir)
    unknown = sorted({n for s in sections for n in NUMBER.findall(s)
                      if _normalize(n) not in allowed and not YEAR.fullmatch(n)})
    return [f"unmeasured_number:{n}" for n in unknown]


def competitor_report(topic_dir: Path) -> str | None:
    """The research '## 경쟁 글 대비 차별점' section, or None when the research has none."""
    research = Path(topic_dir) / "research.md"
    if not research.is_file():
        return None
    found = re.search(r"(?ms)^## 경쟁 글 대비 차별점\s*$\n(.*?)(?=^##\s|\Z)", research.read_text(encoding="utf-8"))
    return found.group(1).strip() if found else None


def competitor_kakao(title: str, slug: str, report: str) -> str:
    """<=200 chars: compared hosts, the first thing only we add, and the full report link."""
    hosts = list(dict.fromkeys(re.findall(r"https?://(?:www\.)?([^/\s)]+)", report)))[:4]
    adds = re.findall(r"이 글이 더할 것\s*[:：]\s*(.+)", report)
    link = f"github.com/sungpyo9053/blog/blob/main/experiments/{slug}/competitors.md"
    head = f"[HuntLab 새 글·경쟁비교] {title[:30]}\n경쟁 {len(hosts)}곳: {', '.join(h[:18] for h in hosts)}\n우리만: "
    room = 200 - len(head) - len(link) - 1
    return head + (adds[0] if adds else "기록 없음")[:max(room, 0)] + "\n" + link


def _pinned_image(directory: Path) -> str:
    """The exact image digest the harness ran, so readers reproduce the same environment."""
    record = json.loads((directory / "results.json").read_text())
    return record.get("environment", {}).get("image_digest") or IMAGE


def publish_to_repo(topic_dir: Path, slug: str, repo: Path, publish=None) -> str | None:
    """Mirror a finished experiment into the public repo under experiments/<slug>/ and push it."""
    source = Path(topic_dir) / "experiment"
    if not (source / "results.json").is_file():
        return None
    target = Path(repo) / "experiments" / slug
    target.mkdir(parents=True, exist_ok=True)
    for name in ("experiment.py", "plan.md", "results.json"):
        (target / name).write_bytes((source / name).read_bytes())
    report = competitor_report(topic_dir)
    if report:
        (target / "competitors.md").write_text(f"# 경쟁 글 대비 차별점: {slug}\n\n{report}\n", encoding="utf-8")
    (target / "README.md").write_text(
        f"# {slug}\n\n글: https://huntlab.app/{slug}/\n\n`results.json`은 하네스가 {IMAGE} 컨테이너"
        f"(네트워크 없음)에서 {RUNS}회 실행한 원본 출력과 환경 기록이다.\n\n## 재현\n\n```bash\n"
        f"docker run --rm --network none --cpus 1 --memory 1g -v \"$PWD\":/work {_pinned_image(source)} \\\n"
        "  bash -c \"source /opt/ros/jazzy/setup.bash && python3 /work/experiment.py\"\n```\n")
    names = ["experiment.py", "plan.md", "results.json", "README.md"] + (["competitors.md"] if report else [])
    paths = [f"experiments/{slug}/{name}" for name in names]
    # Already published during the Experiment stage: committing identical bytes would fail.
    if subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", f"experiments/{slug}"],
                      capture_output=True, text=True).stdout.strip() == "" and \
            subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", paths[0]],
                           capture_output=True).returncode == 0:
        return None
    if publish is None:
        from scripts.discover_physical_ai import publish_files as publish
    config = json.loads((Path(repo) / "config/physical-ai-discovery.json").read_text())
    return publish(Path(repo), paths, config, f"Add measured experiment {slug}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic_dir", type=Path)
    parser.add_argument("--try", dest="trial", action="store_true", help="single trial run for the agent")
    args = parser.parse_args()
    try:
        record = run_experiment(args.topic_dir, runs=1 if args.trial else RUNS)
    except ExperimentFailed as exc:
        print(f"FAILED: {exc}")
        results = args.topic_dir / "experiment" / "results.json"
        if results.exists():
            print(results.read_text()[-3000:])
        return 1
    print(json.dumps({"ok_runs": record["ok_runs"], "first_stdout": record["runs"][0]["stdout"][-2000:]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
