#!/usr/bin/env python3
"""Migrate HuntLab's public taxonomy and brand to Hunt News without deleting posts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


ACTIVE_CATEGORIES = {
    "life": {
        "name": "생활",
        "description": "교통, 주거, 건강, 교육, 소비와 공공서비스 변화가 내 생활에 미치는 영향을 설명합니다.",
    },
    "economy": {
        "name": "경제",
        "description": "금리, 물가, 세금, 보험료와 에너지 가격이 내 지갑과 선택에 만드는 변화를 설명합니다.",
    },
    "real-estate": {
        "name": "부동산",
        "description": "전월세, 청약, 대출 규제, 세금과 정비사업 변화가 내 계약·현금흐름·거주 선택에 미치는 영향을 설명합니다.",
    },
    "society": {
        "name": "사회",
        "description": "노동, 복지, 안전과 제도의 변화가 누구에게 언제 적용되는지 설명합니다.",
    },
    "politics": {
        "name": "정치",
        "description": "법안과 정책 원문, 찬반의 근거와 전제를 나누고 내 권리와 생활에 미치는 영향을 설명합니다.",
    },
    "culture-entertainment": {
        "name": "문화·엔터",
        "description": "콘텐츠, 공연, 방송, 계약과 플랫폼 변화가 내 소비와 선택에 미치는 영향을 설명합니다.",
    },
    "it": {
        "name": "IT",
        "description": "AI, 앱, 플랫폼과 시스템의 변화를 사용자 행동에서 시작해 쉬운 말로 설명합니다.",
    },
}

LEGACY_IT_SLUGS = {
    "tech",
    "ai",
    "ml-algorithms",
    "harness-engineering",
    "system-architecture",
    "build-log",
}


def fetch_all(client: WordPressClient, endpoint: str, **query: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        params = {"per_page": "100", "page": str(page), **query}
        try:
            batch = client.request(
                "GET", f"{endpoint}?{urlencode(params)}", expected=(200,)
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) == 400 and page > 1:
                break
            raise
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return rows


def classify_hot_issue(title: str) -> str:
    normalized = re.sub(r"\s+", " ", title).casefold()
    if re.search(
        r"\b(?:ai|next\.js|waf|api|sdk|cloudflare|github|docker|python|wordpress)\b|"
        r"보안|취약점|패치|인프라|서버|코드|모델 평가|권한 격리|시스템",
        normalized,
    ):
        return "it"
    if re.search(r"부동산|아파트|주택|전세|월세|청약|재건축|재개발|임대차", normalized):
        return "real-estate"
    if re.search(r"금리|물가|가격|보험료|세금|gdp|유가|석유|주유|대출|환율", normalized):
        return "economy"
    if re.search(r"국회|법안|정당|선거|대통령|총리|헌법|정부조직", normalized):
        return "politics"
    if re.search(r"영화|드라마|공연|음악|연예|ott|방송|콘서트|웹툰", normalized):
        return "culture-entertainment"
    if re.search(r"노동|복지|안전|인구|고용|조사|폭염|재난", normalized):
        return "society"
    return "life"


def safe_post_snapshot(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": post["id"],
        "status": post.get("status"),
        "slug": post.get("slug"),
        "link": post.get("link"),
        "title": post.get("title", {}).get("raw", ""),
        "categories": post.get("categories", []),
        "modified_gmt": post.get("modified_gmt"),
    }


def build_plan(
    posts: list[dict[str, Any]], categories: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id = {int(row["id"]): row for row in categories}
    by_slug = {str(row["slug"]): row for row in categories}
    targets = {
        slug: {**spec, "id": by_slug.get(slug, {}).get("id")}
        for slug, spec in ACTIVE_CATEGORIES.items()
    }
    legacy_it_ids = {
        int(by_slug[slug]["id"]) for slug in LEGACY_IT_SLUGS if slug in by_slug
    }
    hot_issue_id = int(by_slug["hot-issue"]["id"]) if "hot-issue" in by_slug else None
    updates: list[dict[str, Any]] = []

    for post in posts:
        old_ids = [int(value) for value in post.get("categories", [])]
        old_slugs = [str(by_id[value]["slug"]) for value in old_ids if value in by_id]
        target_slug: str | None = None
        if legacy_it_ids.intersection(old_ids):
            target_slug = "it"
        elif hot_issue_id is not None and hot_issue_id in old_ids:
            target_slug = classify_hot_issue(post.get("title", {}).get("raw", ""))

        if target_slug is None:
            continue
        updates.append(
            {
                "id": int(post["id"]),
                "slug": str(post.get("slug", "")),
                "link": str(post.get("link", "")),
                "title": post.get("title", {}).get("raw", ""),
                "old_category_ids": old_ids,
                "old_category_slugs": old_slugs,
                "target_slug": target_slug,
            }
        )
    return updates, targets


def write_backup(
    directory: Path,
    *,
    posts: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    settings: dict[str, Any],
    plan: list[dict[str, Any]],
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"hunt-news-migration-{timestamp}.json"
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "posts": [safe_post_snapshot(post) for post in posts],
        "categories": categories,
        "pages": pages,
        "settings": settings,
        "plan": plan,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def ensure_categories(
    client: WordPressClient, categories: list[dict[str, Any]]
) -> dict[str, int]:
    by_slug = {str(row["slug"]): row for row in categories}
    ids: dict[str, int] = {}
    for slug, spec in ACTIVE_CATEGORIES.items():
        existing = by_slug.get(slug)
        payload = {
            "name": spec["name"],
            "slug": slug,
            "description": spec["description"],
        }
        if existing:
            row = client.request(
                "POST", f"categories/{existing['id']}", payload=payload, expected=(200,)
            )
        else:
            row = client.request(
                "POST", "categories", payload=payload, expected=(200, 201)
            )
        ids[slug] = int(row["id"])
    return ids


ABOUT_HTML = """
<p><strong>Hunt News는 복잡한 변화가 내 생활에 어떤 영향을 주는지 쉽게 설명합니다.</strong></p>
<p>정책, 경제, 부동산, 사회, 정치, 문화·엔터와 IT의 변화를 발표 제목으로 끝내지 않습니다. 무엇이 바뀌었는지, 누구에게 언제부터 적용되는지, 내 돈·시간·일·권리·소비·선택에는 무엇이 달라지는지, 지금 무엇을 확인해야 하는지까지 이어서 설명합니다.</p>
<h2>우리가 확인하는 것</h2>
<ul><li>정부·공공기관·법령·공시·당사자 원문</li><li>적용 대상, 시행일, 예외와 아직 확정되지 않은 부분</li><li>금액 계산의 공식 산식과 입력 조건</li><li>찬반 쟁점의 주장, 근거, 전제와 확인된 사실의 차이</li></ul>
<h2>주제는 어떻게 고르나</h2>
<p>Whereispost의 PC·모바일 검색량, 문서 수와 경쟁 비율은 사람들이 실제로 궁금해하는 표현을 찾는 수요 신호로 사용합니다. 해당 수치를 사실 근거로 쓰지는 않으며, 본문의 정책·가격·시점은 공식 원문으로 다시 검증합니다.</p>
<h2>AI는 어디까지 사용하나</h2>
<p>AI는 조사 정리와 초안 작성을 보조합니다. Research가 원문과 한계를 남기고, Writer가 그 범위 안에서 설명하며, Reviewer가 사실·용어·생활 영향·이미지·발행 계약을 승인한 글만 공개합니다. 확인하지 못한 경험이나 숫자는 만들지 않습니다.</p>
<h2>기존 기술 글</h2>
<p>HuntLab에서 발행한 기존 기술 글은 삭제하지 않고 IT 카테고리에 보존합니다. 앞으로는 기술 자체보다 일반 사용자가 겪는 변화와 선택을 먼저 설명하고, 필요한 독자에게 작동 원리와 시스템 설계를 깊이 보기로 연결합니다.</p>
""".strip()


def apply_migration(
    client: WordPressClient,
    *,
    categories: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    updates: list[dict[str, Any]],
) -> dict[str, Any]:
    category_ids = ensure_categories(client, categories)
    changed_posts: list[int] = []
    for update in updates:
        post_id = update["id"]
        before = client.get_post(post_id)
        before_slug = str(before.get("slug", ""))
        before_link = str(before.get("link", ""))
        client.update_post(
            post_id,
            {"categories": [category_ids[update["target_slug"]]]},
            status=str(before.get("status", "publish")),
        )
        after = client.get_post(post_id)
        if int(after["id"]) != post_id or str(after.get("slug", "")) != before_slug:
            raise RuntimeError(f"post {post_id}: identity changed during migration")
        if before_link and str(after.get("link", "")) != before_link:
            raise RuntimeError(f"post {post_id}: permalink changed during migration")
        if after.get("categories") != [category_ids[update["target_slug"]]]:
            raise RuntimeError(f"post {post_id}: category verification failed")
        changed_posts.append(post_id)

    client.request(
        "POST",
        "settings",
        payload={
            "title": "Hunt News",
            "description": "복잡한 변화가 내 생활에 어떤 영향을 주는지 쉽게 설명합니다.",
        },
        expected=(200,),
    )

    about = next((page for page in pages if page.get("slug") == "about"), None)
    if about:
        client.request(
            "POST",
            f"pages/{about['id']}",
            payload={"title": "Hunt News 소개", "content": ABOUT_HTML, "status": "publish"},
            expected=(200,),
        )
    else:
        about = client.request(
            "POST",
            "pages",
            payload={
                "title": "Hunt News 소개",
                "slug": "about",
                "content": ABOUT_HTML,
                "status": "publish",
            },
            expected=(200, 201),
        )

    return {
        "changed_post_ids": changed_posts,
        "category_ids": category_ids,
        "about_page_id": int(about["id"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--backup-dir", type=Path, default=ROOT / "output" / "backups" / "hunt-news"
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    if args.apply and not args.yes:
        parser.error("--apply requires --yes")

    client = WordPressClient(WordPressConfig.from_environment(args.env_file))
    categories = fetch_all(client, "categories", context="edit", hide_empty="false")
    posts = fetch_all(client, "posts", context="edit", status="publish")
    posts.extend(fetch_all(client, "posts", context="edit", status="draft"))
    pages = fetch_all(client, "pages", context="edit", status="publish")
    pages.extend(fetch_all(client, "pages", context="edit", status="draft"))
    settings = client.request("GET", "settings", expected=(200,))
    updates, targets = build_plan(posts, categories)
    backup_path = write_backup(
        args.backup_dir,
        posts=posts,
        categories=categories,
        pages=pages,
        settings=settings,
        plan=updates,
    )
    result: dict[str, Any] = {
        "mode": "apply" if args.apply else "plan",
        "backup_path": str(backup_path),
        "post_count": len(posts),
        "planned_post_updates": len(updates),
        "targets": targets,
    }
    if args.apply:
        result["applied"] = apply_migration(
            client, categories=categories, pages=pages, updates=updates
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
