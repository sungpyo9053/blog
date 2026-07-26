"""Publisher configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class ConfigurationError(ValueError):
    """Raised when required WordPress configuration is invalid."""


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE entries without overwriting process environment."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value.startswith(("'", '"')):
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class WordPressConfig:
    base_url: str
    username: str
    app_password: str
    timeout_seconds: float = 20.0

    @classmethod
    def from_environment(cls, env_file: Path | None = None) -> "WordPressConfig":
        if env_file is not None:
            load_env_file(env_file)

        base_url = os.environ.get("WORDPRESS_URL", "").strip().rstrip("/")
        username = os.environ.get("WORDPRESS_USERNAME", "").strip()
        app_password = os.environ.get("WORDPRESS_APP_PASSWORD", "").strip()

        missing = [
            name
            for name, value in (
                ("WORDPRESS_URL", base_url),
                ("WORDPRESS_USERNAME", username),
                ("WORDPRESS_APP_PASSWORD", app_password),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigurationError("WORDPRESS_URL must be an absolute HTTP(S) URL")
        if parsed.scheme != "https":
            raise ConfigurationError("WORDPRESS_URL must use HTTPS")

        return cls(
            base_url=base_url,
            username=username,
            app_password=app_password,
        )

    @property
    def api_root(self) -> str:
        # The rest_route form also works when Apache permalink rewrites do not
        # expose the usual /wp-json/ path.
        return f"{self.base_url}/?rest_route=/wp/v2"
