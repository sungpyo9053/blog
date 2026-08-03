"""HuntLab WordPress navigation structure and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


MENU_NAME = "HuntLab Primary"
MENU_LOCATIONS = ("primary", "mobile")
CATEGORY_ORDER = (
    "Tech",
    "AI",
    "Build Log",
    "Economy",
    "Society",
    "Politics",
    "Hot Issue",
)


@dataclass(frozen=True)
class MenuItemSpec:
    title: str
    url: str
    parent_title: str | None
    menu_order: int


def build_menu_spec(
    base_url: str,
    categories: Mapping[str, Mapping[str, Any]],
) -> tuple[MenuItemSpec, ...]:
    """Build the public menu, omitting editorial categories with no posts."""
    site_url = base_url.rstrip("/")
    items = [MenuItemSpec("카테고리", "#", None, 1)]
    order = 2
    for name in CATEGORY_ORDER:
        category = categories.get(name)
        if not category or int(category.get("count", 0)) <= 0:
            continue
        link = str(category.get("link", "")).strip()
        if not link:
            raise ValueError(f"Category {name!r} is missing its public link")
        items.append(MenuItemSpec(name, link, "카테고리", order))
        order += 1

    items.extend(
        (
            MenuItemSpec("HuntLab 소개", f"{site_url}/about/", None, 20),
            MenuItemSpec(
                "개인정보처리방침",
                f"{site_url}/privacy-policy/",
                None,
                21,
            ),
            MenuItemSpec("문의", f"{site_url}/contact/", None, 22),
            MenuItemSpec(
                "편집 및 AI 활용 원칙",
                f"{site_url}/editorial-policy/",
                None,
                23,
            ),
        )
    )
    return tuple(items)


def raw_title(item: Mapping[str, Any]) -> str:
    value = item.get("title", "")
    if isinstance(value, Mapping):
        value = value.get("raw") or value.get("rendered") or ""
    return " ".join(str(value).split())


def validate_menu_state(
    items: Sequence[Mapping[str, Any]],
    locations: Sequence[str],
    expected: Sequence[MenuItemSpec],
) -> list[str]:
    """Return stable, human-readable drift errors for an existing menu."""
    errors: list[str] = []
    missing_locations = sorted(set(MENU_LOCATIONS) - set(locations))
    if missing_locations:
        errors.append("missing_locations:" + ",".join(missing_locations))

    by_title: dict[str, Mapping[str, Any]] = {}
    duplicate_titles: set[str] = set()
    for item in items:
        title = raw_title(item)
        if title in by_title:
            duplicate_titles.add(title)
        by_title[title] = item
    if duplicate_titles:
        errors.append("duplicate_titles:" + ",".join(sorted(duplicate_titles)))

    expected_titles = {spec.title for spec in expected}
    actual_titles = set(by_title)
    missing_titles = sorted(expected_titles - actual_titles)
    unexpected_titles = sorted(actual_titles - expected_titles)
    if missing_titles:
        errors.append("missing_items:" + ",".join(missing_titles))
    if unexpected_titles:
        errors.append("unexpected_items:" + ",".join(unexpected_titles))

    for spec in expected:
        item = by_title.get(spec.title)
        if item is None:
            continue
        if str(item.get("url", "")).rstrip("/") != spec.url.rstrip("/"):
            errors.append(f"url_mismatch:{spec.title}")
        actual_parent = int(item.get("parent") or 0)
        if spec.parent_title is None:
            if actual_parent != 0:
                errors.append(f"parent_mismatch:{spec.title}")
        else:
            expected_parent = by_title.get(spec.parent_title)
            expected_parent_id = int(expected_parent.get("id") or 0) if expected_parent else 0
            if not expected_parent_id or actual_parent != expected_parent_id:
                errors.append(f"parent_mismatch:{spec.title}")
    return errors
