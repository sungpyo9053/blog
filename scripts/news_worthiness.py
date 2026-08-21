#!/usr/bin/env python3
"""Deterministic Shadow ranking for Hunt News topic candidates.

The legacy TopicPlanner remains the production selector.  This module only
normalizes its qualitative observations, applies evidence contracts, and
writes a comparable Shadow ranking.  It performs no network or model calls.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CONTRACT_VERSION = "news-worthiness.v1"
SCORER_VERSION = "deterministic.v1"
WEIGHTS_VERSION = "hunt-news.v1"
SELECTION_MODE = "shadow"

FEATURE_WEIGHTS: dict[str, float] = {
    "urgency": 1.0,
    "personal_impact": 2.5,
    "explainability": 2.0,
    "source_confidence": 2.0,
    "search_demand": 1.5,
    "shareability": 2.5,
    "duplication": -4.0,
    "trust_risk": -5.0,
}
EVIDENCE_MULTIPLIERS = {
    "none": 0.0,
    "weak": 0.7,
    "medium": 0.9,
    "strong": 1.0,
}
SCORE_LABELS = {
    "최신성": "urgency",
    "공식 출처": "source_confidence",
    "HuntLab 적합성": "personal_impact",
    "기술적 깊이": "explainability",
    "독창성": "shareability",
}
HIGH_RISK_CATEGORIES = {"정치", "Politics", "경제", "Economy", "부동산"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 4)


def _parse_score_breakdown(value: str) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for item in re.split(r"[;|]", value):
        match = re.match(r"\s*(.+?)\s+(\d+(?:\.\d+)?)\s*$", item)
        if match:
            parsed[match.group(1).strip()] = _clamp_score(float(match.group(2)))
    return parsed


def _urls(value: str) -> list[str]:
    return re.findall(r"https?://[^\s,;)>\]]+", value or "")


def normalize_source_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host if port in {None, 80, 443} else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/").rstrip("/") or "/"
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, val) for key, val in query if not key.lower().startswith("utm_")]
    return urllib.parse.urlunsplit(
        ((parsed.scheme or "https").lower(), netloc, path, urllib.parse.urlencode(sorted(query)), "")
    )


def make_candidate_id(source_url: str, event_identifier: str) -> str:
    identity = f"{normalize_source_url(source_url)}|{' '.join(event_identifier.split()).casefold()}"
    return f"candidate-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"


def make_topic_id(title: str) -> str:
    normalized = " ".join(title.split()).casefold()
    return f"topic-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"


def make_shadow_input_snapshot(
    candidates: Sequence[Mapping[str, Any]], legacy_top2: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Detach Shadow input from all mutable legacy object references."""
    candidate_snapshot = json.loads(_canonical_json(candidates))
    legacy_title_snapshot = tuple(str(item.get("title", "")) for item in legacy_top2)
    return candidate_snapshot, legacy_title_snapshot


def _event_identifier(candidate: Mapping[str, Any]) -> str:
    explicit = str(candidate.get("event_identifier", "")).strip()
    if explicit:
        return explicit
    parts = [
        str(candidate.get("primary_keyword", "")).strip(),
        str(candidate.get("effective_date", "")).strip(),
        str(candidate.get("problem_origin", "")).strip(),
    ]
    return "|".join(part for part in parts if part) or str(candidate.get("title", ""))


def _evidence(
    *, claim: str, source_urls: Sequence[str], strength: str, observed_value: Any = None
) -> dict[str, Any]:
    if not claim.strip() and observed_value is None:
        strength = "none"
    return {
        "claim": claim.strip(),
        "source_urls": list(source_urls),
        "observed_value": observed_value,
        "strength": strength,
    }


