"""Minimal WordPress REST API client using Application Password authentication."""

from __future__ import annotations

import base64
import json
import mimetypes
import socket
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from .config import WordPressConfig


@dataclass
class WordPressError(Exception):
    category: str
    message: str
    status_code: int | None = None
    wp_code: str | None = None
    retry_count: int = 0

    def __str__(self) -> str:
        return self.message


class WordPressClient:
    def __init__(
        self,
        config: WordPressConfig,
        *,
        max_retries: int = 3,
        sleep: Any = time.sleep,
    ) -> None:
        self.config = config
        self.max_retries = max_retries
        self._sleep = sleep

    def _authorization(self) -> str:
        raw = f"{self.config.username}:{self.config.app_password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        body: bytes | None = None,
        content_type: str = "application/json",
        extra_headers: dict[str, str] | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> Any:
        api_root = self.config.api_root
        clean_path = path.lstrip("/")
        if "?rest_route=" in api_root:
            endpoint, separator, query = clean_path.partition("?")
            url = f"{api_root.rstrip('/')}/{endpoint}"
            if separator:
                url = f"{url}&{query}"
        else:
            url = f"{api_root.rstrip('/')}/{clean_path}"
        data = body
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        headers = {
            "Authorization": self._authorization(),
            "Accept": "application/json",
            "User-Agent": "HuntLab-Publisher/1.0",
        }
        if data is not None:
            headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)

        for attempt in range(self.max_retries + 1):
            request = Request(url, data=data, headers=headers, method=method)
            try:
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    raw = response.read()
                    if response.status not in expected:
                        raise WordPressError(
                            category="api",
                            message=f"Unexpected WordPress status: {response.status}",
                            status_code=response.status,
                            retry_count=attempt,
                        )
                    return json.loads(raw.decode("utf-8")) if raw else None
            except HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                wp_code = None
                message = f"WordPress API returned HTTP {exc.code}"
                try:
                    error_data = json.loads(raw)
                    wp_code = error_data.get("code")
                    message = error_data.get("message") or message
                except json.JSONDecodeError:
                    pass

                retryable = exc.code == 429 or 500 <= exc.code < 600
                if retryable and attempt < self.max_retries:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(min(delay, 30.0))
                    continue
                category = "authentication" if exc.code in {401, 403} else "api"
                raise WordPressError(
                    category=category,
                    message=message,
                    status_code=exc.code,
                    wp_code=wp_code,
                    retry_count=attempt,
                ) from exc
            except (URLError, TimeoutError, socket.timeout) as exc:
                if attempt < self.max_retries:
                    self._sleep(float(2**attempt))
                    continue
                raise WordPressError(
                    category="network",
                    message="Unable to reach WordPress after retries.",
                    retry_count=attempt,
                ) from exc

        raise AssertionError("request retry loop exhausted unexpectedly")

    def find_posts(self, *, title: str | None = None, slug: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, str] = {"context": "edit", "per_page": "100"}
        if title:
            query["search"] = title
        if slug:
            query["slug"] = slug
        return self.request("GET", f"posts?{urlencode(query)}", expected=(200,))

    def get_post(self, post_id: int) -> dict[str, Any]:
        return self.request(
            "GET", f"posts/{post_id}?context=edit", expected=(200,)
        )

    def get_media(self, media_id: int) -> dict[str, Any]:
        return self.request(
            "GET", f"media/{media_id}?context=edit", expected=(200,)
        )

    def find_media_by_source_url(self, source_url: str) -> dict[str, Any] | None:
        filename_stem = Path(unquote(urlparse(source_url).path)).stem
        media_items = self.request(
            "GET",
            f"media?{urlencode({'search': filename_stem, 'per_page': '100', 'context': 'edit'})}",
            expected=(200,),
        )
        requested_url = urlparse(source_url)
        exact = [
            media
            for media in media_items
            if (
                urlparse(str(media.get("source_url", ""))).scheme.casefold(),
                urlparse(str(media.get("source_url", ""))).netloc.casefold(),
                unquote(urlparse(str(media.get("source_url", ""))).path),
            )
            == (
                requested_url.scheme.casefold(),
                requested_url.netloc.casefold(),
                unquote(requested_url.path),
            )
        ]
        return exact[0] if len(exact) == 1 else None

    def find_term(self, taxonomy: str, name: str) -> dict[str, Any] | None:
        terms = self.request(
            "GET",
            f"{taxonomy}?{urlencode({'search': name, 'per_page': '100'})}",
            expected=(200,),
        )
        normalized = " ".join(name.split()).casefold()
        return next(
            (
                term
                for term in terms
                if " ".join(str(term.get("name", "")).split()).casefold() == normalized
            ),
            None,
        )

    def create_tag(self, name: str) -> dict[str, Any]:
        return self.request(
            "POST", "tags", payload={"name": name}, expected=(200, 201)
        )

    def create_category(self, name: str) -> dict[str, Any]:
        return self.request(
            "POST", "categories", payload={"name": name}, expected=(200, 201)
        )

    def upload_media(self, path: Path, *, alt_text: str) -> dict[str, Any]:
        upload_path = path
        with tempfile.TemporaryDirectory(prefix="huntlab-media-") as temp_dir:
            if path.suffix.casefold() == ".png":
                try:
                    from PIL import Image

                    webp_path = Path(temp_dir) / f"{path.stem}.webp"
                    with Image.open(path) as image:
                        image.save(webp_path, "WEBP", quality=82, method=6)
                    if webp_path.stat().st_size < path.stat().st_size:
                        upload_path = webp_path
                except (ImportError, OSError, ValueError):
                    # Publishing must remain available if an unusual PNG cannot
                    # be converted. WordPress can still serve the original.
                    upload_path = path

            media_type = mimetypes.guess_type(upload_path.name)[0]
            if not media_type or not media_type.startswith("image/"):
                raise WordPressError(
                    "validation", "Featured image format is not supported."
                )
            body = upload_path.read_bytes()
            media = self.request(
                "POST",
                "media",
                body=body,
                content_type=media_type,
                extra_headers={
                    "Content-Disposition": (
                        f'attachment; filename="{upload_path.name}"'
                    ),
                },
                expected=(200, 201),
            )
        return self.request(
            "POST",
            f"media/{media['id']}",
            payload={"alt_text": alt_text},
            expected=(200,),
        )

    def create_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.create_post(payload, status="draft")

    def create_post(
        self,
        payload: dict[str, Any],
        *,
        status: str,
    ) -> dict[str, Any]:
        post_payload = dict(payload)
        post_payload["status"] = status
        return self.request(
            "POST", "posts", payload=post_payload, expected=(200, 201)
        )

    def update_post(
        self,
        post_id: int,
        payload: dict[str, Any],
        *,
        status: str,
    ) -> dict[str, Any]:
        post_payload = dict(payload)
        post_payload["status"] = status
        return self.request(
            "POST", f"posts/{post_id}", payload=post_payload, expected=(200,)
        )
