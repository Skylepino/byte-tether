# Daily Interest Digest — Spec

A once-a-day discovery digest: what showed up in the AI/agent tooling ecosystem
that I haven't seen before, plus what I could actually do with each thing.

Runs via an Orca automation. Output lands in `output/YYYY-MM-DD.md`.

---

## Hard rules

1. **Deduplicate against history.** Before writing, read `ledger/INDEX.md`. Anything
   already listed in the last **90 days** is banned. This is the single most important
   rule — a digest that repeats yesterday is worthless.
2. **10 items per category, 6 categories = 60 items.** If a category is genuinely dry,
   ship fewer and say so in a one-line note. Never pad with filler.
3. **Every item needs an author and a "Use it for" line** — concrete and specific to
   *my* setup (Laravel/Inertia + React + Postgres, Orca, opencode/codex/agy,
   agent skills in `~/.agents/skills`, Windows). Generic restatements of the README
   are useless.
4. **Verify before you list.** Each item must be fetched or queried, not recalled from
   training. Include a real URL. If you can't reach the source, drop the item.
5. **Date-stamp everything.** Use the real current date from the environment, not an
   assumed one.
6. **Never rank.** Two tiers exist for readability, not importance. Nothing is a
   "top N", and position must never imply a ranking.

---

## Categories and sources

### 1. Agent skills (10)
Source: `npx --yes skills find "<keyword>"`, and `https://skills.sh`.
Rotate the keyword slice each run — `agent-skills`, `claude-code`, `mcp`, `test`,
`refactor`, `security`, `laravel`, `react`, `observability`, `prompt`,
`skill-creator`. (`laravel` currently returns **no results**; note it if it still does.)
Install hint: `npx --yes skills add owner/repo@skill --global --agent universal -y`.

### 2. GitHub projects (10)
Source: GitHub Search API.
`https://api.github.com/search/repositories?q=created:>{date-30d}+topic:ai-agent&sort=stars`
Vary the topic per run (`ai-agent`, `llm`, `mcp-server`, `agent-framework`,
`developer-tools`, `coding-agent`). Prefer repos created in the last ~60 days showing
early traction.

Report the signals in `config.digest.repoFacts.report` — stars, language, license,
last-commit recency, open issues, release count, install command, platform. Stars
alone are popularity, not usability:

- **No license** means you cannot legally use it in work. Report that; don't drop it.
- **`pushed_at`** older than a year means abandoned regardless of star count.
- **`archived: true`** means read-only. Say so.
- A library with zero releases is pre-1.0 — pin your version or don't depend on it.

> Do **not** URL-encode the `q` parameter. Encoding `:` as `%3A` makes GitHub's search
> parser return zero results with no error. Encode nothing; let the client handle spaces.
> For release checks, use `https://github.com/<owner>/<repo>/releases.atom` — it costs
> no REST quota. The search result already returns stars, language, `pushed_at`,
> `open_issues_count` and `license`, so you rarely need extra calls.

### 3. CLI tools (10)
Source: GitHub search + awesome-lists. Terminal tools that improve an agent's loop:
file watchers, AST/codegen CLIs, git tooling, terminal AI clients, tUI frameworks.
Report the install method (brew/scoop/npm/cargo/go/pip/uv) **and whether it is
Windows-safe**. "Linux/macOS only" is information worth stating, not a reason to drop it.

### 4. MCP servers (10)
Source: `https://github.com/modelcontextprotocol/registry`, awesome-mcp-servers.
Prefer servers that add real capability to Orca/opencode/codex. Report the transport
(stdio/http) and one real tool call, read from the project's README.

> The registry's newest entries skew heavily toward ad-serving and x402 payment stubs.
> A registry listing proves existence, not quality. Read the README before recommending.

### 5. Agent frameworks & orchestration (10)
Source: GitHub search + engineering blogs. Harnesses, multi-agent orchestration, task
DAGs, handoff protocols, eval harnesses, agent memory, context engineering, MCP
gateways, sandboxes. Read these closer and write richer notes.

### 6. Papers & writing worth reading (10)
Source: arXiv (cs.AI, cs.SE), `dev.to/feed/tag/ai`, HN RSS, Simon Willison's Atom feed.
Skip SEO filler and "10 best X" listicles — `daily.dev` is currently 100% listicles and
can be dropped without checking further. Want: real technique, real benchmarks,
post-mortems, architecture write-ups, eval methodology. Report reading time (an estimate
is fine if you label it) and one sentence on why it's worth the time.

---

## Output format

Write **three** things per run.

### `output/YYYY-MM-DD.md`

Two tiers per category. Tier A is *explained*, not *better*.

````markdown
# Daily Interest Digest — YYYY-MM-DD

