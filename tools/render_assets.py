#!/usr/bin/env python3
"""
render_assets.py - turn a digest markdown file into local, copy-pasteable assets.

Renders:
  * <name>.pdf            - the whole digest, styled for reading or printing
  * <name>-cover.png      - 1200x630 social card, title + the day's thread
  * <name>-<category>.png - one card per category

Everything is LOCAL. This script never touches the network, never reads an API key
and never publishes anywhere. You take the files and post them yourself.

Stdlib only, Python 3.8+. HTML -> PDF/PNG via a headless Chromium already on the
machine (Edge on Windows), so there is nothing to install: no pandoc, no
wkhtmltopdf, no ImageMagick, no flameshot.

    python tools/render_assets.py output/2026-10-09.md
    python tools/render_assets.py output/2026-10-09.md --outdir output/assets
    python tools/render_assets.py output/2026-10-09.md --no-cards
    python tools/render_assets.py output/2026-10-09.md --engine-path "C:/.../msedge.exe"
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------- #
# Browser discovery
# --------------------------------------------------------------------------- #

_BROWSER_CANDIDATES = {
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ],
    "chromium": [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ],
}

_ENV_KEYS = ("DIGEST_BROWSER", "CHROME_PATH", "PUPPETEER_EXECUTABLE_PATH")


def find_browser(explicit: str | None = None) -> str | None:
    """Locate a Chromium-family browser, or None so the caller can degrade."""
    if explicit:
        return explicit if Path(explicit).exists() else None

    for key in _ENV_KEYS:
        val = os.environ.get(key)
        if val and Path(val).exists():
            return val

    for paths in _BROWSER_CANDIDATES.values():
        for raw in paths:
            # %LOCALAPPDATA% etc. live in the candidate strings on Windows.
            p = Path(os.path.expandvars(raw))
            if p.exists():
                return str(p)

    for name in ("msedge", "chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _run_browser(binary: str, url: str, out_file: Path, *flags: str,
                 timeout: int = 90, retries: int = 2) -> bool:
    """Render with a headless Chromium; trust only that out_file appeared.

    No --user-data-dir: on Windows that makes Edge hang against a fresh profile
    dir. Exit status is ignored because Edge logs noise to stderr and still
    succeeds. One retry, since a cold Edge start occasionally produces nothing.
    """
    for _ in range(retries + 1):
        out_file.unlink(missing_ok=True)
        cmd = [binary, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", *flags, url]
        try:
            subprocess.run(cmd, timeout=timeout, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            pass
        except OSError:
            return False
        if out_file.exists() and out_file.stat().st_size > 0:
            return True
    return False


# --------------------------------------------------------------------------- #
# Minimal markdown -> HTML
# --------------------------------------------------------------------------- #

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
# _text_ is standard markdown italics and the mood line uses it. The guards keep
# snake_case_identifiers and filenames from being eaten.
_ITALIC_US = re.compile(r"(?<!\w)_([^_\n]+)_(?!\w)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
# (?<!=") so it does not re-wrap a URL that _LINK just put inside an href="..."
_BARE_URL = re.compile(r'(?<![=\w/@.\-"])(https?://[^\s<>)\]]+[^\s<>)\].,;:!?])')
# A paragraph that is nothing but bold text is the in-depth lead sentence.
_WHOLE_BOLD = re.compile(r"^\*\*([^*]+)\*\*$")
# "![alt](path)" - illustrations only, local paths, so a render stays offline.
_IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$")
# The three label-value lines the digest puts under an in-depth hook.
# Note the colon sits inside the bold: **By:** not **By**:.
_FACT = re.compile(r"^\*\*(By|Author|Plainly|TL;DR|TLDR):\*\*\s*(.*)$")
# The "what I'd use this for" line.
_USE = re.compile(r"^\*\*(Use it for|Use for):\*\*\s*(.*)$")


def inline(text: str) -> str:
    """Escape, then re-introduce the inline markdown we support.

    Code spans are extracted to placeholders first so their contents survive
    escaping and are never re-parsed as bold/italic/link markup.
    """
    stash: list[str] = []

    def keep_code(m: re.Match) -> str:
        stash.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(stash) - 1}\x00"

    text = _INLINE_CODE.sub(keep_code, text)

    text = html.escape(text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = _ITALIC_US.sub(r"<em>\1</em>", text)
    text = _LINK.sub(r'<a href="\2">\1</a>', text)
    text = _BARE_URL.sub(r'<a href="\1">\1</a>', text)

    for i, code in enumerate(stash):
        text = text.replace(f"\x00{i}\x00", code)
    return text


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_]+", "-", s)[:60] or "card"


def clip(text: str, limit: int) -> str:
    """First sentence of some markdown, flattened and hard-cut to fit a card.

    Cards are 1200px wide. Long headlines silently push the chips off the
    bottom, so every string that reaches a card goes through here first.
    """
    t = re.sub(r"[*`>#]+", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    s = m.group(1) if m else t
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s


def md_to_html_body(md: str) -> str:
    """Block-level markdown conversion. Supports the subset a digest actually uses."""
    out: list[str] = []
    lines = md.replace("\r\n", "\n").split("\n")
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # --- horizontal rule ---
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            out.append("<hr>")
            i += 1
            continue

        # --- heading ---
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            # Sections get an id so The Batch-style overview can link to them.
            anchor = f' id="sec-{slugify(m.group(2).strip())}"' if level == 2 else ""
            out.append(f"<h{level}{anchor}>{inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # --- illustration ---
        if stripped.startswith("!["):
            im = _IMAGE.match(stripped)
            if im:
                alt, src = im.group(1), im.group(2)
                fig = f'<figure><img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}">'
                if alt:
                    fig += f"<figcaption>{inline(alt)}</figcaption>"
                out.append(fig + "</figure>")
                i += 1
                continue

        # --- blockquote (consecutive > lines) ---
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            text = " ".join(x.strip() for x in buf)
            # A blockquote that is only bold text is a pull-quote (The Batch),
            # not an aside. Anything else keeps the quiet aside styling.
            cls = "pq" if _WHOLE_BOLD.match(text) else ""
            attr = f' class="{cls}"' if cls else ""
            out.append(f"<blockquote{attr}>{inline(text)}</blockquote>")
            continue

        # --- table ---
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            head = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            body = []
            while i < n and lines[i].strip().startswith("|"):
                body.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head_html = "".join(f"<th>{inline(c)}</th>" for c in head)
            rows_html = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body
            )
            out.append(f"<table><thead><tr>{head_html}</tr></thead><tbody>{rows_html}</tbody></table>")
            continue

        # --- list (flat and two-space nested) ---
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            base_indent = len(line) - len(line.lstrip())
            items: list[str] = []
            nested: list[str] = []
            while i < n:
                cur = lines[i]
                if not cur.strip():
                    # a blank line ends the list only if the next line isn't one
                    if i + 1 < n and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i + 1]):
                        i += 1
                        continue
                    break
                mm = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", cur)
                if not mm:
                    # continuation of the previous item
                    if items:
                        items[-1] += " " + cur.strip()
                        i += 1
                        continue
                    break
                indent = len(mm.group(1))
                body_txt = mm.group(3).strip()
                if indent > base_indent + 1 and nested:
                    nested[-1] += " " + body_txt
                else:
                    nested = []
                    items.append(body_txt)
                i += 1
            facts: list[str] = []
            uses: list[str] = []
            plain: list[str] = []
            for x in items:
                fm = _FACT.match(x)
                if fm:
                    facts.append(
                        f'<div><span class="k">{html.escape(fm.group(1))}</span> '
                        f"{inline(fm.group(2))}</div>"
                    )
                    continue
                um = _USE.match(x)
                if um:
                    uses.append(
                        f'<p class="use"><span class="k">{html.escape(um.group(1))}:</span> '
                        f"{inline(um.group(2))}</p>"
                    )
                    continue
                plain.append(x)

            if facts:
                out.append('<div class="facts">' + "".join(facts) + "</div>")
            for u in uses:
                out.append(u)
            if plain:
                lis = "".join(f"<li>{inline(x)}</li>" for x in plain)
                out.append(f'<ul class="compact">{lis}</ul>')
            continue

        # --- paragraph (merge soft-wrapped lines) ---
        buf = [stripped]
        i += 1
        while i < n and lines[i].strip() and not re.match(
            r"^\s*([-*+]|\d+\.)\s+", lines[i]
        ) and not re.match(r"^\s*#{1,6}\s", lines[i]) and not lines[i].strip().startswith(">"):
            if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", lines[i].strip()):
                break
            buf.append(lines[i].strip())
            i += 1
        para = " ".join(buf)
        # "Use it for:" often stands alone as a paragraph rather than a list item.
        um = _USE.match(para)
        if um:
            out.append(
                f'<p class="use"><span class="k">{html.escape(um.group(1))}:</span> '
                f"{inline(um.group(2))}</p>"
            )
            continue
        # A bare URL on its own line is a source reference, not prose.
        if _BARE_URL.fullmatch(para):
            out.append(f'<p class="srcurl">{inline(para)}</p>')
            continue
        # A paragraph that is entirely bold is the in-depth item's lead sentence.
        hb = _WHOLE_BOLD.match(para)
        if hb:
            out.append(f'<p class="hook">{inline(hb.group(1))}</p>')
            continue
        out.append(f"<p>{inline(para)}</p>")

    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Structure extraction (drives the cards)
# --------------------------------------------------------------------------- #

_ITEM_NAME = re.compile(
    r"^\s*(?:[-*+]\s+|\d+\.\s+)?(?:#{3,4}\s+|\*\*)(\*\*)?([^\n*]+?)(?:\*\*)?(?:\s*[—-].*)?$"
)
_BOLD_NAME = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\*\*(.+?)\*\*")
_H3_NAME = re.compile(r"^#{3}\s+(.+?)\s*$")


def extract_structure(md: str) -> dict:
    """Pull out the title, mood line, thread and per-category item names."""
    lines = md.replace("\r\n", "\n").split("\n")

    title = ""
    mood = ""
    thread: list[str] = []
    categories: list[dict] = []

    current: dict | None = None
    in_thread = False

    for idx, raw in enumerate(lines):
        line = raw.rstrip()
        s = line.strip()

        if not s:
            continue

        if s.startswith("# ") and not title:
            title = s[2:].strip()
            continue

        # italic mood line directly under the H1
        if not mood and title and idx < 8 and re.fullmatch(r"_[^_]+_", s):
            mood = s.strip("_")
            continue

        if re.match(r"^##\s+", s):
            name = s[3:].strip()
            if name.lower().startswith("thread of the day"):
                in_thread = True
                current = None
                continue
            in_thread = False
            # strip a trailing "(10)" count
            clean = re.sub(r"\s*\(\d+\)\s*$", "", name).strip()
            current = {"name": clean, "items": [], "hook": ""}
            categories.append(current)
            continue

        if in_thread:
            if s.startswith("---"):
                break
            if s.startswith(">"):
                thread.append(s.lstrip("> ").strip())
            elif current is None and not s.startswith(("#", "---")):
                thread.append(s)
            continue

        if current is not None:
            # "### name" is the in-depth form: the bold line right after it is the hook.
            h3 = _H3_NAME.match(s)
            if h3:
                nm = h3.group(1).strip().strip("*").strip()
                if nm and nm not in current["items"]:
                    current["items"].append(nm)
                if not current["hook"]:
                    nxt = ""
                    for look in lines[idx + 1: idx + 4]:   # skip the blank line
                        if look.strip():
                            nxt = look.strip()
                            break
                    if nxt.startswith("**"):
                        cand = nxt.strip("*").strip()
                        if not cand.lower().startswith(("use it for", "use for")):
                            current["hook"] = cand
                continue

            b = _BOLD_NAME.match(s)
            if b:
                nm = b.group(1).strip().strip("*").strip()
                # "- **By:** ..." and friends are field labels, not items - on a card
                # they would render as chips reading "By:" and "TL;DR:".
                if nm.endswith(":") or nm.lower() in {"plainly", "tl;dr", "tldr", "by"}:
                    continue
                if nm and nm not in current["items"]:
                    current["items"].append(nm)
                continue

    return {
        "title": title,
        "mood": mood,
        "thread": " ".join(t for t in thread if t),
        "categories": [c for c in categories if c["items"]],
    }


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #

DOC_CSS = """
:root {
  --ink:#14161a; --muted:#5d6673; --faint:#8b95a3; --line:#e3e7ec; --accent:#3b5bdb;
  --card:#f6f8fa; --code-bg:#f0f2f5; --quote:#11161d;
  /* Serif for prose, sans for furniture. Import AI reads as a paper, not a feed. */
  --serif: Georgia, "Iowan Old Style", Charter, "Palatino Linotype", "Book Antiqua", serif;
  --sans: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  --measure: 34em;
}
* { box-sizing: border-box; }
body {
  font-family: var(--serif);
  color: var(--ink); background:#fff; line-height:1.68;
  font-size: 10.6pt; margin:0 auto; padding: 0;
  max-width: var(--measure);
}

