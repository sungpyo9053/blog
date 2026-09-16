#!/usr/bin/env python3
"""Local WordPress-double preview only: no credentials, writes, or live WP data."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import argparse
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/huntlab-warm-editorial"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    completed = subprocess.run([
        "docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "-v", f"{ROOT}:{ROOT}:ro", "-w", str(ROOT),
        "php:8.3-cli", "php", str(ROOT / "tests/fixtures/physical-home-harness.php"),
        str(PLUGIN / "physical-home.php"), "absent",
    ], check=True, capture_output=True, text=True, timeout=30)
    rendered = json.loads(completed.stdout)["html"]
    rendered = rendered.replace("https://example.test/plugin/assets/", "/assets/")
    styles = "\n".join((PLUGIN / "assets" / name).read_text()
                       for name in ("warm-editorial.css", "reader-tools.css", "physical-ai.css"))
    document = ("<!doctype html><html lang='ko'><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>HuntLab local WordPress-double preview</title>"
                "<style>body{margin:0;font-family:system-ui,sans-serif}*{box-sizing:border-box}"
                + styles + "</style><body><aside style='padding:12px;background:#fff3c4'>"
                "로컬 WordPress-double 미리보기 · 실제 WordPress·헤더·카테고리·글 데이터 아님"
                "</aside>" + rendered + "</body></html>").encode()
    image = (PLUGIN / "assets/physical-ai-hero.png").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?", 1)[0] == "/":
                body, content_type = document, "text/html; charset=utf-8"
            elif self.path == "/assets/physical-ai-hero.png":
                body, content_type = image, "image/png"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Local WP-double preview: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
