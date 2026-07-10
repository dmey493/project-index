#!/usr/bin/env python3
"""
build.py — Regenerate the portfolio from project + book cards.

Reads ./projects/*.json and ./books/*.json and rewrites:
  - README.md   : for browsing on GitHub
  - index.html  : a styled, zero-dependency GitHub Pages site

Projects are grouped Education / Service / Personal. Books live under Personal
and render as a 3D book carousel (CSS scroll-snap + tiny vanilla JS). Optional
./site.json controls page chrome. Everything is deterministic and dependency-
free, so the index repo works on its own. Run from inside the index repo:
    python build.py
"""

import html
import json
import sys
from datetime import date
from pathlib import Path

# ---- configuration --------------------------------------------------------

BUCKETS = [
    ("education", "Education"),
    ("service", "Service"),
    ("personal", "Personal"),
]

STATUS = {
    "live":     ("🟢", "Live",     "#16a34a"),
    "shipped":  ("✅", "Shipped",  "#0d9488"),
    "active":   ("🔨", "Active",   "#d97706"),
    "paused":   ("⏸️", "Paused",   "#64748b"),
    "seed":     ("🌱", "Seed",     "#65a30d"),
    "archived": ("📦", "Archived", "#78716c"),
    "killed":   ("⚰️", "Killed",   "#9f1239"),
}
STATUS_ORDER = list(STATUS.keys())

BOOK_STATUS = {
    "printed":     ("Printed",     "#16a34a"),
    "in_progress": ("In progress", "#d97706"),
    "planned":     ("Planned",     "#6366f1"),
}
BOOK_ORDER = list(BOOK_STATUS.keys())

THUMB_WIDTH = 360


def _emoji(s):  return STATUS.get(s, ("•", s or "Unknown", "#888"))[0]
def _label(s):  return STATUS.get(s, ("•", s or "Unknown", "#888"))[1]
def _color(s):  return STATUS.get(s, ("•", s or "Unknown", "#888"))[2]
def _rank(s):
    try: return STATUS_ORDER.index(s)
    except ValueError: return len(STATUS_ORDER)
def _book_rank(s):
    try: return BOOK_ORDER.index(s)
    except ValueError: return len(BOOK_ORDER)


def load_json_dir(d: Path) -> list:
    items = []
    if not d.exists():
        return items
    for path in sorted(d.glob("*.json")):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as ex:
            print(f"  ! skipping {path.name}: {ex}", file=sys.stderr)
    return items