_<one-line mood summary — this is the cover card headline, so it must fit on one line>_

## Agent skills

### owner/repo@skill

**<The hook. One line. Write it before the rest.>**

- **By:** [owner](https://github.com/owner) · 823K installs · `npx skills add owner/repo@skill`
- **Plainly:** <what it does, in plain words, no marketing>
- **TL;DR:** <stands entirely alone; a claim or a number, not a description>

**Use it for:** <a verb. an action. written for config.audience.>

<url>

- **owner/repo@skill** — <one line>. 12K installs.
  **Use it for:** <concrete action.> [link](<url>)

> <closing line — at most ONE per category, never on a Tier A item>

## Thread of the day

**<The pattern, in one line.>**

> **<The one sentence worth setting large, The Batch style. Optional.>**

- <proof from one category>
- <proof from another>

---
_generated by Orca automation · sources actually used_
```

**How the PDF reads.** The renderer treats this as an article, not a markdown dump —
serif prose on a narrow measure, a masthead, and an "In this issue" overview. Five
pieces of markup get special treatment, and using them is what makes the PDF compose
itself:

| Markup | Becomes |
|---|---|
| Leading all-**bold** line of a section | a pull-quote |
| `- **By:**` / `- **Plainly:**` / `- **TL;DR:**` | a label-value grid |
| `**Use it for:**` | an accent-ruled callout |
| A bare URL alone on a line | a small source reference |
| `![alt](path)` | an illustration |`

### `ledger/INDEX.md`

Prepend one row per item, newest first. This is the dedup ledger:

```markdown
| Date | Category | Item | URL |
|------|----------|------|-----|
| 2026-10-09 | skills | owner/repo@skill | https://... |
```

Read this **first** on every run. It is what makes the digest non-repetitive. It lives
outside `output/` because `output/` is gitignored and the automation checks out a fresh
worktree per run — an uncommitted ledger is an empty blocklist.

### `output/assets/` — local, for manual posting

`tools/render_assets.py` renders a PDF of the digest plus a cover card and one card per
category (1200×630 PNG). **Never posted anywhere.** You take the files and post them.

---

## Tone

The voice is a file: `styles/<tone>.md`, selected by `config.style.tone`.

| Tone | Shape |
|---|---|
| `punchy` | Default. Newsletter with opinions. Short sentences, real numbers, one idea per item. |
| `analyst` | Dense, hedged, mechanism-first. Limitations stated on every item. |
| `plain` | Descriptive, no recommendations, no editorialising. |
| `social` | Written to be lifted out of context. TL;DRs must work alone. |

`config.style.avoid` is a banned-phrase list. Those words are the fingerprint of
generated prose; hitting one is a defect, not a style choice. Most common offenders:
*delve, landscape, game-changer, seamless, robust, leverage, unlock, elevate,
not just X but Y,* and the "it's worth noting" family.

**The closing line** is an explicit nudge to go look at something. Scarcity is the
whole point — `style.closingLine.maxPerCategory` defaults to 1 per category. A nudge on
every item turns the digest into a mark-up job and it gets skipped.

---

## Media (manual, always)

There is no publishing step. Not dev.to, not an API, not a key — **the automation never
posts anything**. It renders local files and a human copies them wherever they want.

Rendered per run into `output/assets/`:

| File | What it is |
|---|---|
| `YYYY-MM-DD.pdf` | The whole digest, styled, A4 |
| `YYYY-MM-DD-cover.png` | Cover card: mood line + thread |
| `YYYY-MM-DD-<category>.png` | One card per category |

`python tools/render_assets.py --selftest` checks the parser before you trust a render.

---

## Suggested sources to add

Sites with real signal, no engagement bait:

- **Hacker News** (`news.ycombinator.com/rss`) — via Algolia API, better filtering
- **Lobsters** (`lobste.rs/rss`) — smaller, higher-signal dev crowd
- **Papers with Code** — benchmark results, not just claims
- **Anthropic / OpenAI engineering blogs** — RSS, first-party technique
- **Awesome lists** (`sindresorhus/awesome`, `awesome-mcp-servers`) — discovery, not reading

---

## How this runs

**Orca automation**, daily at 18:00 Asia/Manila, provider `opencode`, repo `Byte-Tether`.

```bash
orca automations list --json
orca automations runs --id <id> --json
orca automations run <id> --json      # trigger manually
orca automations edit <id> --time 08:00 --json
```

**Catch-up on launch.** The 18:00 schedule is the floor, not the whole story.
If Orca was closed at 18:00 and the last digest is >20h old, run it immediately.
`tools/check-staleness.ps1` reads the threshold from config and is a silent no-op when
fresh, so it is safe to wire into a startup hook.