"""Emit a dated quality-remediation reminder without mutating WordPress content."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from scripts.audit_public_site import audit_site, render_markdown

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "output" / "analytics"
START = date(2026, 8, 10)


def phase(today: date) -> tuple[str, str]:
    if today < START:
        return "SCHEDULED", "wait_for_2026-08-10"
    if today == date(2026, 8, 10):
        return "DUE", "select_and_backup_up_to_five_candidates"
    if date(2026, 8, 10) <= today <= date(2026, 8, 12):
        return "DUE", "review_and_enrich_one_candidate_at_a_time"
    if today == date(2026, 8, 13):
        return "DUE", "review_empty_politics_category_and_navigation"
    if today >= date(2026, 8, 14):
        return "DUE", "run_public_audit_after_approved_changes"
    return "HOLD", "no_mutation_without_evidence_and_reviewer_approval"


def main() -> int:
    now = datetime.now().astimezone()
    status, action = phase(now.date())
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "quality-remediation-schedule.md"
    path.write_text(
        "# Quality remediation schedule\n\n"
        f"- generated_at: `{now.isoformat()}`\n"
        f"- status: `{status}`\n"
        f"- action: `{action}`\n"
        "- automatic_content_mutation: `disabled`\n"
        "- note: select evidence-backed changes, back up, review, then deploy.\n",
        encoding="utf-8",
    )
    if status == "DUE":
        try:
            audit = audit_site("https://huntlab.app/")
            audit_path = REPORT_DIR / "quality-remediation-audit.md"
            audit_path.write_text(render_markdown(audit), encoding="utf-8")
            print(f"quality schedule audit={audit_path}")
        except Exception as exc:  # noqa: BLE001 - reminder must never mutate or block
            error_path = REPORT_DIR / "quality-remediation-audit-error.md"
            error_path.write_text(
                f"# Quality remediation audit\n\n- status: `INCOMPLETE`\n- error_type: `{type(exc).__name__}`\n",
                encoding="utf-8",
            )
            print(f"quality schedule audit=INCOMPLETE error_type={type(exc).__name__}")
    print(f"quality schedule status={status} action={action} report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
