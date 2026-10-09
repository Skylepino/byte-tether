# AGENTS.md

Instructions for any agent working in this repo — opencode, codex, claude, or gemini.

## What this repo is

A customizable daily-digest automation. One scheduled agent run per day writes a
markdown digest of things worth knowing, backed by a dedup ledger so consecutive
days never repeat each other. It also renders a PDF and a set of social cards
**locally**, which you then post by hand.

## Read these first, in this order

1. `config/digest.local.json`, falling back to `config/digest.json` — every knob:
   schedule, agent, topics, counts, dedup window, **tone**
2. `skills/daily-digest/SKILL.md` — the procedure
3. `output/test/example.md` — what good output looks like right now
4. `ledger/INDEX.md` — the dedup ledger, read before picking anything

`config/digest.local.json` is gitignored and holds one person's setup;
`config/digest.example.json` is a committed worked example. Resolve exactly the
way `tools/lib.ps1` does — local first, template second.

Nothing else is authoritative. If this file and the config disagree, the config wins.

## The one rule that matters

**Never list an item already in `ledger/INDEX.md` inside the dedup window.**
A digest that repeats yesterday is worthless.

```powershell
powershell -File tools\banned-items.ps1          # prints the banned set
```

Use that output as the blocklist while you select. Widen the keyword families each
run so you do not re-draw the same well even before the blocklist catches it.

## Hard rules

1. **Deduplicate against history.** See above. This is the rule.
2. **Counts come from `config.digest.itemsPerCategory`.** If a category is genuinely
   dry, ship fewer and say so in one line. Never pad with filler.
3. **Tone comes from `config.style.tone`.** Load `styles/<tone>.md` before writing and
   check the draft against `style.avoid`. That list is the fingerprint of generated
   prose; anything on it is a bug.
4. **Never rank.** Tier A items are explained, not best. No "top N", no ordering
   implied by position.
5. **Every item needs an author and a "Use it for" line** written for `config.audience`.
   A restatement of the README is useless — say what you would actually do with it.
6. **Verify before you list.** Fetch or query the source; never recall from training.
   Real URL required. If the source is unreachable, drop the item.
7. **Date-stamp from the environment**, not from an assumed date.
8. **Write two things**: `output/YYYY-MM-DD.md`, then prepend rows to `ledger/INDEX.md`.
9. **Never commit secrets.** Read keys from the environment only.
10. **Never publish anything.** No dev.to, no API call, no key. Render local files with
    `tools/render_assets.py`; posting is done by a human.

## Why the ledger is not in `output/`

`output/` is gitignored — it holds a file per day plus generated PDFs and cards, which
are artifacts, not source. But this automation checks out a **fresh worktree from git**
on every run. If the ledger were inside the ignored folder it would be invisible to
tomorrow's run, the blocklist would be empty, and the digest would repeat itself.

So the ledger lives at `ledger/INDEX.md`, outside `output/`, and is committed every run.

## Layout

| Path | What it is |
|---|---|
| `config/digest.json` | The knobs. The template; edit this to change the default. |
| `config/digest.local.json` | Your working config — **gitignored**, wins if present |
| `config/digest.example.json` | A real tuned config, as a worked example |
| `styles/<tone>.md` | Voice. Pick by changing `style.tone`. |
| `skills/daily-digest/SKILL.md` | The procedure you follow |
| `daily-digest/SPEC.md` | Output format spec, long form |
| `daily-digest/catchup-on-launch.ps1` | Windows login catch-up |
| `tools/` | banned set, staleness, render assets, manual trigger |
| `ledger/INDEX.md` | Dedup ledger, newest first — **tracked** |
| `output/YYYY-MM-DD.md` | One file per run — **not tracked** |
| `output/assets/` | Generated PDF + cards — **not tracked** |
| `output/test/` | QA fixture and reference example — **tracked** |
| `CONTRIBUTING.md` | Contribution standards — **tracked** |
| `LICENSE` | MIT — **tracked** |

`output/test/` is committed on purpose. After any change to `config.style`, `styles/` or
the item format, read `output/test/example.md` and ask whether a real run would still
look like that. See `output/test/README.md` for the checklist, and re-render the
fixture with `python tools/render_assets.py output/test/example.md --outdir output/test`
if the format actually changed.

## Repo hygiene

The repo must stay committed. `new_per_run` automations check out from git, so an
uncommitted file is invisible to the scheduled run — this repo shipped with an empty
initial commit and run 1 found no spec at all. Commit new tooling before relying on it.