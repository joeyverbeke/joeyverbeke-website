#!/usr/bin/env python3
"""Preview this static site locally with Vercel-like clean URLs and redirects."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
EXACT_REDIRECTS = {
    rule["source"]: rule["destination"]
    for rule in CONFIG.get("redirects", [])
    if ":path*" not in rule["source"]
}
PREFIX_REDIRECTS = [
    (rule["source"].removesuffix(":path*").rstrip("/"), rule["destination"])
    for rule in CONFIG.get("redirects", [])
    if ":path*" in rule["source"]
]


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        requested = urlsplit(path).path
        candidate = ROOT / requested.lstrip("/")
        if requested == "/":
            candidate = ROOT / "index.html"
        elif not candidate.suffix and not candidate.is_dir():
            candidate = candidate.with_suffix(".html")
        return str(candidate)

    def do_GET(self) -> None:
        requested = urlsplit(self.path).path.rstrip("/") or "/"
        destination = EXACT_REDIRECTS.get(requested)
        if destination is None:
            for prefix, target in PREFIX_REDIRECTS:
                if requested == prefix or requested.startswith(prefix + "/"):
                    destination = target
                    break
        if destination is not None:
            self.send_response(308)
            self.send_header("Location", destination)
            self.end_headers()
            return
        if not Path(self.translate_path(self.path)).exists():
            error_page = ROOT / "404.html"
            body = error_page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Clean Vercel preview: http://127.0.0.1:{args.port}/", flush=True)
    server.serve_forever()