def load_site(root: Path) -> dict:
    defaults = {
        "title": "Project Portfolio",
        "tagline": "Everything I've built, in one place.",
        "accent": "#4f46e5",
        "links": [],
    }
    p = root / "site.json"
    if p.exists():
        try:
            defaults.update(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError as ex:
            print(f"  ! site.json ignored: {ex}", file=sys.stderr)
    return defaults


def e(s):  # html-escape
    return html.escape(str(s), quote=True)


# ===========================================================================
# README.md
# ===========================================================================

def md_badge(s): return f"{_emoji(s)} **{_label(s)}**"


def md_card(card: dict) -> str:
    out, name = [], card.get("name", "Untitled")
    out += [f"### {name} — {md_badge(card.get('status',''))}", ""]
    if card.get("screenshot"):
        out += [f'<img src="{card["screenshot"]}" width="{THUMB_WIDTH}" '
                f'alt="{name} screenshot">', ""]
    if card.get("one_liner"):
        out += [card["one_liner"], ""]
    links = []
    if card.get("live_url"): links.append(f"[🔗 Live]({card['live_url']})")
    if card.get("repo_url"): links.append(f"[</> Repo]({card['repo_url']})")
    if links:
        out += [" · ".join(links), ""]
    meta = []
    if card.get("stack"): meta.append(", ".join(card["stack"]))
    if card.get("last_touched"): meta.append(f"last touched {card['last_touched']}")
    if meta:
        out += [f"<sub>{' — '.join(meta)}</sub>", ""]
    if card.get("left_off"): out.append(f"**Left off:** {card['left_off']}")
    if card.get("next"): out.append(f"**Next:** {card['next']}")
    if card.get("left_off") or card.get("next"): out.append("")
    comps = card.get("components") or []
    if comps:
        out.append("**Inside:**")
        for c in comps:
            head = f"  - **{c.get('name','Untitled')}** — {md_badge(c.get('status',''))}"
            if c.get("deep_link"): head += f" · [open]({c['deep_link']})"
            out.append(head)
            if c.get("one_liner"): out.append(f"    {c['one_liner']}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def md_books(books: list) -> str:
    if not books:
        return ""
    ordered = sorted(books, key=lambda b: (_book_rank(b.get("status", "printed")),
                                           b.get("title", "").lower()))
    out = ["### 📚 Books", ""]
    for b in ordered:
        label = BOOK_STATUS.get(b.get("status", "printed"), ("", ""))[0]
        bits = [f"**{b.get('title','Untitled')}**"]
        if b.get("author"): bits.append(f"by {b['author']}")
        line = " ".join(bits)
        sub = []
        if b.get("format"): sub.append(b["format"])
        if b.get("year"): sub.append(str(b["year"]))
        if label: sub.append(label)
        if sub: line += " — " + " · ".join(sub)
        if b.get("buy_url"): line += f" · [Buy]({b['buy_url']})"
        cover = (f'<img src="{b["cover"]}" width="70" align="left" '
                 f'alt="{e(b.get("title",""))} cover" hspace="10"> ' if b.get("cover") else "")
        out.append(f"- {cover}{line}")
        if b.get("one_liner"):
            out.append(f"  {b['one_liner']}")
    out.append("")
    return "\n".join(out)


def build_readme(cards: list, books: list, site: dict) -> str:
    L = ["# " + site["title"], "",
         site["tagline"] + " Auto-generated; edit the cards in `projects/` and "
         "`books/`, not this file.",
         "",
         f"<sub>{len(cards)} project(s) · {len(books)} book(s) · last generated "
         f"{date.today().isoformat()}</sub>", ""]
    for key, title in BUCKETS:
        items = sorted([c for c in cards if c.get("bucket") == key],
                       key=lambda c: (_rank(c.get("status","")), c.get("name","").lower()))
        L += [f"## {title}", ""]
        if key == "personal" and books:
            L += [md_books(books)]
        if items:
            for c in items:
                L += [md_card(c), "---", ""]
        elif not (key == "personal" and books):
            L += ["_Nothing here yet._", ""]
    return "\n".join(L).rstrip() + "\n"


# ===========================================================================
# index.html
# ===========================================================================

PAGE_CSS = """
:root {
  --accent: #4f46e5;
  --bg: #fbfbfd; --surface: #ffffff; --text: #1a1a1f; --muted: #6b7280;
  --line: #e7e7ec; --tag-bg: #f1f1f5; --radius: 14px;
  --maxw: 1120px; --shadow: 0 1px 2px rgba(0,0,0,.04), 0 8px 24px rgba(0,0,0,.05);
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d0d12; --surface: #16161d; --text: #ececf1; --muted: #9a9aa6;
    --line: #26262f; --tag-bg: #20202a;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.4);
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: var(--bg); color: var(--text);
  font-family: var(--font); line-height: 1.55; -webkit-font-smoothing: antialiased; }
a { color: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }

.wrap { max-width: var(--maxw); margin: 0 auto; padding: 0 24px; }

header.site { border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 6%, var(--bg)), var(--bg)); }
.site-inner { padding: 56px 24px 40px; max-width: var(--maxw); margin: 0 auto; }
.eyebrow { font-size: 12px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--accent); font-weight: 700; margin: 0 0 10px; }
h1 { margin: 0; font-size: clamp(28px, 5vw, 44px); letter-spacing: -.02em; }
.tagline { margin: 12px 0 0; color: var(--muted); font-size: 18px; max-width: 60ch; }
.header-links { margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
.hl { text-decoration: none; font-size: 14px; font-weight: 600; padding: 7px 14px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--surface); }
.hl:hover { border-color: var(--accent); }
.stat { margin-top: 20px; font-size: 13px; color: var(--muted); }

nav.jump { position: sticky; top: 0; z-index: 5;
  background: color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter: saturate(180%) blur(8px); border-bottom: 1px solid var(--line); }
nav.jump .wrap { display: flex; gap: 4px; padding: 10px 24px; }
nav.jump a { text-decoration: none; font-size: 14px; font-weight: 600; color: var(--muted);
  padding: 6px 12px; border-radius: 8px; }
nav.jump a:hover { color: var(--text); background: var(--tag-bg); }

main { padding: 40px 0 72px; }
.bucket { margin-bottom: 52px; scroll-margin-top: 64px; }
.bucket-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 22px; }
.bucket-head h2 { margin: 0; font-size: 22px; letter-spacing: -.01em; }
.count { font-size: 13px; color: var(--muted); background: var(--tag-bg);
  padding: 2px 10px; border-radius: 999px; font-weight: 600; }

.grid { display: grid; gap: 22px; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
.empty { color: var(--muted); font-style: italic; padding: 28px;
  border: 1px dashed var(--line); border-radius: var(--radius); text-align: center; }

.card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  overflow: hidden; box-shadow: var(--shadow); display: flex; flex-direction: column;
  transition: transform .15s ease, border-color .15s ease; }
.card:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 40%, var(--line)); }
.thumb-wrap { display: block; aspect-ratio: 16 / 9; background: var(--tag-bg); overflow: hidden; }
.thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.card-body { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.card-top { display: flex; }
.card-title { margin: 0; font-size: 19px; letter-spacing: -.01em; }
.one-liner { margin: 0; color: var(--muted); }

.pill { display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px; font-weight: 600;
  color: var(--text); background: var(--tag-bg); padding: 4px 11px; border-radius: 999px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

.links { display: flex; gap: 8px; flex-wrap: wrap; }
.btn { text-decoration: none; font-size: 13.5px; font-weight: 600; padding: 8px 14px;
  border-radius: 9px; border: 1px solid var(--line); background: var(--surface); }
.btn:hover { border-color: var(--accent); }
.btn-primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn-primary:hover { filter: brightness(1.07); }

.meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.tag { font-size: 11.5px; color: var(--muted); background: var(--tag-bg); padding: 3px 9px; border-radius: 6px; }
.touched { font-size: 11.5px; color: var(--muted); margin-left: 2px; }

.progress { margin: 2px 0 0; padding: 12px 14px; border-radius: 10px; background: var(--tag-bg);
  display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 13.5px; }
.progress dt { font-weight: 700; color: var(--text); }
.progress dd { margin: 0; color: var(--muted); }

.inside { border-top: 1px solid var(--line); padding-top: 12px; }
.inside summary { cursor: pointer; font-weight: 600; font-size: 14px; }
.comps { list-style: none; margin: 12px 0 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.comp { padding-left: 12px; border-left: 2px solid var(--line); }
.comp-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.comp-name { font-weight: 600; font-size: 14px; }
.comp-desc { margin: 3px 0 0; color: var(--muted); font-size: 13px; }
.mini { font-size: 12.5px; font-weight: 600; color: var(--accent); text-decoration: none; }

/* ---- Books shelf (3D carousel) ---- */
.shelf { margin: 4px 0 8px; }
.shelf-head { display: flex; align-items: center; justify-content: space-between; }
.shelf-head h3 { margin: 0; font-size: 16px; color: var(--muted); font-weight: 600;
  letter-spacing: .01em; }
.shelf-controls { display: flex; gap: 8px; }
.shelf-btn { width: 38px; height: 38px; border-radius: 50%; border: 1px solid var(--line);
  background: var(--surface); color: var(--text); cursor: pointer; font-size: 18px; line-height: 1;
  display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow); }
.shelf-btn:hover { border-color: var(--accent); }
.shelf-track { display: flex; gap: 56px; overflow-x: auto; scroll-snap-type: x mandatory;
  padding: 40px 16px 26px; scroll-behavior: smooth; perspective: 1600px; }
.shelf-track::-webkit-scrollbar { height: 8px; }
.shelf-track::-webkit-scrollbar-thumb { background: var(--line); border-radius: 999px; }

.book { scroll-snap-align: center; flex: 0 0 auto; width: 190px; outline: none;
  display: flex; flex-direction: column; align-items: center; gap: 20px; }
.book-3d { position: relative; width: 190px; height: 280px; transform-style: preserve-3d;
  transform: rotateY(-28deg); transition: transform .55s cubic-bezier(.2,.7,.2,1); }
.book:hover .book-3d, .book:focus-visible .book-3d, .book:focus-within .book-3d {
  transform: rotateY(-6deg) translateZ(12px); }
.book-face { position: absolute; top: 0; left: 0; height: 280px; }
.book-front { width: 190px; transform: translateZ(20px); overflow: hidden;
  border-radius: 2px 5px 5px 2px; background: var(--tag-bg); box-shadow: 0 18px 36px rgba(0,0,0,.32); }
.book-front img { width: 100%; height: 100%; object-fit: cover; display: block; }
.book-front::after { content: ""; position: absolute; inset: 0; border-radius: 2px 5px 5px 2px;
  background: linear-gradient(90deg, rgba(0,0,0,.35) 0, rgba(0,0,0,.05) 5%, rgba(255,255,255,.16) 9%, rgba(255,255,255,0) 16%); }
.book-front--blank { display: flex; align-items: center; justify-content: center; padding: 18px;
  text-align: center; color: #fff; font-weight: 700; font-size: 16px;
  background: var(--spine, #3a3a44); }
.book-spine { width: 40px; left: 0; transform-origin: left center; transform: rotateY(-90deg);
  border-radius: 2px 0 0 2px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(90deg, rgba(0,0,0,.30), rgba(255,255,255,.05)), var(--spine, #3a3a44); }
.book-spine span { writing-mode: vertical-rl; transform: rotate(180deg); color: #fff;
  font-size: 12px; font-weight: 600; white-space: nowrap; opacity: .92; letter-spacing: .02em;
  max-height: 248px; overflow: hidden; text-overflow: ellipsis; padding: 8px 0; }
.book-pages { width: 40px; left: 150px; transform-origin: right center; transform: rotateY(90deg);
  border-radius: 0 4px 4px 0;
  background: repeating-linear-gradient(90deg, #f3f1ea, #f3f1ea 1px, #cfcabb 2px, #f3f1ea 3px); }
.book-3d::after { content: ""; position: absolute; left: 4px; right: 4px; bottom: -24px; height: 26px;
  background: radial-gradient(ellipse at center, rgba(0,0,0,.32), rgba(0,0,0,0) 70%);
  transform: rotateX(82deg); filter: blur(2px); }
.book-info { text-align: center; width: 210px; display: flex; flex-direction: column;
  gap: 6px; align-items: center; }
.book-title { font-weight: 700; font-size: 15px; line-height: 1.3; }
.book-author { color: var(--muted); font-size: 13px; }
.book-sub { color: var(--muted); font-size: 12px; }
.book-actions { margin-top: 4px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: center; }

footer { border-top: 1px solid var(--line); padding: 28px 0; color: var(--muted); font-size: 13px; }

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; scroll-behavior: auto !important; }
  .book-3d { transform: rotateY(-20deg); }
}
"""

PAGE_JS = """
(function () {
  document.querySelectorAll('[data-shelf]').forEach(function (shelf) {
    var track = shelf.querySelector('.shelf-track');
    if (!track) return;
    function step() { return Math.max(220, Math.round(track.clientWidth * 0.7)); }
    var prev = shelf.querySelector('.shelf-prev');
    var next = shelf.querySelector('.shelf-next');
    if (prev) prev.addEventListener('click', function () { track.scrollBy({ left: -step(), behavior: 'smooth' }); });
    if (next) next.addEventListener('click', function () { track.scrollBy({ left: step(), behavior: 'smooth' }); });
  });
})();
"""


def book_pill(s: str) -> str:
    label, color = BOOK_STATUS.get(s, (s.title() if s else "Unknown", "#888"))
    return f'<span class="pill"><span class="dot" style="background:{color}"></span>{e(label)}</span>'


def html_book(b: dict) -> str:
    title = e(b.get("title", "Untitled"))
    spine_attr = f' style="--spine:{e(b["spine_color"])}"' if b.get("spine_color") else ""
    if b.get("cover"):
        front = (f'<div class="book-face book-front"><img src="{e(b["cover"])}" '
                 f'alt="{title} cover" loading="lazy"></div>')
    else:
        front = f'<div class="book-face book-front book-front--blank"><span>{title}</span></div>'
    spine = f'<div class="book-face book-spine"><span>{title}</span></div>'
    pages = '<div class="book-face book-pages"></div>'
    author = f'<div class="book-author">{e(b["author"])}</div>' if b.get("author") else ""
    sub_bits = []
    if b.get("format"): sub_bits.append(e(b["format"]))
    if b.get("year"): sub_bits.append(e(str(b["year"])))
    sub = f'<div class="book-sub">{" · ".join(sub_bits)}</div>' if sub_bits else ""
    buy = f'<a class="btn btn-primary" href="{e(b["buy_url"])}">Buy ↗</a>' if b.get("buy_url") else ""
    status = book_pill(b.get("status", "printed"))
    return (f'<div class="book" tabindex="0">'
            f'<div class="book-3d"{spine_attr}>{front}{spine}{pages}</div>'
            f'<div class="book-info"><div class="book-title">{title}</div>{author}{sub}'
            f'<div class="book-actions">{status}{buy}</div></div></div>')


def html_books_shelf(books: list) -> str:
    ordered = sorted(books, key=lambda b: (_book_rank(b.get("status", "printed")),
                                           b.get("title", "").lower()))
    items = "".join(html_book(b) for b in ordered)
    return ('<div class="shelf" data-shelf>'
            '<div class="shelf-head"><h3>📚 Books</h3>'
            '<div class="shelf-controls">'
            '<button class="shelf-btn shelf-prev" aria-label="Scroll books left">‹</button>'
            '<button class="shelf-btn shelf-next" aria-label="Scroll books right">›</button>'
            '</div></div>'
            f'<div class="shelf-track">{items}</div></div>')


def html_pill(status: str) -> str:
    return (f'<span class="pill"><span class="dot" style="background:{_color(status)}"></span>'
            f'{e(_label(status))}</span>')


def html_component(c: dict) -> str:
    name = e(c.get("name", "Untitled"))
    link = f' <a class="mini" href="{e(c["deep_link"])}">open ↗</a>' if c.get("deep_link") else ""
    desc = f'<p class="comp-desc">{e(c["one_liner"])}</p>' if c.get("one_liner") else ""
    return (f'<li class="comp"><div class="comp-head"><span class="comp-name">{name}</span>'
            f'{html_pill(c.get("status",""))}{link}</div>{desc}</li>')


def html_card(card: dict) -> str:
    name = e(card.get("name", "Untitled"))
    p = ['<article class="card">']
    if card.get("screenshot"):
        p.append(f'<a class="thumb-wrap" href="{e(card.get("live_url") or card.get("repo_url") or "#")}">'
                 f'<img class="thumb" src="{e(card["screenshot"])}" alt="{name} screenshot" loading="lazy"></a>')
    p.append('<div class="card-body">')
    p.append(f'<div class="card-top">{html_pill(card.get("status",""))}</div>')
    p.append(f'<h3 class="card-title">{name}</h3>')
    if card.get("one_liner"):
        p.append(f'<p class="one-liner">{e(card["one_liner"])}</p>')
    links = []
    if card.get("live_url"):
        links.append(f'<a class="btn btn-primary" href="{e(card["live_url"])}">Live ↗</a>')
    if card.get("repo_url"):
        links.append(f'<a class="btn" href="{e(card["repo_url"])}">Code ↗</a>')
    if links:
        p.append(f'<div class="links">{"".join(links)}</div>')
    meta = []
    if card.get("stack"):
        meta.append("".join(f'<span class="tag">{e(t)}</span>' for t in card["stack"]))
    if card.get("last_touched"):
        meta.append(f'<span class="touched">updated {e(card["last_touched"])}</span>')
    if meta:
        p.append(f'<div class="meta">{"".join(meta)}</div>')
    if card.get("left_off") or card.get("next"):
        p.append('<dl class="progress">')
        if card.get("left_off"): p.append(f'<dt>Left off</dt><dd>{e(card["left_off"])}</dd>')
        if card.get("next"): p.append(f'<dt>Next</dt><dd>{e(card["next"])}</dd>')
        p.append('</dl>')
    comps = card.get("components") or []
    if comps:
        p.append('<details class="inside" open><summary>Inside (' + str(len(comps))
                 + ')</summary><ul class="comps">'
                 + "".join(html_component(c) for c in comps) + '</ul></details>')
    p.append('</div></article>')
    return "".join(p)


def build_html(cards: list, books: list, site: dict) -> str:
    accent = site.get("accent", "#4f46e5")
    header_links = "".join(
        f'<a class="hl" href="{e(l.get("url","#"))}">{e(l.get("label","link"))} ↗</a>'
        for l in site.get("links", []) if l.get("url"))

    sections = []
    for key, title in BUCKETS:
        items = sorted([c for c in cards if c.get("bucket") == key],
                       key=lambda c: (_rank(c.get("status","")), c.get("name","").lower()))
        has_books = key == "personal" and bool(books)
        inner = ""
        if has_books:
            inner += html_books_shelf(books)
        if items:
            inner += f'<div class="grid">{"".join(html_card(c) for c in items)}</div>'
        if not items and not has_books:
            inner = '<p class="empty">Nothing here yet.</p>'
        count = len(items) + (len(books) if has_books else 0)
        sections.append(
            f'<section id="{key}" class="bucket"><div class="bucket-head">'
            f'<h2>{e(title)}</h2><span class="count">{count}</span></div>{inner}</section>')

    nav = "".join(f'<a href="#{key}">{e(title)}</a>' for key, title in BUCKETS)
    total = len(cards) + len(books)

    return f"""<!doctype html>
<html lang="en" style="--accent: {e(accent)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(site['title'])}</title>
<meta name="description" content="{e(site['tagline'])}">
<style>{PAGE_CSS}</style>
</head>
<body>
<header class="site"><div class="site-inner">
  <p class="eyebrow">Portfolio</p>
  <h1>{e(site['title'])}</h1>
  <p class="tagline">{e(site['tagline'])}</p>
  {f'<div class="header-links">{header_links}</div>' if header_links else ''}
  <p class="stat">{total} item{'s' if total != 1 else ''} · last updated {date.today().isoformat()}</p>
</div></header>
<nav class="jump"><div class="wrap">{nav}</div></nav>
<main><div class="wrap">{"".join(sections)}</div></main>
<footer><div class="wrap">Generated by the project-portfolio skill · rebuild with <code>python build.py</code></div></footer>
<script>{PAGE_JS}</script>
</body>
</html>
"""


# ===========================================================================

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    cards = load_json_dir(root / "projects")
    books = load_json_dir(root / "books")
    site = load_site(root)
    (root / "README.md").write_text(build_readme(cards, books, site), encoding="utf-8")
    (root / "index.html").write_text(build_html(cards, books, site), encoding="utf-8")
    print(f"Built README.md + index.html from {len(cards)} project(s) and {len(books)} book(s) in {root}")


if __name__ == "__main__":
    main()
