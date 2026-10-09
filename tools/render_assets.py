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
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
            out.append(f"<h{level}>{inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # --- blockquote (consecutive > lines) ---
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{inline(' '.join(x.strip() for x in buf))}</blockquote>")
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
            lis = "".join(f"<li>{inline(x)}</li>" for x in items)
            out.append(f"<ul>{lis}</ul>")
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
        out.append(f"<p>{inline(' '.join(buf))}</p>")

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
  --ink:#14161a; --muted:#5d6673; --line:#e3e7ec; --accent:#3b5bdb;
  --card:#f6f8fa; --code-bg:#f0f2f5;
}
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  color: var(--ink); background:#fff; line-height:1.62;
  font-size: 11.2pt; margin:0; padding: 0 2.2em 3em;
}
h1 {
  font-size: 24pt; line-height:1.2; letter-spacing:-.02em;
  margin: 0 0 .25em; padding-bottom:.45em; border-bottom: 3px solid var(--accent);
}
h2 {
  font-size: 15pt; letter-spacing:-.01em; margin: 2.4em 0 .7em;
  padding-bottom:.28em; border-bottom:1px solid var(--line);
}
h3 { font-size: 12.4pt; margin: 1.9em 0 .4em; letter-spacing:-.005em; }
h4 { font-size: 11pt; margin: 1.5em 0 .3em; color:var(--muted); }
p { margin: .55em 0; }
ul { margin: .4em 0 .8em; padding-left: 1.35em; }
li { margin: .34em 0; }
li > ul { margin: .3em 0 .2em; }
code {
  font-family: "Cascadia Mono", Consolas, "SF Mono", Menlo, monospace;
  font-size: .88em; background: var(--code-bg);
  padding: .1em .38em; border-radius: 4px; border: 1px solid #e6e9ed;
}
pre { background:#11161d; color:#e6edf3; padding: .9em 1.1em; border-radius: 8px; overflow-x:auto; }
pre code { background:none; border:none; color:inherit; padding:0; }
a { color: var(--accent); text-decoration: none; border-bottom: 1px solid rgba(59,91,219,.3); }
a:hover { border-bottom-color: var(--accent); }
strong { font-weight: 650; }
hr { border:0; border-top:1px solid var(--line); margin: 2.2em 0; }
blockquote {
  margin: 1em 0; padding: .75em 1.1em; background: var(--card);
  border-left: 3px solid var(--accent); border-radius: 0 6px 6px 0; color: #333a45;
}
blockquote p { margin: .3em 0; }
table { border-collapse: collapse; width:100%; margin:1em 0; font-size: 9.6pt; }
th, td { border:1px solid var(--line); padding: .42em .6em; text-align:left; vertical-align:top; }
th { background: var(--card); font-weight:650; }
td:first-child, th:first-child { white-space: nowrap; }
@page { size: A4; margin: 15mm 13mm; }
@media print {
  body { font-size: 10pt; padding: 0; }
  h2 { page-break-after: avoid; }
  h3, h4 { page-break-after: avoid; }
  li, blockquote { page-break-inside: avoid; }
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
    assert "<h1>" in h and "<h2>Agent skills (3)</h2>" in h, h[:200]
    assert "<strong>Nobody" in h, h[:400]                    # thread body captured
    assert '<a href="https://example.com/a">repo</a>' in h
    assert "<code>npm i -g foo</code>" in h
    assert "<li>" in h and "mattpocock/skills@tdd</strong>" in h
    assert "<em>Quiet Tuesday." in h

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
            doc_path = tmp / "digest.html"
            doc_path.write_text(
                wrap_document(args.title or struct["title"] or stem, md_to_html_body(md), DOC_CSS),
                encoding="utf-8",
            )
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