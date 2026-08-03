#!/usr/bin/env python3
"""Safely configure the HuntLab category navigation in WordPress."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import ConfigurationError, WordPressConfig
from publisher.navigation import (
    MENU_LOCATIONS,
    MENU_NAME,
    MenuItemSpec,
    build_menu_spec,
    validate_menu_state,
)
from publisher.wordpress import WordPressClient, WordPressError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure HuntLab desktop and mobile category navigation."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="WordPress environment file (default: repository .env).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create or assign the menu. Without this flag the command is read-only.",
    )
    return parser


def fetch_state(client: WordPressClient) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    menus = client.request(
        "GET", "menus?context=edit&per_page=100", expected=(200,)
    )
    matches = [menu for menu in menus if str(menu.get("name", "")) == MENU_NAME]
    if len(matches) > 1:
        raise RuntimeError(f"Multiple menus named {MENU_NAME!r} exist")
    if not matches:
        return None, []
    menu = matches[0]
    query = urlencode(
        {"context": "edit", "menus": int(menu["id"]), "per_page": 100}
    )
    items = client.request("GET", f"menu-items?{query}", expected=(200,))
    return menu, items


def create_item(
    client: WordPressClient,
    menu_id: int,
    spec: MenuItemSpec,
    parent_id: int,
) -> dict[str, Any]:
    return client.request(
        "POST",
        "menu-items",
        payload={
            "title": spec.title,
            "status": "publish",
            "menus": menu_id,
            "type": "custom",
            "url": spec.url,
            "menu_order": spec.menu_order,
            "parent": parent_id,
        },
        expected=(200, 201),
    )


def write_backup(menu: dict[str, Any] | None, items: list[dict[str, Any]]) -> Path:
    backup_dir = ROOT / "output" / "wordpress-navigation-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    backup_path.write_text(
        json.dumps({"menu": menu, "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.chmod(backup_path, 0o600)
    return backup_path


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = WordPressConfig.from_environment(args.env_file)
        client = WordPressClient(config)
        categories = client.request(
            "GET",
            "categories?per_page=100&hide_empty=true",
            expected=(200,),
        )
        expected = build_menu_spec(
            config.base_url,
            {str(category["name"]): category for category in categories},
        )
        menu, items = fetch_state(client)

        if menu is not None:
            errors = validate_menu_state(items, menu.get("locations", []), expected)
            item_errors = [error for error in errors if not error.startswith("missing_locations:")]
            if item_errors:
                print(
                    json.dumps(
                        {"status": "DriftDetected", "menu_id": menu["id"], "errors": errors},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 1
            if not errors:
                print(
                    json.dumps(
                        {
                            "status": "Success",
                            "action": "AlreadyConfigured",
                            "menu_id": menu["id"],
                            "locations": list(MENU_LOCATIONS),
                            "items": len(items),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 0
            if not args.apply:
                print(json.dumps({"status": "Plan", "action": "AssignLocations", "errors": errors}, ensure_ascii=False, indent=2))
                return 0
            backup = write_backup(menu, items)
            client.request(
                "POST",
                f"menus/{menu['id']}",
                payload={"locations": list(MENU_LOCATIONS)},
                expected=(200,),
            )
            action = "AssignedLocations"
            menu_id = int(menu["id"])
        else:
            if not args.apply:
                print(
                    json.dumps(
                        {
                            "status": "Plan",
                            "action": "CreateMenu",
                            "menu": MENU_NAME,
                            "locations": list(MENU_LOCATIONS),
                            "items": [spec.title for spec in expected],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 0
            backup = write_backup(None, [])
            created = client.request(
                "POST", "menus", payload={"name": MENU_NAME}, expected=(200, 201)
            )
            menu_id = int(created["id"])
            ids_by_title: dict[str, int] = {}
            for spec in expected:
                parent_id = ids_by_title.get(spec.parent_title or "", 0)
                item = create_item(client, menu_id, spec, parent_id)
                ids_by_title[spec.title] = int(item["id"])
            client.request(
                "POST",
                f"menus/{menu_id}",
                payload={"locations": list(MENU_LOCATIONS)},
                expected=(200,),
            )
            action = "CreatedMenu"

        verified_menu, verified_items = fetch_state(client)
        if verified_menu is None:
            raise RuntimeError("Menu disappeared after update")
        verification_errors = validate_menu_state(
            verified_items, verified_menu.get("locations", []), expected
        )
        if verification_errors:
            raise RuntimeError("Post-apply verification failed: " + "; ".join(verification_errors))
        print(
            json.dumps(
                {
                    "status": "Success",
                    "action": action,
                    "menu_id": menu_id,
                    "locations": list(MENU_LOCATIONS),
                    "items": len(verified_items),
                    "backup": str(backup),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (ConfigurationError, WordPressError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "Failed", "message": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
