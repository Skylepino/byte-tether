# AGENTS.md

Instructions for any agent working in this repo — opencode, codex, claude, or gemini.

## What this repo is

A customizable daily-digest automation. One scheduled agent run per day writes a
markdown digest of things worth knowing, backed by a dedup ledger so consecutive
days never repeat each other.

## Read these first, in this order

1. `config/digest.json` — every knob: schedule, agent, topics, counts, dedup window
2. `skills/daily-digest/SKILL.md` — the procedure
3. `output/INDEX.md` — the dedup ledger, read before picking anything

Nothing else is authoritative. If this file and `config/digest.json` disagree,
`config/digest.json` wins.

## The one rule that matters

**Never list an item already in `output/INDEX.md` inside the dedup window.**
A digest that repeats yesterday is worthless.

```bash
powershell -File tools/banned-items.ps1          # prints the banned set
```

Use that output as the blocklist while you select. Widen the keyword families each
run so you do not re-draw the same well even before the blocklist catches it.

## Hard rules

1. **Deduplicate against history.** See above. This is the rule.
2. **Counts come from `config.digest.itemsPerCategory`.** If a category is genuinely
   dry, ship fewer and say so in one line. Never pad with filler.
3. **Every item needs a "Use for" line** written for `config.audience`. A
   restatement of the README is useless — say what you would actually do with it.
4. **Verify before you list.** Fetch or query the source; never recall from
   training. Real URL required. If the source is unreachable, drop the item.
5. **Date-stamp from the environment**, not from an assumed date.
6. **Write two files**: `output/YYYY-MM-DD.md`, then prepend rows to
   `output/INDEX.md`.
7. **Never commit secrets.** Read keys from the environment only.
8. **Media never fails the digest.** If the dev.to or image key is absent, skip it
   silently.

## Layout

| Path | What it is |
|---|---|
| `config/digest.json` | The knobs. Edit this, not the prompt. |
| `skills/daily-digest/SKILL.md` | The procedure you follow |
| `daily-digest/SPEC.md` | Output format template |
| `daily-digest/catchup-on-launch.ps1` | Windows login catch-up |
| `tools/` | Helpers — banned set, staleness check, manual trigger |
| `output/INDEX.md` | Dedup ledger, newest first |
| `output/YYYY-MM-DD.md` | One file per run |

## Repo hygiene

The repo must stay committed. `new_per_run` automations check out from git, so an
uncommitted file is invisible to the scheduled run — this repo shipped with an empty
initial commit and run 1 found no spec at all. Commit new tooling before relying on it.