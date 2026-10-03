import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.experiment_runner import ExperimentFailed, check_measured_section, publish_to_repo, run_experiment


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
            (Path(root) / "experiment/plan.md").write_text("예측: 0.055초")
            self.assertEqual(check_measured_section(bad, Path(root)), [])

    def test_publish_mirrors_experiment_into_repo(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as repo:
            run_experiment(topic(root), executor=executor())
            (Path(repo) / "config").mkdir()
            (Path(repo) / "config/physical-ai-discovery.json").write_text("{}")
            calls = []
            publish_to_repo(Path(root), "my-slug", Path(repo), publish=lambda *a: calls.append(a) or "rev")
            self.assertTrue((Path(repo) / "experiments/my-slug/results.json").is_file())
            self.assertIn("https://huntlab.app/my-slug/", (Path(repo) / "experiments/my-slug/README.md").read_text())
            readme = (Path(repo) / "experiments/my-slug/README.md").read_text()
            self.assertIn("--cpus 1 --memory 1g", readme)
            digest = json.loads((Path(root) / "experiment/results.json").read_text())["environment"]["image_digest"]
            self.assertIn(digest or "ros:jazzy-ros-base", readme)
            self.assertEqual(calls[0][1][0], "experiments/my-slug/experiment.py")

    def test_publish_skips_when_already_committed(self):
        import subprocess
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as repo:
            run_experiment(topic(root), executor=executor())
            (Path(repo) / "config").mkdir()
            (Path(repo) / "config/physical-ai-discovery.json").write_text("{}")
            publish_to_repo(Path(root), "s", Path(repo), publish=lambda *a: "rev")
            git = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)
            git("init", "-q"); git("add", "."); git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")
            calls = []
            self.assertIsNone(publish_to_repo(Path(root), "s", Path(repo), publish=lambda *a: calls.append(a)))
            self.assertEqual(calls, [])

    def test_reader_signals_split_measured_and_other(self):
        from scripts.run_weekly_editorial import reader_signals
        ga4 = {"periods": {"current": {"pages": [{"page": "/a/", "sessions": 10, "engagedSessions": 8},
                                                  {"page": "/b/", "sessions": 10, "engagedSessions": 4}]}},
               "feedback": {"up": 3, "down": 1}}
        posts = [{"slug": "a", "content": '<h2 id="measured-x">'}, {"slug": "b", "content": "plain"}]
        signals = reader_signals(ga4, posts)
        self.assertEqual(signals["measured"]["engagement_rate"], 0.8)
        self.assertEqual(signals["other"]["engagement_rate"], 0.4)
        self.assertEqual((signals["feedback_up"], signals["feedback_down"]), (3, 1))

    def test_competitor_report_and_kakao_fit_200_chars(self):
        from scripts.experiment_runner import competitor_kakao, competitor_report
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "research.md").write_text(
                "# R\n## 경쟁 글 대비 차별점\n1. https://velog.io/a\n   - 이 글이 더할 것: 포화 구간 실측 " + "가" * 200
                + "\n2. https://www.wikipedia.org/b\n## 다음\n")
            report = competitor_report(Path(root))
            message = competitor_kakao("제목" * 30, "my-slug", report)
            self.assertLessEqual(len(message), 200)
            self.assertIn("velog.io", message)
            self.assertTrue(message.endswith("experiments/my-slug/competitors.md"))
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(competitor_report(Path(root)))


if __name__ == "__main__":
    unittest.main()


class PublisherTitleTests(unittest.TestCase):
    def test_readback_title_prefers_raw_over_texturized_rendered(self):
        from publisher.service import _normalized, _plain_text
        title = "'Message Filter dropping message' 로그"
        stored = {"raw": title, "rendered": "&#8216;Message Filter dropping message&#8217; 로그"}
        self.assertEqual(_normalized(_plain_text(stored)), _normalized(title))
        self.assertEqual(_plain_text({"rendered": "x"}), "x")


class CategoryTests(unittest.TestCase):
    def test_tool_names_with_korean_particles_map_to_frameworks(self):
        from scripts.run_evidence_deep_article import candidate_category
        for title in ("RViz2에서 TF가 안 보일 때", "Gazebo에서 모델이 안 보일 때", "colcon build가 실패할 때"):
            self.assertEqual(candidate_category({"title_seed": title, "problem": ""}), "프레임워크·라이브러리", title)
