#!/usr/bin/env python3
"""Convert the preserved Squarespace-rendered capture into a local static site.

The source is always read from the local baseline Git commit so this script can
be re-run after the generated pages have replaced the capture in the worktree.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "https://www.joeyverbeke.com"
BASELINE = "3b18462"
ROUTES = [
    "", "dynamic-vr-auditory-awareness", "embody", "google-soli-speaker",
    "gradi-vox", "heroes", "in-vivo-in-vitro-trial-14", "in-vivo-in-vitro",
    "lookingglass", "lux-aeterna", "movestudio", "neurosense", "open-windows-1",
    "pageme", "patents", "porous", "previous-works", "recurrent",
    "remember-to-forget", "shapeshifting-controller", "slow-magic-mask-redesign",
    "slowmagicsmask", "tael", "ted-performance", "threewaymirror", "timeprojector",
    "vibrations", "whimsic",
]
NAV = [
    ("Home", "/"), ("Gradi Vox", "/gradi-vox"), ("Porous", "/porous"),
    ("T.A.E.L.", "/tael"),
    ("In Vivo / In Vitro - Trial 1.4", "/in-vivo-in-vitro-trial-14"),
    ("In Vivo / In Vitro - Trial 1&2", "/in-vivo-in-vitro"),
    ("remember to forget.", "/remember-to-forget"), ("Recurrent", "/recurrent"),
    ("threeWayMirror", "/threewaymirror"), ("Looking-glass", "/lookingglass"),
    ("Time Projector", "/timeprojector"), ("Heroes", "/heroes"),
    ("Slow Magic's Mask", "/slowmagicsmask"), ("Patents", "/patents"),
    ("Embody", "/embody"), ("Whimsic", "/whimsic"), ("MOVE Studio", "/movestudio"),
    ("Lux Aeterna", "/lux-aeterna"), ("Open Windows", "/open-windows-1"),
    ("Shapeshifting Controller", "/shapeshifting-controller"),
    ("Google Soli Speaker", "/google-soli-speaker"),
    ("Dynamic VR Auditory Awareness", "/dynamic-vr-auditory-awareness"),
    ("Neurosense", "/neurosense"),
    ("Slow Magic Mask Redesign", "/slow-magic-mask-redesign"),
    ("TED Performance", "/ted-performance"), ("Vibrations", "/vibrations"),
    ("Previous Works", "/previous-works"), ("Me", "/pageme"),
]

SAFE_TAGS = {
    "a", "br", "em", "strong", "b", "i", "p", "h1", "h2", "h3", "h4",
    "ul", "ol", "li", "blockquote", "span", "small", "sup", "sub", "code",
}
ALLOWED_IFRAME_HOSTS = {"player.vimeo.com", "www.youtube.com", "w.soundcloud.com", "cdn2.trb.tv"}


def baseline_html(filename: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{BASELINE}:{filename}"], cwd=ROOT, check=True,
        text=True, capture_output=True,
    )
    return result.stdout


def local_media(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value).split("?", 1)[0]
    if value.startswith("media/"):
        value = "/" + value
    return value if value.startswith("/media/") else ""


def clean_fragment(node: Tag | None) -> str:
    if node is None:
        return ""
    soup = BeautifulSoup(str(node), "lxml")
    root = soup.body or soup
    for bad in root.select("script, style, noscript"):
        bad.decompose()
    for tag in list(root.find_all(True)):
        if tag.name not in SAFE_TAGS and tag.name not in {"html", "body"}:
            tag.unwrap()
            continue
        if tag.name == "a":
            href = tag.get("href", "")
            attrs = {"href": href} if href else {}
            if href.startswith("http"):
                attrs.update({"target": "_blank", "rel": "noopener noreferrer"})
            tag.attrs = attrs
        elif tag.name not in {"html", "body"}:
            tag.attrs = {}
    output = "".join(str(child) for child in root.contents).strip()
    return re.sub(r"\s*<p>\s*</p>\s*", "", output)


def image_dimensions(img: Tag) -> tuple[str, str]:
    dims = img.get("data-image-dimensions", "")
    match = re.fullmatch(r"(\d+)x(\d+)", dims)
    if match:
        return match.group(1), match.group(2)
    return str(img.get("width", "")), str(img.get("height", ""))


def image_html(img: Tag, alt: str | None = None, eager: bool = False, class_name: str = "") -> str:
    src = local_media(img.get("data-src") or img.get("data-image") or img.get("src"))
    if not src:
        return ""
    width, height = image_dimensions(img)
    attrs = [f'src="{html.escape(src)}"', f'alt="{html.escape(alt if alt is not None else img.get("alt", ""))}"']
    if width:
        attrs.append(f'width="{html.escape(width)}"')
    if height:
        attrs.append(f'height="{html.escape(height)}"')
    attrs.extend([f'loading="{"eager" if eager else "lazy"}"', 'decoding="async"'])
    if class_name:
        attrs.append(f'class="{class_name}"')
    focal = img.get("data-image-focal-point", "0.5,0.5").split(",")
    if len(focal) == 2:
        try:
            attrs.append(f'style="object-position:{float(focal[0]) * 100:.1f}% {float(focal[1]) * 100:.1f}%"')
        except ValueError:
            pass
    return "<img " + " ".join(attrs) + ">"


def transform_text(block: Tag) -> str:
    content = block.select_one(".sqs-html-content") or block.select_one(".sqs-block-content")
    cleaned = clean_fragment(content)
    return f'<section class="text-block">{cleaned}</section>' if cleaned else ""


def transform_image(block: Tag, eager: bool) -> str:
    img = block.find("img", attrs={"data-src": True}) or block.find("img")
    if not img:
        return ""
    rendered = image_html(img, eager=eager, class_name="content-image")
    if not rendered:
        return ""
    link = img.find_parent("a")
    if link and link.get("href"):
        href = html.escape(link["href"], quote=True)
        extra = ' target="_blank" rel="noopener noreferrer"' if href.startswith("http") else ""
        rendered = f'<a href="{href}"{extra}>{rendered}</a>'
    shape = img.find_parent(class_=lambda value: value and "sqs-image-shape-container-element" in value)
    ratio = "auto"
    if shape:
        match = re.search(r"padding-bottom\s*:\s*([\d.]+)%", shape.get("style", ""))
        if match and float(match.group(1)) > 0:
            ratio = f"{100 / float(match.group(1)):.8f}"
    source_figure = img.find_parent("figure")
    max_width = "100%"
    if source_figure:
        match = re.search(r"max-width\s*:\s*([\d.]+)px", source_figure.get("style", ""))
        if match:
            max_width = f"{match.group(1)}px"
    fit = "contain" if "object-fit: contain" in img.get("style", "") else "cover"
    caption_node = block.select_one(".image-caption, .image-card-wrapper, figcaption")
    caption = clean_fragment(caption_node)
    caption_html = f"<figcaption>{caption}</figcaption>" if caption else ""
    style = f"--media-ratio:{ratio};--media-max-width:{max_width}"
    return f'<figure class="media-block media-block--{fit}" style="{style}"><div class="media-frame">{rendered}</div>{caption_html}</figure>'


def transform_gallery(block: Tag) -> tuple[str, dict]:
    try:
        config = json.loads(block.get("data-block-json", "{}"))
    except json.JSONDecodeError:
        config = {}
    design = config.get("design", "grid")
    cols = int(config.get("thumbnails-per-row") or 1)
    ratio = config.get("aspect-ratio", "auto")
    gap = int(config.get("padding") or 0)
    lightbox = bool(config.get("lightbox"))
    figures: list[str] = []
    media: list[str] = []
    for slide in block.select(".slide, .image-wrapper"):
        img = slide.find("img", attrs={"data-src": True}) or slide.find("img")
        if not img:
            continue
        src = local_media(img.get("data-src") or img.get("src"))
        if not src or src in media:
            continue
        media.append(src)
        anchor = slide.find("a")
        title = (anchor.get("data-title", "") if anchor else "").strip()
        description = (anchor.get("data-description", "") if anchor else "").strip()
        caption_bits = [value for value in (title, description) if value]
        caption_text = " — ".join(BeautifulSoup(value, "lxml").get_text(" ", strip=True) for value in caption_bits)
        rendered = image_html(img, alt=img.get("alt") or caption_text, class_name="gallery-image")
        if lightbox:
            label = html.escape(caption_text or img.get("alt") or "View image")
            rendered = (
                f'<button class="gallery-open" type="button" data-lightbox-src="{html.escape(src)}" '
                f'data-lightbox-caption="{html.escape(caption_text, quote=True)}" aria-label="{label}">{rendered}</button>'
            )
        caption = f"<figcaption>{html.escape(caption_text)}</figcaption>" if caption_text else ""
        figures.append(f'<figure class="gallery-item">{rendered}{caption}</figure>')
    classes = f"gallery gallery--{design} gallery--cols-{cols} gallery--ratio-{ratio}"
    markup = f'<section class="{classes}" style="--gallery-gap:{gap}px">' + "".join(figures) + "</section>"
    manifest = {"design": design, "columns": cols, "ratio": ratio, "gap": gap, "lightbox": lightbox, "images": media}
    return markup, manifest


def direct_embed_url(raw: str) -> str:
    raw = html.unescape(raw).replace("&amp;", "&")
    if raw.startswith("//"):
        raw = "https:" + raw
    parsed = urlparse(raw)
    if parsed.hostname == "cdn.embedly.com":
        nested = parse_qs(parsed.query).get("src", [""])[0]
        raw = unquote(nested)
        if raw.startswith("//"):
            raw = "https:" + raw
        parsed = urlparse(raw)
    if parsed.hostname == "youtube.com":
        raw = raw.replace("https://youtube.com", "https://www.youtube.com", 1)
        parsed = urlparse(raw)
    return raw if parsed.hostname in ALLOWED_IFRAME_HOSTS else ""


def find_embed(block: Tag) -> tuple[str, str]:
    iframe = block.find("iframe")
    if not iframe:
        encoded = ""
        holder = block.find(attrs={"data-html": True})
        if holder:
            encoded = holder.get("data-html", "")
        if encoded:
            embedded = BeautifulSoup(html.unescape(encoded), "lxml")
            iframe = embedded.find("iframe")
    if not iframe:
        return "", ""
    src = direct_embed_url(iframe.get("src", ""))
    if not src:
        return "", ""
    host = urlparse(src).hostname or "media"
    provider = "Vimeo" if "vimeo" in host else "YouTube" if "youtube" in host else "SoundCloud" if "soundcloud" in host else "Video"
    return src, provider


def transform_embed(block: Tag) -> tuple[str, str]:
    src, provider = find_embed(block)
    if not src:
        return "", ""
    soundcloud = provider == "SoundCloud"
    cls = "embed-block embed-block--soundcloud" if soundcloud else "embed-block"
    height = ' height="450"' if soundcloud else ""
    allow = "autoplay" if soundcloud else "autoplay; fullscreen; picture-in-picture"
    markup = (
        f'<figure class="{cls}"><iframe src="{html.escape(src, quote=True)}" title="{provider} player" '
        f'loading="lazy" allow="{allow}" allowfullscreen{height}></iframe>'
        f'<figcaption class="embed-fallback">If the player is unavailable, '
        f'<a href="{html.escape(src, quote=True)}" target="_blank" rel="noopener noreferrer">open it on {provider}</a>.</figcaption></figure>'
    )
    return markup, src


def transform_summary(block: Tag) -> tuple[str, list[str], dict]:
    wrapper = block.select_one(".summary-block-wrapper")
    column_width = int(wrapper.get("data-column-width", 300)) if wrapper else 300
    gutter = int(wrapper.get("data-gutter", 9)) if wrapper else 9
    columns = max(1, 883 // max(column_width, 1))
    centered = bool(wrapper and "summary-block-setting-text-align-center" in wrapper.get("class", []))
    text_size = "medium" if wrapper and "summary-block-setting-text-size-medium" in wrapper.get("class", []) else "small"
    cards: list[str] = []
    media: list[str] = []
    for item in block.select(".summary-item"):
        img = item.find("img", attrs={"data-src": True}) or item.find("img")
        title_node = item.select_one(".summary-title-link")
        excerpt_node = item.select_one(".summary-excerpt")
        thumb_link = item.select_one(".summary-thumbnail-container")
        href = (title_node or thumb_link or {}).get("href", "") if (title_node or thumb_link) else ""
        patent_link = excerpt_node.select_one('a[href^="http"]') if excerpt_node else None
        if patent_link:
            href = patent_link.get("href", href)
        link_attrs = ' target="_blank" rel="noopener noreferrer"' if href.startswith("http") else ""
        title = title_node.get_text(" ", strip=True) if title_node else ""
        image = image_html(img, alt=(img.get("alt") or title) if img else title, class_name="summary-image") if img else ""
        src = local_media(img.get("data-src") or img.get("src")) if img else ""
        if src:
            media.append(src)
        if image and href:
            image = f'<a href="{html.escape(href, quote=True)}"{link_attrs}>{image}</a>'
        title_html = f'<h2 class="summary-title"><a href="{html.escape(href, quote=True)}"{link_attrs}>{html.escape(title)}</a></h2>' if title else ""
        excerpt = clean_fragment(excerpt_node)
        excerpt_html = f'<div class="summary-excerpt">{excerpt}</div>' if excerpt else ""
        cards.append(f'<article class="summary-card">{image}{title_html}{excerpt_html}</article>')
    alignment = " summary-grid--center" if centered else ""
    markup = f'<section class="summary-grid summary-grid--cols-{columns} summary-grid--text-{text_size}{alignment}" style="--summary-gap:{gutter}px">' + "".join(cards) + "</section>"
    return markup, media, {"columns": columns, "gutter": gutter, "centered": centered, "textSize": text_size}


def transform_block(block: Tag, eager: bool) -> tuple[str, dict]:
    block_type = block.get("data-block-type", "")
    definition = block.get("data-definition-name", "")
    info: dict = {"type": block_type, "definition": definition or None}
    if block_type == "2":
        return transform_text(block), info
    if block_type == "5":
        rendered = transform_image(block, eager)
        img = block.find("img", attrs={"data-src": True}) or block.find("img")
        info["images"] = [local_media(img.get("data-src") or img.get("src"))] if img else []
        return rendered, info
    if block_type == "8":
        rendered, gallery = transform_gallery(block)
        info["gallery"] = gallery
        return rendered, info
    if block_type == "56":
        rendered, src = transform_embed(block)
        info["embed"] = src
        return rendered, info
    if block_type == "1337" and definition == "website.components.horizontalrule":
        return '<hr class="content-rule">', info
    if block_type == "1337" and definition == "website.components.socialLinks":
        info["removed"] = True
        return "", info
    if block_type == "1337" and definition == "website.components.summary":
        rendered, images, summary = transform_summary(block)
        info["images"] = images
        info["summary"] = summary
        return rendered, info
    if block_type == "1337" and definition in {"website.components.video", "website.components.embed", "website.components.code"}:
        rendered, src = transform_embed(block)
        info["embed"] = src
        return rendered, info
    return "", info


def top_blocks(main: Tag) -> list[Tag]:
    blocks = []
    for block in main.select("[data-block-type]"):
        parent = block.find_parent(attrs={"data-block-type": True})
        if parent is None:
            blocks.append(block)
    return blocks


def nav_html(route: str) -> str:
    current = "/" if not route else "/" + route
    links = []
    for label, href in NAV:
        active = ' class="active" aria-current="page"' if href == current else ""
        links.append(f'<li><a href="{href}"{active}>{html.escape(label)}</a></li>')
    return "".join(links)


def page_html(route: str, title: str, description: str, content: str, image: str) -> str:
    path = "/" if not route else f"/{route}"
    canonical = CANONICAL + path
    og_image = CANONICAL + (image or "/media/570580e1_k0j0.png")
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{og_image}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title, quote=True)}">
  <meta name="twitter:description" content="{html.escape(description, quote=True)}">
  <meta name="twitter:image" content="{og_image}">
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/assets/css/site.css">
  <script src="/assets/js/site.js" defer></script>
  <script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": canonical})}</script>
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <div class="site-shell">
    <header class="site-header">
      <div class="header-row">
        <a class="site-title" href="/" aria-label="Joey Verbeke home">//Joey Verbeke</a>
        <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav"><span>Menu</span></button>
      </div>
      <nav id="site-nav" class="site-nav" aria-label="Primary"><ul>{nav_html(route)}</ul></nav>
    </header>
    <main id="content" class="page-content">{content}</main>
  </div>
  <dialog class="lightbox" aria-label="Image viewer">
    <button class="lightbox-close" type="button" aria-label="Close image viewer">×</button>
    <button class="lightbox-prev" type="button" aria-label="Previous image">‹</button>
    <figure><img src="" alt=""><figcaption></figcaption></figure>
    <button class="lightbox-next" type="button" aria-label="Next image">›</button>
  </dialog>
</body>
</html>
'''


def convert_page(route: str) -> dict:
    filename = "index.html" if not route else f"{route}.html"
    soup = BeautifulSoup(baseline_html(filename), "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else (route.replace("-", " ").title() + " — Joey Verbeke")
    title = re.sub(r"\s*—\s*Joey Verbeke\s*$", " — Joey Verbeke", title)
    main = soup.select_one(".main-content")
    if not main:
        raise RuntimeError(f"No main content in {filename}")
    chunks: list[str] = []
    manifest_blocks: list[dict] = []
    first_image = True
    for block in top_blocks(main):
        rendered, info = transform_block(block, first_image)
        if rendered:
            chunks.append(rendered)
            if "<img " in rendered:
                first_image = False
        manifest_blocks.append(info)
    content = "\n".join(chunks)
    description_soup = BeautifulSoup(content, "lxml")
    for fallback in description_soup.select(".embed-fallback"):
        fallback.decompose()
    content_text = description_soup.get_text(" ", strip=True)
    description = content_text[:157].rsplit(" ", 1)[0] + "…" if len(content_text) > 160 else content_text
    description = description or "Selected work by artist and designer Joey Verbeke."
    images = re.findall(r'(?:src|data-lightbox-src)="(/media/[^\"]+)"', content)
    (ROOT / filename).write_text(page_html(route, title, description, content, images[0] if images else ""), encoding="utf-8")
    return {"route": "/" if not route else f"/{route}", "file": filename, "title": title, "blocks": manifest_blocks, "images": sorted(set(images))}


def main() -> None:
    manifest = [convert_page(route) for route in ROUTES]
    (ROOT / "content-manifest.json").write_text(json.dumps({"pages": manifest}, indent=2) + "\n", encoding="utf-8")
    print(f"Converted {len(manifest)} pages.")


if __name__ == "__main__":
    main()
