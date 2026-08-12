#!/usr/bin/env python3
"""Run dependency, route, and local-asset checks for the static site."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(ROOT.glob("*.html"))
PLATFORM_TERMS = re.compile(
    r"squarespace|sqspcdn|typekit|use\.typekit|assets\.squarespace|static1\.squarespace",
    re.I,
)
LOCAL_REF = re.compile(r'''(?:src|href)=["'](/[^"'#?]+)''')
RUNTIME_REF = re.compile(r'''<(?:script|iframe|link)\b[^>]*(?:src|href)=["'](https?://[^"']+)''', re.I)
ALLOWED_RUNTIME_HOSTS = {
    "www.joeyverbeke.com", "player.vimeo.com", "www.youtube.com",
    "w.soundcloud.com", "cdn2.trb.tv",
}


def local_path(reference: str) -> Path:
    if reference == "/":
        return ROOT / "index.html"
    candidate = ROOT / reference.lstrip("/")
    if candidate.exists():
        return candidate
    return candidate.with_suffix(".html")


def main() -> int:
    errors: list[str] = []
    if len(HTML_FILES) != 29:
        errors.append(f"expected 28 pages plus 404.html, found {len(HTML_FILES)} HTML files")
    for path in HTML_FILES:
        text = path.read_text(encoding="utf-8")
        if PLATFORM_TERMS.search(text):
            errors.append(f"platform dependency in {path.name}")
        for reference in LOCAL_REF.findall(text):
            if not local_path(reference).exists():
                errors.append(f"missing {reference} referenced by {path.name}")
        for reference in RUNTIME_REF.findall(text):
            host = urlparse(reference.replace("&amp;", "&")).hostname
            if host not in ALLOWED_RUNTIME_HOSTS:
                errors.append(f"unapproved runtime host {host} in {path.name}")
    for path in [ROOT / "assets/css/site.css", ROOT / "assets/js/site.js"]:
        if PLATFORM_TERMS.search(path.read_text(encoding="utf-8")):
            errors.append(f"platform dependency in {path.relative_to(ROOT)}")
    routes = [path.stem for path in HTML_FILES if path.name not in {"index.html", "404.html"}]
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for route in routes:
        if f"/{route}</loc>" not in sitemap:
            errors.append(f"route /{route} missing from sitemap.xml")
    if errors:
        print("Validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    media_count = sum(1 for path in (ROOT / "media").iterdir() if path.is_file())
    print(f"Validated {len(HTML_FILES) - 1} pages, 1 custom 404 page, and {media_count} local media files.")
    print("No platform dependencies, missing local references, or unapproved runtime hosts found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