@dataclass(frozen=True)
class CandidateEvaluator:
    """Normalize TopicPlanner observations into the V1 feature/evidence contract."""

    def evaluate(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        breakdown = _parse_score_breakdown(str(candidate.get("score_breakdown", "")))
        source_urls = list(
            dict.fromkeys(
                normalize_source_url(url)
                for url in _urls(str(candidate.get("sources", "")))
            )
        )
        primary_source = source_urls[0] if source_urls else ""
        event_identifier = _event_identifier(candidate)
        candidate_id = (
            make_candidate_id(primary_source, event_identifier)
            if primary_source
            else f"candidate-unresolved-{_sha256({'event': event_identifier})[:20]}"
        )

        raw = {name: 0.0 for name in FEATURE_WEIGHTS}
        for legacy_label, feature in SCORE_LABELS.items():
            raw[feature] = breakdown.get(legacy_label, 0.0)

        total_searches = candidate.get("whereispost_total_searches", 0)
        try:
            observed_searches = max(0, int(total_searches))
        except (TypeError, ValueError):
            observed_searches = 0
        # Search demand is derived only from an observed numeric value. The
        # logarithmic cap prevents a single large keyword from dominating.
        raw["search_demand"] = _clamp_score(math.log10(observed_searches + 1) * 2.5)

        duplicate_text = str(candidate.get("duplicate_check", ""))
        raw["duplication"] = 10.0 if re.search(r"(?:중복\s*(?:있음|확인)|duplicate)", duplicate_text, re.I) else 0.0
        raw["trust_risk"] = _clamp_score(10.0 - raw["source_confidence"])

        life_claim = " ".join(
            str(candidate.get(key, "")).strip()
            for key in (
                "affected_reader",
                "life_impact",
                "reader_action",
                "observed_problem_phrase",
                "user_action",
            )
            if str(candidate.get(key, "")).strip()
        )
        evidence = {
            "urgency": _evidence(
                claim=str(candidate.get("effective_date", candidate.get("reason", ""))),
                source_urls=source_urls,
                strength="strong" if source_urls and candidate.get("effective_date") else "medium" if source_urls else "none",
            ),
            "personal_impact": _evidence(
                claim=life_claim,
                source_urls=source_urls,
                strength="strong" if source_urls and life_claim else "none",
            ),
            "explainability": _evidence(
                claim=str(candidate.get("research_focus", "")),
                source_urls=source_urls,
                strength="medium" if source_urls and candidate.get("research_focus") else "none",
            ),
            "source_confidence": _evidence(
                claim=str(candidate.get("sources", "")),
                source_urls=source_urls,
                strength="strong" if len(source_urls) >= 2 else "medium" if source_urls else "none",
            ),
            "search_demand": _evidence(
                claim=str(candidate.get("demand_signal_source", "")),
                source_urls=[],
                observed_value=observed_searches,
                strength="strong" if observed_searches > 0 else "none",
            ),
            "shareability": _evidence(
                claim=str(candidate.get("editorial_thesis", "")),
                source_urls=source_urls,
                strength="medium" if source_urls and candidate.get("editorial_thesis") else "none",
            ),
            "duplication": _evidence(
                claim=duplicate_text,
                source_urls=[],
                strength="strong" if duplicate_text else "none",
            ),
            "trust_risk": _evidence(
                claim=str(candidate.get("sources", "")),
                source_urls=source_urls,
                strength="strong" if source_urls else "none",
            ),
        }
        multipliers = {
            name: EVIDENCE_MULTIPLIERS[item["strength"]]
            for name, item in evidence.items()
        }
        effective = {
            name: round(raw[name] * multipliers[name], 4) for name in FEATURE_WEIGHTS
        }
        snapshot = {
            "source_urls": source_urls,
            "event_identifier": event_identifier,
            "effective_date": candidate.get("effective_date"),
            "observed_searches": observed_searches,
        }
        return {
            "candidate_id": candidate_id,
            "topic_id": candidate.get("topic_id") or make_topic_id(str(candidate.get("title", ""))),
            "post_id": None,
            "title": candidate.get("title"),
            "category": candidate.get("category"),
            "topic_cluster": candidate.get("topic_cluster") or candidate.get("primary_keyword"),
            "contract_version": CONTRACT_VERSION,
            "scorer_version": SCORER_VERSION,
            "weights_version": WEIGHTS_VERSION,
            "source_snapshot_hash": _sha256(snapshot),
            "raw_features": raw,
            "evidence": evidence,
            "evidence_multiplier": multipliers,
            "effective_features": effective,
        }


def apply_hard_filter(record: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    evidence = record["evidence"]
    source_urls = evidence["source_confidence"]["source_urls"]
    if not source_urls:
        reasons.append("official_source_missing")
    if not evidence["personal_impact"]["claim"]:
        reasons.append("reader_outcome_missing")
    if record.get("category") in HIGH_RISK_CATEGORIES and len(source_urls) < 2:
        reasons.append("high_risk_evidence_contract_violation")
    if record["raw_features"]["duplication"] >= 10:
        reasons.append("duplicate_intent")
    if record["evidence"]["urgency"]["strength"] == "none":
        reasons.append("applicable_timing_missing")
    return not reasons, reasons


@dataclass(frozen=True)
class NewsWorthinessScorer:
    weights: Mapping[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.weights is None:
            object.__setattr__(self, "weights", FEATURE_WEIGHTS)

    def score(self, record: Mapping[str, Any]) -> dict[str, Any]:
        passed, reasons = apply_hard_filter(record)
        score_breakdown = {
            name: round(record["effective_features"][name] * weight, 4)
            for name, weight in self.weights.items()
        }
        base_score = round(sum(score_breakdown.values()), 4) if passed else 0.0
        return {
            **record,
            "hard_filter_result": "pass" if passed else "reject",
            "hard_filter_reasons": reasons,
            "score_breakdown": score_breakdown,
            "base_score": base_score,
        }


@dataclass(frozen=True)
class TopicReranker:
    repeat_decay: float = 0.7

    def rank(self, records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        remaining = [dict(record) for record in records if record["hard_filter_result"] == "pass"]
        ranked: list[dict[str, Any]] = []
        selected_clusters: dict[str, int] = {}
        while remaining:
            choices: list[tuple[float, str, dict[str, Any], float, int]] = []
            for record in remaining:
                cluster = str(record.get("topic_cluster") or "").strip().casefold()
                prior_count = selected_clusters.get(cluster, 0)
                decay = self.repeat_decay ** prior_count
                final_score = round(record["base_score"] * decay, 4)
                choices.append((final_score, str(record["candidate_id"]), record, decay, prior_count))
            _, _, chosen, decay, prior_count = max(choices, key=lambda item: (item[0], item[1]))
            cluster = str(chosen.get("topic_cluster") or "").strip().casefold()
            selected_clusters[cluster] = prior_count + 1
            ranked.append(
                {
                    **chosen,
                    "topic_decay": {
                        "factor": round(decay, 4),
                        "prior_selected_in_cluster": prior_count,
                        "cluster": chosen.get("topic_cluster"),
                    },
                    "topic_decay_applied": prior_count > 0,
                    "final_score": round(chosen["base_score"] * decay, 4),
                    "rank": len(ranked) + 1,
                    "selection_mode": SELECTION_MODE,
                }
            )
            remaining.remove(chosen)
        return ranked


def build_shadow_diff(
    candidates: Sequence[Mapping[str, Any]], legacy_top2: Sequence[str], *, selected_at: str | None = None
) -> dict[str, Any]:
    selected_at = selected_at or datetime.now(UTC).isoformat()
    evaluator = CandidateEvaluator()
    scorer = NewsWorthinessScorer()
    scored = [scorer.score(evaluator.evaluate(candidate)) for candidate in candidates]
    ranked = TopicReranker().rank(scored)
    shadow_top2_records = ranked[:2]
    shadow_titles = [str(record["title"]) for record in shadow_top2_records]
    legacy_titles = [str(title) for title in legacy_top2]
    aggregate_snapshot_hash = _sha256(sorted(record["source_snapshot_hash"] for record in scored))
    evidence_missing = {
        str(record["candidate_id"]): [
            name for name, multiplier in record["evidence_multiplier"].items() if multiplier == 0
        ]
        for record in scored
        if any(multiplier == 0 for multiplier in record["evidence_multiplier"].values())
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "scorer_version": SCORER_VERSION,
        "weights_version": WEIGHTS_VERSION,
        "source_snapshot_hash": aggregate_snapshot_hash,
        "selection_mode": SELECTION_MODE,
        "selected_at": selected_at,
        "legacy_top2": legacy_titles,
        "shadow_top2": shadow_titles,
        "overlap_count": len(set(legacy_titles) & set(shadow_titles)),
        "legacy_only": [title for title in legacy_titles if title not in shadow_titles],
        "shadow_only": [title for title in shadow_titles if title not in legacy_titles],
        "hard_filter_rejections": [
            {
                "candidate_id": record["candidate_id"],
                "title": record["title"],
                "reasons": record["hard_filter_reasons"],
            }
            for record in scored
            if record["hard_filter_result"] == "reject"
        ],
        "evidence_missing": evidence_missing,
        "score_breakdown": {
            str(record["candidate_id"]): record["score_breakdown"] for record in scored
        },
        "topic_decay_applied": [
            {
                "candidate_id": record["candidate_id"],
                "title": record["title"],
                "topic_decay": record["topic_decay"],
            }
            for record in ranked
            if record["topic_decay_applied"]
        ],
        "candidates": scored,
        "ranking": ranked,
    }


def write_shadow_diff(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
