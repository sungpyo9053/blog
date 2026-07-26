"""Data models returned by the publisher."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    field: str | None = None


@dataclass
class ValidationReport:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
            "checks": dict(self.checks),
        }


@dataclass
class PublishResult:
    status: str
    action: str
    post_id: int | None
    draft_url: str | None
    published_url: str | None
    validation_report: ValidationReport
    error_report: dict[str, Any] | None
    publish_summary: dict[str, Any]
    audit_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "action": self.action,
            "post_id": self.post_id,
            "draft_url": self.draft_url,
            "published_url": self.published_url,
            "validation_report": self.validation_report.to_dict(),
            "error_report": self.error_report,
            "publish_summary": self.publish_summary,
            "audit_id": self.audit_id,
        }
