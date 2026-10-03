#!/usr/bin/env python3
"""Weekly: add a measured (실측) section to one published Physical AI post that has none.

Experiment Agent writes the script, the harness runs it 5 times in a sealed ROS 2 container,
a writer drafts the section, the measured-number gate checks it, then it is inserted before
"참고 링크" with a backup. One post per run; failures are recorded and never retried blindly.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.experiment_runner import check_measured_section, publish_to_repo, run_experiment

STATE = ROOT / "output/measured-backfill/state.json"
ANCHOR = "<h2>참고 링크</h2>"


def has_measured(content: str) -> bool:
    return "measured:start" in content or 'id="measured-' in content


def pick(posts: list[dict], attempted: dict) -> dict | None:
    """Oldest eligible post first: no measured section yet, never attempted."""
    for post in sorted(posts, key=lambda p: p["post_id"]):
        if not has_measured(post["content"]) and str(post["post_id"]) not in attempted:
            return post
    return None


def insert_section(content: str, section: str) -> str:
    return content.replace(ANCHOR, section.strip() + "\n\n" + ANCHOR, 1) if ANCHOR in content \
        else content.rstrip() + "\n\n" + section.strip() + "\n"


def run(now=None, *, client=None, posts=None, stage=None, executor=None, publish=None, notify=None,
        state_path=STATE, work_root=ROOT / "output/measured-backfill") -> dict:
    from zoneinfo import ZoneInfo
    now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    state = json.loads(state_path.read_text()) if state_path.exists() else {"attempted": {}}
    if client is None:
        from publisher.config import WordPressConfig
        from publisher.wordpress import WordPressClient
        client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    if posts is None:
        from scripts import run_evidence_deep_article as deep
        from scripts.run_weekly_editorial import eligible_posts
        posts = eligible_posts(client, deep.refresh_inventory())
    post = pick(posts, state["attempted"])
    if post is None:
        return {"status": "nothing_to_backfill"}
    work = work_root / f"{post['slug']}-{now.strftime('%Y%m%dT%H%M%S')}"
    (work / "experiment").mkdir(parents=True)
    (work / "research.md").write_text(f"# {post['title']}\n\n{post['content']}", encoding="utf-8")
    anchor_id = f"measured-{now.date().isoformat()}"
    if stage is None:
        from scripts.run_daily_pipeline import Stage, configure_logger, resolve_codex, run_stage
        logger = configure_logger(now.date())
        stage = lambda name, prompt: run_stage(resolve_codex(), Stage(name, None, prompt), logger,
                                               timeout_seconds=1800, topic=post["slug"])
    result = {"post_id": post["post_id"], "slug": post["slug"]}
    try:
        stage("Experiment Agent", (
            f"입력은 이미 공개된 글 {str(work / 'research.md')!r}입니다. 이 글의 핵심 주장을 실제로 확인할 ROS 2 Jazzy "
            "실험 하나를 설계하세요. ros-base 이미지의 rclpy·tf2_ros·std_msgs 등만 쓰고, 네트워크 없이 한 번 실행이 "
            "60초 안에 끝나야 합니다. 측정값은 실행 중에 재서 JSON 줄로 출력하고, 결과 숫자를 코드에 미리 적어 출력하지 "
            f"마세요. 스크립트는 {str(work / 'experiment/experiment.py')!r}, 계획은 {str(work / 'experiment/plan.md')!r}"
            "(질문, 글이 주장한 예측값, 측정 방법, 시행착오)에 저장하세요. 시험 실행은 "
            f"{str(ROOT / '.venv/bin/python')!r} -m scripts.experiment_runner {str(work)!r} --try 로만 하세요."))
        run_experiment(work, **({"executor": executor} if executor else {}))
        stage("Writer Agent", (
            f"공개된 글 {str(work / 'research.md')!r} 끝에 붙일 실측 섹션 하나만 HTML로 써서 {str(work / 'section.html')!r}에 "
            f"저장하세요. 첫 줄은 <h2 id=\"{anchor_id}\">로 시작하는 제목(실측에서 드러난 사실을 담은 문장)입니다. "
            f"입력: {str(work / 'experiment/plan.md')!r}, 하네스가 5회 실행한 {str(work / 'experiment/results.json')!r}. "
            "글의 계산(예측)과 실측을 표로 나란히 두고, 원본 출력 몇 줄과 측정 환경(이미지·RMW·버전·반복 횟수)·한계를 "
            "<!-- measured:start -->와 <!-- measured:end --> 사이에 넣으세요. 이 구간의 숫자는 results.json·experiment.py·"
            "plan.md에 있는 값만 씁니다. 차이의 해석은 구간 밖에, 해석과 측정을 구분해 적으세요. 측정하지 않은 권장값, "
            "결론 예고 문장, URL은 쓰지 마세요(재현 코드 링크는 하네스가 붙입니다). 본문 다른 부분은 바꾸지 않습니다."))
        section = (work / "section.html").read_text(encoding="utf-8")
        problems = check_measured_section(section, work)
        if problems or not section.lstrip().startswith(f'<h2 id="{anchor_id}"') or "http" in section:
            raise ValueError("backfill_gate:" + ",".join(problems[:5] or ["format"]))
        (publish or publish_to_repo)(work, post["slug"], ROOT)
        section += (f'\n<p>재현 코드와 실행별 원본 출력: <a href="https://github.com/sungpyo9053/blog/tree/main/'
                    f'experiments/{post["slug"]}">GitHub</a></p>')
        backup = work / "post-before.html"
        backup.write_text(post["content"], encoding="utf-8")
        client.update_post(post["post_id"], {"content": insert_section(post["content"], section)}, status="publish")
        result.update(status="added", url=post["link"] + "#" + anchor_id, backup=str(backup))
    except Exception as exc:
        result.update(status="failed", reason=f"{type(exc).__name__}:{str(exc)[:80]}")
    state["attempted"][str(post["post_id"])] = {
        "at": now.isoformat(), "status": "added" if result["status"] == "added" else "failed:" + result["reason"]}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    message = (f"[HuntLab 실측 보강] {post['title'][:40]} → " +
               ("추가 완료\n" + result["url"] if result["status"] == "added" else "실패 " + result["reason"][:60]))
    try:
        if notify is None:
            import os
            from scripts.send_kakao_report import send
            notify = lambda text: send(text, os.environ.get("MCPORTER_BIN", "mcporter"))
        notify(message[:200])
    except Exception:
        result["notify"] = "failed"
    return result


def main() -> int:
    from scripts import run_evidence_deep_article as deep
    lock = deep.PipelineLock(deep.LOCK)
    try:
        lock.acquire()
    except deep.PipelineError:
        print(json.dumps({"status": "deferred", "reason": "pipeline_busy"}))
        return 0
    try:
        print(json.dumps(run(), ensure_ascii=False))
    finally:
        lock.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