/* ---- masthead ---------------------------------------------------------- */
.masthead { border-bottom: 3px solid var(--accent); padding-bottom: 1.1em; margin-bottom: 2.2em; }
.kicker {
  font-family: var(--sans); font-size: 7.6pt; font-weight: 700; letter-spacing:.16em;
  text-transform: uppercase; color: var(--accent); margin: 0 0 .9em;
}
.masthead h1 {
  font-size: 27pt; line-height:1.12; letter-spacing:-.021em; font-weight: 700;
  margin: 0 0 .3em; border: 0; padding: 0;
}
.deck {
  font-size: 13.4pt; line-height:1.42; color: var(--muted); font-style: italic;
  margin: 0 0 1.1em; padding: 0;
}
.colophon {
  font-family: var(--sans); font-size: 7.4pt; letter-spacing:.1em; text-transform: uppercase;
  color: var(--faint); margin: 0;
}

/* ---- The Batch style overview: one line per section, scannable ----------- */
.overview {
  background: var(--card); border:1px solid var(--line); border-radius: 8px;
  padding: 1.1em 1.4em .6em; margin: 0 0 2.4em;
}
.overview-h {
  font-family: var(--sans); font-size: 7.6pt; font-weight: 700; letter-spacing:.16em;
  text-transform: uppercase; color: var(--faint); margin: 0 0 .7em;
}
.overview ol { margin:0; padding-left: 1.5em; }
.overview li { margin:.34em 0; font-size: 10pt; }
.overview .n { font-family: var(--sans); font-size: 8.4pt; color: var(--faint); }
.overview a { border:0; color: var(--ink); }

