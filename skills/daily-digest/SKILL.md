---
name: daily-digest
description: Generate the daily digest — pick fresh items across every category in config/digest.json, verify each one against a live source, write output/YYYY-MM-DD.md, prepend ledger/INDEX.md, and render local PDF + social cards for manual posting. Use when asked to run/generate/refresh the digest, or when invoked by the scheduled automation.
---

# Daily digest run

Follow this exactly. The whole point is that yesterday's digest and today's digest
never overlap.

## Step 0 — read the config, don't assume

```bash
cat config/digest.json
```

Everything below is driven by that file: how many items, which categories, which
sources, which keyword families, how far back the dedup window reaches, **and what
tone the writing is in**. If it disagrees with anything in this skill or in `AGENTS.md`,
the config wins.

## Step 1 — build the blocklist FIRST

```powershell
powershell -File tools/banned-items.ps1
```

This prints every item inside the dedup window, read from the ledger at
`digest.indexFile` (`ledger/INDEX.md`). Do not select anything until you have read the
whole list. Selecting first and checking after is how digests start repeating themselves.

Also read `ledger/INDEX.md` directly — the script gives you URLs and names, but the
ledger's structure is what you append to later.

## Step 2 — widen the well

Every category carries a `keywords` / `queries` list longer than one run can exhaust.
Pick a *different slice* each run rather than always drawing the same ten results.
Rotating the slice is what stops the source well going dry before the blocklist catches it.

## Step 3 — verify every candidate

For each candidate, actually fetch or query the source. No recall from training — the
training cutoff is behind you and this is a *discovery* tool. A recall-based item is a bug.

- **GitHub items:** hit the Search API or the repo page. Record language, star count,
  whether releases exist.
- **Skills:** `npx --yes skills find "<keyword>"` or skills.sh. Record install counts.
- **MCP:** the registry or an awesome list. Record transport and one real tool call.
- **Writing:** the actual feed entry. Record reading time if the source states it.

If a source will not load, drop the item. Do not substitute a remembered version of it.

Two things that will save you time, both learned the hard way:

- `https://github.com/<owner>/<repo>/releases.atom` tells you whether a repo ships
  releases without spending a single REST API request. The unauthenticated API allows
  roughly 10 search calls a minute — the atom feed doesn't count.
- The MCP registry's newest entries are mostly ad servers and x402 payment stubs. Read
  the project's own README for transport and tool names instead of trusting the listing.

### The repo facts

`digest.repoFacts.report` lists what to report on any GitHub item, and `repoFacts.how`
says how to fetch each one. Stars alone measure popularity, not usability. Two that
change the answer:

- **No license is a finding.** Without one you cannot legally use it in work. Say so
  plainly rather than dropping the item.
- **`pushed_at` beats the star count.** A 40k-star repo untouched for two years is a
  corpse. Under 30 days is alive.

Budget matters: the search result already carries stars, language, `pushed_at`,
`open_issues_count` and `license`. Spend extra calls on `releases.atom` (free) and
save `CONTRIBUTING.md` / good-first-issue checks for in-depth items, where the detail
earns its cost. A 60-item run cannot afford one call per repo per fact.

## Step 4 — load the tone, then write

```bash
cat styles/$(jq -r .style.tone config/digest.json).md
```

The voice is a file. Read it before you write a single line. The default is `punchy`.

Then check every draft against `style.avoid` — the list of banned phrases, which is the
fingerprint of generated prose. Anything on it is a failure, not a style choice.

## Step 5 — write the digest

Two tiers per category. **Neither is a ranking** — nothing here is "best", and the output
must not imply otherwise. Tier A items are simply the ones that needed more explaining.

