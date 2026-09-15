import json
import re
from html.parser import HTMLParser
from urllib.request import Request, HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_refused")


class SummaryCounter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden, self.heading, self.parts = [], False, []
        self.headings, self.boxes = 0, 0

    def handle_starttag(self, tag, attrs):
        if tag in {"pre", "script", "style", "template"}:
            self.hidden.append(tag)
        if self.hidden:
            return
        classes = (dict(attrs).get("class") or "").split()
        if "huntlab-article-quick-summary" in classes:
            self.boxes += 1
        if tag == "h2":
            self.heading, self.parts = True, []

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            return
        if tag == "h2" and self.heading:
            title = " ".join("".join(self.parts).split())
            self.headings += bool(re.fullmatch(r"(?:20초\s*)?핵심\s*요약", title))
            self.heading = False

    def handle_data(self, data):
        if self.heading and not self.hidden:
            self.parts.append(data)


if __name__ == "__main__":
    url = "https://huntlab.app/wordpress-quick-summary-regex-fix/"
    request = Request(url, headers={"User-Agent": "HuntLab-Reader-Check/1.0", "Cache-Control": "no-cache"})
    with build_opener(NoRedirect()).open(request, timeout=20) as response:
        if response.status != 200 or response.headers.get_content_type() != "text/html":
            raise ValueError("unexpected_response")
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("response_too_large")
    parser = SummaryCounter()
    parser.feed(raw.decode("utf-8")); parser.close()
    passed = parser.headings == 1 and parser.boxes == 0
    print(json.dumps({"passed": passed, "summary_h2": parser.headings, "automatic_boxes": parser.boxes}))
    raise SystemExit(0 if passed else 1)