/* ---- section heads ----------------------------------------------------- */
h2 {
  font-size: 15.5pt; letter-spacing:-.012em; font-weight:700;
  margin: 2.6em 0 .8em; padding-bottom:.3em; border-bottom:1px solid var(--line);
}
h3 {
  font-family: var(--sans); font-size: 9.6pt; font-weight: 700; letter-spacing:.01em;
  margin: 2em 0 .35em;
}
h4 { font-size: 10.6pt; margin: 1.5em 0 .3em; color:var(--muted); }
p { margin: .6em 0; }

/* ---- item furniture ---------------------------------------------------- */
.hook {                       /* the in-depth lead sentence - Import AI style */
  font-size: 12.6pt; line-height:1.42; font-weight: 700; margin: .1em 0 .5em;
}
.facts {                     /* By / Plainly / TL;DR as a label-value grid */
  font-family: var(--sans); font-size: 8.6pt; line-height:1.6;
  margin: .5em 0 .9em; padding: .55em .8em;
  background: var(--card); border-left: 2px solid var(--accent); border-radius: 0 5px 5px 0;
}
.facts div { margin: .16em 0; }
.facts .k { color: var(--faint); letter-spacing:.06em; text-transform: uppercase; font-weight:700; font-size:7.6pt; }
.use {
  font-family: var(--sans); font-size: 9.4pt; line-height:1.6;
  margin: .9em 0 1.1em; padding-left:.85em; border-left:2px solid var(--accent);
}
.use .k { font-weight:700; letter-spacing:.02em; }
.srcurl { font-family: var(--sans); font-size: 8.2pt; margin: -.6em 0 1.6em; word-break: break-all; }
.srcurl a { color: var(--faint); border:0; }

