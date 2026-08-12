#!/usr/bin/env python3
"""Preview this static site locally with Vercel-like clean URLs and redirects."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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
        super().do_GET()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    print("Clean Vercel preview: http://127.0.0.1:8766/", flush=True)
    server.serve_forever()