```markdown
# Daily Interest Digest — YYYY-MM-DD

_<one-line mood summary — this is the cover card headline, so write it to fit one>_

## <Category>

### <in-depth item>

**<The hook. One line. This becomes the card headline, so write it first.>**

- **By:** [owner](https://github.com/owner) · 823★ · TypeScript · MIT · pushed 4d · 10 releases · `npm i -g thing` · Windows-native
- **Plainly:** <what it actually does, no marketing>
- **TL;DR:** <stands alone. A claim or a number, never a description.>

**Use it for:** <a verb, an action, written for config.audience>

<url>

- **owner/repo** — <one line.> `<install command>`. 256★, Go.
  **Use it for:** <concrete action.> [repo](<url>)

> <the closing line — at most one per category, never on a Tier A item>

## Thread of the day

**<The pattern, in one line.>**

- <proof from one category>
- <proof from another>

---
_generated by Orca automation · sources actually used_
```

Rules that the format depends on:

- **Author is required on Tier A.** Name the person or org and link them. Add "known
  for" only when it tells you something.
- **Tier A carries the repo facts** from `digest.repoFacts.report` — at minimum stars,
  language, license, last-commit recency, release count, install command and platform.
  Compact items get stars + language + install, nothing more.
- **Missing license or an archive flag is stated, not omitted.** Both change whether
  the item is usable at all.
- **TL;DR must survive being read alone.** No "this", no "it", no back-reference to the item.
- **"Use it for" starts with a verb.** It is an action, not a restatement of the README.
- **The closing line is scarce.** `style.closingLine.maxPerCategory`, default 1. A nudge
  on every item reads as a mark-up job and gets skipped.
- **Platform is stated, not implied.** This machine is Windows; "Linux/macOS only" is
  information, not a flaw in the item.

If a category is genuinely dry, ship fewer items and say so in one line. Never pad.

`daily-digest/SPEC.md` holds the longer version of this template.

## Step 6 — update the ledger

Prepend one row per item to `digest.indexFile` (`ledger/INDEX.md`), newest first:

```markdown
| Date | Category | Item | URL |
|------|----------|------|-----|
| 2026-10-09 | cli | owner/repo | https://... |
```

The date must be the real current date from the environment. Newest rows go **above**
older ones.

The ledger lives outside `output/` on purpose: `output/` is gitignored, and this
automation checks out a fresh worktree per run. A ledger that isn't committed means an
empty blocklist tomorrow.

## Step 7 — render local assets

```powershell
python tools\render_assets.py output\YYYY-MM-DD.md
```

Writes `output/assets/`: one PDF of the whole digest, a cover card, and a card per
category at 1200×630. Renders through a headless Edge/Chromium already on the machine.

The PDF is laid out as an **article**, not a markdown dump: serif prose on a narrow
measure, a masthead with an "In this issue" overview, pull-quotes, and label-value
grids. Five pieces of markdown are recognised and given article treatment — use them
and the PDF composes itself:

| In the markdown | Renders as |
|---|---|
| The leading all-**bold** line of a section | a pull-quote |
| `- **By:**` / `- **Plainly:**` / `- **TL;DR:**` | one label-value grid |
| `**Use it for:**` | an accent-ruled callout |
| A bare URL alone on a line | a small grey source reference |
| `![alt](path)` | an illustration, full measure |

Add `--illustrate` to generate one editorial illustration for the masthead. It needs
`OPENAI_API_KEY`; without it the script warns and renders without art.

**This step never publishes anything.** No dev.to, no API, no key, no network. The files
land on disk and a human copies whatever they want onto wherever they post. If the
browser is missing the script writes HTML and warns — it never fails the digest.

Run `python tools\render_assets.py --selftest` after editing the renderer.

## Step 8 — commit

```bash
git add -A && git commit -m "digest YYYY-MM-DD"
```

`output/` is gitignored on purpose; the run's markdown, PDF and cards stay local. What
gets committed is `ledger/INDEX.md` (the dedup state) and any tooling or config changes.
Never commit a key.

## Anti-patterns

- Selecting first, checking the ledger after.
- Listing something because you remember it rather than because you fetched it.
- Padding a dry category to hit a number.
- A "Use it for" line that restates the README.
- Labelling Tier A as "top picks" or numbering it as a ranking. It isn't one.
- Reaching for a phrase on `style.avoid`. That's the tell that reads as machine-written.
- Trying to publish. Posting is manual, always.
- Committing a secret, or writing a key into any file in this repo.
- Guessing today's date instead of reading it from the environment.