import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.experiment_runner import ExperimentFailed, check_measured_section, run_experiment


def topic(root):
    exp = Path(root) / "experiment"
    exp.mkdir()
    (exp / "experiment.py").write_text("HZ = 10.0\nprint('x')\n")
    (exp / "plan.md").write_text("plan")
    return Path(root)


def executor(stdout='{"count": 4, "arrival_s": 0.075}', code=0):
    def run(command, **_):
        if command[:2] == ["docker", "image"]:
            return SimpleNamespace(returncode=0, stdout="ros@sha256:abc", stderr="")
        if "/work/experiment.py" not in command[-1]:
            return SimpleNamespace(returncode=0, stdout="jazzy Python 3.12.3 9.2.1", stderr="")
        assert "--network" in command and command[command.index("--network") + 1] == "none"
        return SimpleNamespace(returncode=code, stdout=stdout, stderr="")
    return run


class ExperimentRunnerTests(unittest.TestCase):
    def test_runs_five_times_and_records_environment(self):
        with tempfile.TemporaryDirectory() as root:
            record = run_experiment(topic(root), executor=executor())
            self.assertEqual(record["ok_runs"], 5)
            self.assertEqual(record["environment"]["ros_distro"], "jazzy")
            self.assertTrue((Path(root) / "experiment/results.json").is_file())

    def test_too_few_successful_runs_fail(self):
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ExperimentFailed):
            run_experiment(topic(root), executor=executor(code=1))

    def test_timeout_counts_as_failed_run(self):
        def hang(command, **kw):
            if "/work/experiment.py" in command[-1]:
                raise subprocess.TimeoutExpired(command, 1)
            return executor()(command, **kw)
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ExperimentFailed):
            run_experiment(topic(root), executor=hang)

    def test_gate_accepts_measured_numbers_and_rejects_invented_ones(self):
        with tempfile.TemporaryDirectory() as root:
            run_experiment(topic(root), executor=executor())
            ok = "<!-- measured:start -->2026년에 재 보니 0.075초, 10.0 Hz<!-- measured:end -->"
            self.assertEqual(check_measured_section(ok, Path(root)), [])
            bad = "<!-- measured:start -->지연은 0.055초<!-- measured:end -->"
            self.assertEqual(check_measured_section(bad, Path(root)), ["unmeasured_number:0.055"])
            self.assertEqual(check_measured_section("본문만", Path(root)), ["measured_section_missing"])


if __name__ == "__main__":
    unittest.main()