ul, ol { margin: .4em 0 .9em; padding-left: 1.4em; }
li { margin: .36em 0; }
li > ul { margin: .3em 0 .2em; }
.compact { font-size: 10pt; }   /* the run of short items under an in-depth one */

code {
  font-family: "Cascadia Mono", Consolas, "SF Mono", Menlo, monospace;
  font-size: .87em; background: var(--code-bg);
  padding: .1em .38em; border-radius: 4px; border: 1px solid #e6e9ed;
}
pre { background:#11161d; color:#e6edf3; padding: .9em 1.1em; border-radius: 8px; overflow-x:auto;
      font-family: "Cascadia Mono", Consolas, monospace; font-size: 8.6pt; line-height:1.5; }
pre code { background:none; border:none; color:inherit; padding:0; }
a { color: var(--accent); text-decoration: none; border-bottom: 1px solid rgba(59,91,219,.28); }
strong { font-weight: 700; }
hr { border:0; border-top:1px solid var(--line); margin: 2.4em 0; }

/* ---- The Batch style pull-quote ---------------------------------------- */
blockquote.pq {
  margin: 1.7em 0; padding: 1.1em 0; background: none;
  border: 0; border-top: 2px solid var(--ink); border-bottom: 1px solid var(--line);
  border-radius: 0; color: var(--quote); text-align: center;
  font-size: 13pt; line-height:1.45; font-style: italic;
}
blockquote.pq p { margin: 0; }
/* any other blockquote stays a plain aside */
blockquote { margin: 1em 0; padding: .75em 1.1em; background: var(--card);
             border-left: 3px solid var(--accent); border-radius: 0 6px 6px 0; color:#333a45; }
blockquote p { margin: .3em 0; }

/* ---- illustrations ----------------------------------------------------- */
figure { margin: 1.5em 0; }
figure img { display:block; width:100%; border-radius: 7px; }
figcaption {
  font-family: var(--sans); font-size: 7.8pt; color: var(--faint);
  margin-top: .5em; letter-spacing:.03em;
}

table { border-collapse: collapse; width:100%; margin:1em 0; font-family: var(--sans); font-size: 8.6pt; }
th, td { border:1px solid var(--line); padding: .42em .6em; text-align:left; vertical-align:top; }
th { background: var(--card); font-weight:650; }
td:first-child, th:first-child { white-space: nowrap; }

@page { size: A4; margin: 16mm 15mm; }
@media print {
  body { font-size: 10.2pt; }
  h2 { page-break-after: avoid; }
  h3, h4, .hook { page-break-after: avoid; }
  .facts, .use, li, blockquote, figure { page-break-inside: avoid; }
  a { color: var(--ink); border-bottom-color:#ccd2da; }
}
"""

CARD_CSS = """
* { box-sizing:border-box; margin:0; padding:0; }
body {
  width:1200px; height:630px; overflow:hidden; position:relative;
  font-family:"Segoe UI",-apple-system,"Helvetica Neue",Arial,sans-serif;
  background:
    radial-gradient(1200px 620px at 12% -10%, #2b3f8f 0%, transparent 58%),
    radial-gradient(900px 560px at 105% 115%, #14304d 0%, transparent 60%),
    linear-gradient(158deg,#0d1220 0%,#151d31 52%,#0b0f1a 100%);
  color:#eef2f8; padding:56px 60px; display:flex; flex-direction:column;
}
.kicker {
  font-size:20px; letter-spacing:.16em; text-transform:uppercase;
  color:#8fb0ff; font-weight:650; margin-bottom:20px;
}
h1 {
  font-size:50px; line-height:1.13; letter-spacing:-.025em; font-weight:700; max-width:1050px;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;
}
h1 em { font-style:normal; color:#8fb0ff; }
.sub {
  font-size:25px; line-height:1.42; color:#c3cfe2; margin-top:22px; max-width:1010px;
  font-weight:400; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical;
  overflow:hidden;
}
.rule { width:76px; height:5px; background:#5b83f5; border-radius:3px; margin:28px 0 0; }
.items { margin-top:auto; display:flex; flex-wrap:wrap; gap:9px 10px; }
.chip {
  font-size:18.5px; color:#dbe4f2; background:rgba(255,255,255,.075);
  border:1px solid rgba(255,255,255,.14); border-radius:999px; padding:7px 17px;
}
.foot {
  margin-top:auto; padding-top:22px; display:flex; justify-content:space-between;
  align-items:baseline; font-size:19px; color:#8b99b0;
}
.brand { color:#cfd9e8; font-weight:600; letter-spacing:.01em; }
.thread-quote {
  font-size:29px; line-height:1.4; font-weight:600; color:#f2f6fc; max-width:1040px;
}
"""


def wrap_document(title: str, body: str, css: str) -> str:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )


def _data_uri(png: Path) -> str:
    """Inline a PNG so the PDF render needs no file:// or network access."""
    return "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode("ascii")


_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _strip_front_matter(md: str) -> str:
    """Drop the H1, the mood line and HTML comments - the masthead renders them."""
    md = _HTML_COMMENT.sub("", md)
    lines = md.replace("\r\n", "\n").split("\n")
    for i, raw in enumerate(lines):
        if re.match(r"^##\s+", raw.strip()):
            return "\n".join(lines[i:])
    return md


def build_document(md: str, struct: dict, issue: str, date: str,
                   images: dict[str, Path]) -> tuple[str, str]:
    """Masthead + scannable overview + body. Returns (title, html)."""
    title = struct["title"] or "Daily Interest Digest"
    mood = struct["mood"]

    head = [
        '<header class="masthead">',
        f'<p class="kicker">{html.escape(issue)}</p>',
        f"<h1>{inline(title)}</h1>",
    ]
    if mood:
        head.append(f'<p class="deck">{inline(mood)}</p>')
    head.append(f'<p class="colophon">{html.escape(date)}</p>')
    head.append("</header>")

    # One line per section, TLDR-shaped: enough to decide where to start reading.
    # This is the only place the digest gets TLDR's scannability; the body below
    # stays Import AI dense.
    cats = [c for c in struct["categories"] if c["name"].lower() != "thread of the day"]
    if cats:
        rows = []
        for c in cats:
            n = len(c["items"])
            lead = c["hook"] or f"{n} item{'s' if n != 1 else ''}."
            anchor = f'sec-{slugify(c["name"])}'
            rows.append(
                f'<li><span class="n">{n}</span> '
                f'<a href="#{anchor}">{html.escape(c["name"])}</a> — {inline(lead)}</li>'
            )
        head.append(
            '<section class="overview"><p class="overview-h">In this issue</p><ol>'
            + "".join(rows)
            + "</ol></section>"
        )

    body = md_to_html_body(_strip_front_matter(md))
    # The lead illustration goes under the masthead, ahead of the overview.
    if "cover" in images:
        body = (
            f'<figure><img src="{_data_uri(images["cover"])}" alt=""></figure>' + body
        )

    # The Thread section already renders as a normal section - no colophon repeat.
    html_doc = "".join(head) + body
    return title, wrap_document(title, html_doc, DOC_CSS)


def build_card(kicker: str, headline: str, sub: str, chips: list[str],
               footer: str, date: str) -> str:
    chip_html = "".join(f'<div class="chip">{html.escape(c)}</div>' for c in chips[:6])
    parts = [
        f'<div class="kicker">{html.escape(kicker)}</div>',
        f"<h1>{inline(headline)}</h1>",
    ]
    if sub:
        parts.append(f'<div class="sub">{inline(sub)}</div>')
    if chip_html:
        parts.append(f'<div class="items">{chip_html}</div>')
    parts.append(
        f'<div class="foot"><div class="brand">{html.escape(footer)}</div>'
        f"<div>{html.escape(date)}</div></div>"
    )
    return wrap_document(kicker + " " + headline, "".join(parts), CARD_CSS)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def date_of(path: Path) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if m:
        return m.group(1)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.read_text(encoding="utf-8", errors="replace")[:600])
    return m.group(1) if m else ""


def issue_no(struct: dict, date: str) -> str:
    """Import AI numbers its issues. Derive the number from the digest's own age."""
    ledger = Path(__file__).resolve().parent.parent / "ledger" / "INDEX.md"
    days: set[str] = set()
    if ledger.exists():
        text = ledger.read_text(encoding="utf-8", errors="replace")
        days = set(re.findall(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", text, re.M))
    if date and date not in days:
        days.add(date)          # this run hasn't been written to the ledger yet
    return f"Issue {len(days)}" if days else "Daily Interest Digest"


_ILLUSTRATION_PROMPT = (
    "Editorial illustration for a technical newsletter. Muted two-colour risograph "
    "style, limited palette of deep navy, warm cream and one accent. Flat geometric "
    "shapes, subtle paper grain, generous negative space. No text, no words, no "
    "letters, no logos. Aspect ratio {w}:{h}."
)


def generate_illustration(prompt_text: str, out_png: Path, w: int, h: int,
                          api_key: str) -> bool:
    """One illustration via the OpenAI images API. Returns False on any failure."""
    try:
        payload = json.dumps({
            "model": "gpt-image-1",
            "prompt": prompt_text.format(w=w, h=h),
            "size": "auto",
            "output_format": "png",
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode())
        out_png.write_bytes(base64.b64decode(body["data"][0]["b64_json"]))
        return True
    except Exception:
        return False


def _selftest() -> int:
    """Assert-based self-check for the parser. Run after editing the markdown rules."""
    sample = """# Daily Interest Digest — 2026-10-09

_Quiet Tuesday. Two things actually shipped._

## Agent skills (3)

- **mattpocock/skills@tdd** — 1M installs. `npm i -g foo`.
  **Use it for:** testing.
  [repo](https://example.com/a)

### fauxnix

**Your agents get a real shell on Windows.**

- **By:** 20000419 · 823★
- **TL;DR:** the WSL prompt is now optional.

**Use it for:** default shell.

## Thread of the day

**Nobody can verify the agent is done.** Two projects attacked it.

> Worth the fifteen minutes if you run more than one agent.

---
_generated_
"""
    s = extract_structure(sample)
    assert s["title"] == "Daily Interest Digest — 2026-10-09", s["title"]
    assert s["mood"].startswith("Quiet Tuesday"), s["mood"]
    assert len(s["categories"]) == 1, s["categories"]
    cat = s["categories"][0]
    assert cat["name"] == "Agent skills", cat["name"]      # "(3)" stripped
    assert cat["items"] == ["mattpocock/skills@tdd", "fauxnix"], cat["items"]
    assert cat["hook"] == "Your agents get a real shell on Windows.", cat["hook"]
    assert "Nobody can verify the agent is done" in s["thread"], s["thread"]
    assert "Worth the fifteen minutes" in s["thread"], s["thread"]

    h = md_to_html_body(sample)
    assert "<h1>" in h and 'id="sec-agent-skills-3"' in h, h[:200]
    assert '<h2 id="sec-agent-skills-3">Agent skills (3)</h2>' in h, h[:300]
    assert "<strong>Nobody" in h, h[:400]                    # thread body captured
    assert '<a href="https://example.com/a">repo</a>' in h
    assert "<code>npm i -g foo</code>" in h
    assert "<li>" in h and "mattpocock/skills@tdd</strong>" in h
    assert "<em>Quiet Tuesday." in h

    # article furniture: hook / facts / use / pull-quote / src / figure
    assert '<p class="hook">Your agents get a real shell on Windows.</p>' in h, h
    assert '<div class="facts">' in h and "823★" in h, h
    assert '<p class="use">' in h and "default shell" in h, h
    assert '<ul class="compact">' in h, h
    fig = md_to_html_body("![a risograph terminal](assets/cover.png)")
    assert '<figure><img src="assets/cover.png" alt="a risograph terminal">' in fig, fig
    assert "<figcaption>" in fig, fig
    # a bold-only quote is a pull-quote; a plain one stays an aside
    assert md_to_html_body("> **Pull this.**").startswith('<blockquote class="pq">')
    assert md_to_html_body("> just an aside").startswith("<blockquote>")

    # the overview is the one TLDR-shaped part: one line per section, linked
    _t, doc = build_document(sample, s, "Issue 1", "2026-10-09", {})
    assert '<p class="kicker">Issue 1</p>' in doc
    assert '<section class="overview">' in doc and "In this issue" in doc
    assert '<a href="#sec-agent-skills">Agent skills</a>' in doc, doc[:2000]
    assert "Your agents get a real shell on Windows." in doc
    # the masthead owns the H1 and mood line; the body must not repeat them
    assert doc.count("<h1>") == 1, doc.count("<h1>")
    assert doc.count("Quiet Tuesday") == 1, doc.count("Quiet Tuesday")
    # Thread renders once, as a section - never appended again as a colophon
    assert doc.count("Thread of the day") == 1, doc.count("Thread of the day")
    assert "colophon-block" not in doc
    # comments never leak into the rendered document
    assert "WHAT THIS FILE IS" not in _strip_front_matter(
        "<!-- WHAT THIS FILE IS x -->\n# T\n_Quiet Tuesday._\n\n## A\nbody\n"
    )

    # code spans must survive escaping, not be re-parsed as markdown
    assert md_to_html_body("`a **b**`").count("<code>") == 1
    # clip() is the only thing standing between the layout and an overflowing card
    assert len(clip("word " * 200, 80)) <= 81
    assert clip("One. Two. Three.", 100) == "One."

    print("selftest: OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a digest to PDF + social cards (local only).")
    ap.add_argument("markdown", type=Path, nargs="?", help="digest .md file")
    ap.add_argument("--selftest", action="store_true", help="check the markdown parser and exit")
    ap.add_argument("--outdir", type=Path, default=None, help="default: <md parent>/assets")
    ap.add_argument("--no-cards", action="store_true", help="PDF only")
    ap.add_argument("--no-pdf", action="store_true", help="cards only")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=630)
    ap.add_argument("--engine-path", default=None, help="explicit Chromium/Edge executable")
    ap.add_argument("--browser", default=None, help="auto|edge|chrome|chromium")
    ap.add_argument("--title", default=None, help="override the PDF document title")
    ap.add_argument("--footer", default="Daily Interest Digest")
    ap.add_argument("--illustrate", action="store_true",
                    help="generate one editorial illustration for the masthead "
                         "(needs OPENAI_API_KEY; skipped silently without it)")
    ap.add_argument("--il-width", type=int, default=1536)
    ap.add_argument("--il-height", type=int, default=640)
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if args.markdown is None:
        ap.error("markdown is required (or use --selftest)")

    if not args.markdown.exists():
        print(f"error: no such file: {args.markdown}", file=sys.stderr)
        return 1

    # Edge resolves --print-to-pdf / --screenshot against its OWN directory, not the
    # caller's cwd, so a relative outdir silently writes nothing. Absolute, always.
    md_path = args.markdown.resolve()
    outdir = (args.outdir or (md_path.parent / "assets")).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    md = md_path.read_text(encoding="utf-8", errors="replace")
    stem = md_path.stem
    date = date_of(md_path)

    binary = find_browser(args.engine_path)
    result = {"source": str(md_path), "outdir": str(outdir),
              "engine": binary, "pdf": None, "cards": [], "warnings": []}

    if binary is None:
        result["warnings"].append(
            "No Chromium/Edge found - wrote HTML only. Install Edge or Chrome, "
            "or set DIGEST_BROWSER to an executable path."
        )

    tmp = Path(tempfile.mkdtemp(prefix="digest-html-"))

    try:
        struct = extract_structure(md)

        # ---- PDF ------------------------------------------------------- #
        if not args.no_pdf:
            images: dict[str, Path] = {}
            if args.illustrate:
                key = os.environ.get("OPENAI_API_KEY")
                if not key:
                    result["warnings"].append(
                        "--illustrate needs OPENAI_API_KEY; rendering without art."
                    )
                else:
                    art = tmp / "cover.png"
                    prompt = _ILLUSTRATION_PROMPT + "\n\nMood: " + (
                        struct["mood"] or struct["title"] or "a day in AI tooling"
                    )
                    if generate_illustration(prompt, art, args.il_width, args.il_height, key):
                        images["cover"] = art
                    else:
                        result["warnings"].append("illustration failed; rendering without art.")

            title, doc = build_document(md, struct, issue_no(struct, date), date, images)
            doc_path = tmp / "digest.html"
            doc_path.write_text(doc, encoding="utf-8")
            target = outdir / f"{stem}.pdf"
            if binary:
                # No --no-pdf-header-footer: this Edge build rejects the switch
                # and writes no file. @page margins handle the spacing instead.
                if _run_browser(binary, doc_path.as_uri(), target,
                                f"--print-to-pdf={target.as_posix()}"):
                    result["pdf"] = str(target)
                else:
                    result["warnings"].append(f"PDF render failed, HTML kept at {doc_path}")
            else:
                result["warnings"].append(f"HTML written to {doc_path}")

        # ---- cards ----------------------------------------------------- #
        if not args.no_cards:
            cat_list = struct["categories"]
            specs = []
            if struct["thread"] or struct["title"]:
                headline = clip(struct["mood"] or struct["title"] or "Daily Interest Digest", 88)
                specs.append(("cover", clip(struct["title"] or "Daily Interest Digest", 60),
                              headline, clip(struct["thread"], 150), [c["name"] for c in cat_list]))

            for cat in cat_list:
                headline = cat["hook"] or f"{len(cat['items'])} things worth your time."
                specs.append((slugify(cat["name"]), clip(cat["name"], 44),
                              clip(headline, 110), "", cat["items"]))

            for key, kicker, headline, sub, chips in specs:
                card = build_card(kicker, headline, sub, chips, args.footer, date)
                cpath = tmp / f"card-{key}.html"
                cpath.write_text(card, encoding="utf-8")
                target = outdir / f"{stem}-{key}.png"
                if binary and _run_browser(
                    binary, cpath.as_uri(), target,
                    f"--screenshot={target.as_posix()}",
                    f"--window-size={args.width},{args.height}",
                ):
                    result["cards"].append(str(target))
                else:
                    result["warnings"].append(f"card '{key}' failed")
    finally:
        if not result["warnings"] or binary is None:
            shutil.rmtree(tmp, ignore_errors=True)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"engine : {result['engine'] or 'NOT FOUND'}")
        print(f"outdir : {outdir}")
        print(f"pdf    : {result['pdf'] or '-'}")
        print(f"cards  : {len(result['cards'])}")
        for c in result["cards"]:
            print(f"   {Path(c).name}")
        for w in result["warnings"]:
            print(f"warn   : {w}")
    return 0 if result["pdf"] or result["cards"] else 2


if __name__ == "__main__":
    sys.exit(main())