from datetime import UTC, datetime
from email.message import Message
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


class WordPressRetryTest(TestCase):
    def client(self, sleeps: list[float]) -> WordPressClient:
        return WordPressClient(
            WordPressConfig(
                base_url="https://example.test",
                username="operator",
                app_password="secret",
                timeout_seconds=5,
            ),
            max_retries=1,
            sleep=sleeps.append,
        )

    def http_error(self, retry_after: str) -> HTTPError:
        headers = Message()
        headers["Retry-After"] = retry_after
        return HTTPError(
            "https://example.test/wp-json/wp/v2/posts",
            429,
            "Too Many Requests",
            headers,
            BytesIO(b'{"code":"rest_rate_limited","message":"slow down"}'),
        )

    def test_retry_after_http_date_is_converted_to_seconds(self):
        now = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
        self.assertEqual(
            WordPressClient._retry_after_seconds(
                "Sat, 05 Sep 2026 00:00:07 GMT", now=now
            ),
            7.0,
        )

    def test_malformed_retry_after_falls_back_instead_of_raising_value_error(self):
        sleeps: list[float] = []
        client = self.client(sleeps)
        response = BytesIO(b'{"id":50}')
        response.status = 200
        response.__enter__ = lambda item: item
        response.__exit__ = lambda *args: None
        with patch(
            "publisher.wordpress.urlopen",
            side_effect=[self.http_error("not-a-date"), response],
        ):
            result = client.request("GET", "posts/50")
        self.assertEqual(result, {"id": 50})
        self.assertEqual(sleeps, [1.0])

