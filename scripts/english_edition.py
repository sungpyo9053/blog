"""English edition: written from the same research and measured data, gated, then scheduled
in the same slot as its Korean counterpart. Never a machine translation; never blocks Korean."""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.experiment_runner import check_measured_section


def _prompt(topic_dir: Path, slug: str) -> str:
    out = topic_dir / "en"
    return (
        "Write the English edition of this article for English-speaking ROS 2 developers who search "
        "for this problem. It is not a translation: decide what an English reader needs and write natural, "
        "plain English from these inputs. Facts and source URLs: "
        f"{str(topic_dir / 'research.md')!r}. Measurements (real harness runs): "
        f"{str(topic_dir / 'experiment' / 'results.json')!r}, the plan and predictions: "
        f"{str(topic_dir / 'experiment' / 'plan.md')!r}. The Korean article "
        f"{str(topic_dir / 'final.md')!r} is only a reference for scope. "
        "Open with what happened when it was actually run. Put measured values, the prediction they are "
        "compared with, a few raw output lines and the environment (image, RMW, versions, number of runs) "
        "between <!-- measured:start --> and <!-- measured:end -->; keep derived numbers and interpretation "
        "outside that block. Inside it, use only numbers present in results.json, experiment.py or plan.md. "
        "Separate interpretation from measurement and state limits. Every URL must be a complete file URL "
        f"(no directory URLs, no shell variables). Link the reproduction code at "
        f"https://github.com/sungpyo9053/blog/tree/main/experiments/{slug} . "
        f"Save the HTML body (h2 and below, no h1, no front matter) to {str(out / 'article.html')!r} and "
        f"{str(out / 'meta.json')!r} as JSON with exactly title, slug (lowercase ASCII words joined by hyphens) "
        "and excerpt (one sentence, at most 160 characters). This edition is the main search entry point: "
        "the title must contain the words an English developer types into Google for this problem (the exact "
        "error message or command when there is one, plus 'ROS 2'), front-loaded and under 65 characters; the "
        "slug uses those same words; the excerpt states the concrete answer, not a teaser. "
        "Do not write anything else."
    )


def _meta(topic_dir: Path) -> dict:
    meta = json.loads((topic_dir / "en" / "meta.json").read_text(encoding="utf-8"))
    if (set(meta) != {"title", "slug", "excerpt"} or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", meta["slug"])
            or not meta["title"].strip() or len(meta["excerpt"]) > 160):
        raise ValueError("english_meta_invalid")
    return meta


def write_english(topic_dir: Path, slug: str, logger, *, runner=None) -> Path | None:
    """Run the English writer once; return the gated article path, or None when there is no experiment."""
    topic_dir = Path(topic_dir)
    if not (topic_dir / "experiment" / "results.json").is_file():
        return None
    (topic_dir / "en").mkdir(exist_ok=True)
    if runner is None:
        from scripts.run_daily_pipeline import Stage, resolve_codex, run_stage
        runner = lambda prompt: run_stage(resolve_codex(), Stage("English Writer Agent", None, prompt), logger,
                                          timeout_seconds=1800, topic=slug)
    article = topic_dir / "en" / "article.html"
    prompt = _prompt(topic_dir, slug)
    try:
        for attempt in (1, 2):
            runner(prompt)
            problems = check_measured_section(article.read_text(encoding="utf-8"), topic_dir)
            if not problems:
                break
            if attempt == 2:
                raise ValueError("english_measured_gate:" + ",".join(problems[:5]))
            # One targeted retry: usually a derived number slipped inside the measured block.
            prompt += (f" Your previous {str(article)!r} failed the measured-number gate: {', '.join(problems[:5])}. "
                       "Move derived numbers and explanations outside the measured block (or remove them) and save again.")
        _meta(topic_dir)
    except Exception:
        # A rejected draft must not be picked up by schedule_english later.
        if article.exists():
            article.rename(article.with_name("article.rejected.html"))
        raise
    return article


def schedule_english(topic_dir: Path, ko_post_id: int, slot, client) -> int | None:
    """Create the English post as WordPress 'future' in the Korean slot; None when no gated English exists."""
    article = Path(topic_dir) / "en" / "article.html"
    if not article.is_file():
        return None
    meta = _meta(Path(topic_dir))
    post = client.request("POST", "hunt_en", payload={
        "title": meta["title"], "content": article.read_text(encoding="utf-8"), "excerpt": meta["excerpt"],
        "slug": meta["slug"], "status": "future", "date": slot.strftime("%Y-%m-%dT%H:%M:%S"),
        "meta": {"ko_post_id": int(ko_post_id)}}, expected=(201,))
    return post["id"]
