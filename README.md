# Byte-Tether — Daily Interest Digest

A **self-contained daily digest automation**. Once a day, a scheduled agent run
collects the things worth knowing in the AI/agent tooling ecosystem and writes them
to `output/YYYY-MM-DD.md` — each with a real source URL and a concrete note on what
you'd actually do with it.

Everything is customizable: which agent runs it, when it runs, what topics it
covers, how many items per topic, whether it publishes anywhere.

---

## Quick start

```powershell
# 1. Everything needed for a run is already in this folder. Commit it — a
#    new_per_run automation checks out from git, so uncommitted = invisible.
git add -A; git commit -m "digest tooling"

# 2. Create the automation from config/digest.json
powershell -File tools\install-automation.ps1

# 3. Fire one now
powershell -File tools\run-digest.ps1
```

---

## Customize it

**All customization lives in [`config/digest.json`](config/digest.json).** Edit it,
commit, done. The automation prompt never needs to change.

| Knob | What it does |
|---|---|
| `schedule.rrule` | When it runs — `FREQ=DAILY;BYHOUR=8;BYMINUTE=0`, weekly, weekdays, cron… |
| `schedule.timezone` | IANA tz, e.g. `Asia/Manila` |
| `schedule.catchupAfterHours` | How stale the last digest may get before the login hook fires |
| `agent.provider` | `opencode`, `codex`, `claude`, `gemini`, `grok`, `pi`, `omp` |
| `digest.itemsPerCategory` | How many items per category |
| `digest.dedupWindowDays` | How far back to check for repeats |
| `audience` | Who the "Use for" lines are written for — stack, tools, skills dir |
| `publishing.*` | dev.to drafts, cover image; each gated on an env var |
| `categories[]` | Add, remove, or retune topics: focus, sources, keyword rotation |

### Change the agent

```jsonc
"agent": { "provider": "opencode" }   // or codex, claude, gemini, grok, pi, omp
```

The model is chosen inside the agent, not here. Switch the provider, then pick the
model in that agent's own config.

### Change the schedule

```jsonc
"schedule": {
  "rrule": "FREQ=WEEKLY;BYDAY=MO,WE,FR;BYHOUR=9;BYMINUTE=0",
  "timezone": "Asia/Manila"
}
```

Then re-run `tools\install-automation.ps1`, or edit the live automation directly:

```powershell
orca automations edit <id> --trigger "FREQ=DAILY;BYHOUR=8;BYMINUTE=0" --json
```

### Change the topics

`categories` is a plain array. Drop entries to drop a category, add entries to add
one. Each carries its own `sources` and `keywords`, so a new category is
self-contained:

```jsonc
{
  "name": "Rust CLI ecosystem",
  "count": 6,
  "focus": "Terminal tools written in Rust that are actually fast.",
  "sources": ["https://api.github.com/search/repositories"],
  "queries": ["language:rust+topic:cli+created:>{date-60d}&sort=stars"],
  "note": "Report cargo install line and Windows support."
}
```

The `keywords` / `queries` lists are longer than any single run can exhaust. The
agent rotates through a different slice each run — that's what stops the source well
going dry before the dedup ledger even catches the repeat.

### Change the publishing

Both blocks are opt-in and gate on an environment variable. Absent key = skip
silently, never a failed digest.

```jsonc
"publishing": {
  "devto":       { "enabled": true, "envKey": "DEVTO_API_KEY", "published": false },
  "coverImage":  { "enabled": true, "envKey": "OPENAI_API_KEY", "width": 1000, "height": 420 }
}
```

`published: false` posts a **draft** with an edit URL. That's deliberate —
unreviewed generated output shouldn't go live under your name by itself.

---

## How it works

```
config/digest.json      ← all the knobs
      ↓
AGENTS.md               ← repo instructions, loaded first by any agent
      ↓
skills/daily-digest/    ← the procedure (SKILL.md)
      ↓
daily-digest/SPEC.md    ← output format template
      ↓
output/YYYY-MM-DD.md    ← the digest
output/INDEX.md         ← dedup ledger, newest first
```

The one rule that makes it useful: **never list an item already in `INDEX.md`
inside the dedup window.** A digest that repeats yesterday is worthless, so the
ledger is read *before* anything is selected.

```
Run N:   read INDEX.md → build blocklist → verify against live sources → write digest → prepend ledger
```

The automation runs in a **fresh worktree per run** (`new_per_run`), so nothing it
does leaks into your working copy. The agent reads and writes `output/`, commits,
and that commit is the deliverable.

---

## Layout

| Path | What it is |
|---|---|
| `config/digest.json` | Every knob. Edit this, not the prompt. |
| `AGENTS.md` | Repo instructions for any agent working here |
| `skills/daily-digest/SKILL.md` | The digest procedure |
| `daily-digest/SPEC.md` | Output format template |
| `daily-digest/catchup-on-launch.ps1` | Login-hook catch-up |
| `tools/` | Helper scripts (below) |
| `output/` | `INDEX.md` ledger + one file per run |

### Tools

| Script | What it does |
|---|---|
| `tools/install-automation.ps1` | Create the automation from config, write the id back |
| `tools/run-digest.ps1` | Fire a run now |
| `tools/banned-items.ps1` | Print the banned set for the dedup window |
| `tools/check-staleness.ps1` | Report digest age; fire if stale (`-Force` to always) |

---

## The login catch-up

The daily schedule is the floor, not the whole story. If the machine was asleep or
Orca was closed at the scheduled hour, the run is missed. A startup hook closes
that gap:

```powershell
Copy-Item daily-digest\catchup-on-launch.ps1 "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\"
```

It's a silent no-op when the last digest is fresher than
`schedule.catchupAfterHours`, so it's safe to run at every login.

Prefer the CLI version, which reads the threshold from config and supports
`--json` for other tooling:

```powershell
powershell -File tools\check-staleness.ps1
```

---

## Orca CLI reference

```bash
orca automations list --json                    # all automations
orca automations show <id> --json               # one
orca automations run <id> --json                # fire now
orca automations runs --id <id> --json          # history
orca automations edit <id> --time 08:00 --json  # reschedule
orca automations remove <id> --json             # delete
```

`automation.id` lives in `config/digest.json` so the scripts don't hardcode it.

---

## Troubleshooting

**Run completes but `output/` is empty.** The repo isn't committed. `new_per_run`
checks out from git, so uncommitted files are invisible to the run. `git status`
should be clean.

**`orca automations list` reports the automation as an orphan.** It points at a
project id that no longer resolves — usually because the repo was re-added to Orca.
Re-create it: `tools\install-automation.ps1`.

**Categories come back short.** Working as intended. The rule is never pad. A short
honest category beats a padded one.

**Nothing gets published to dev.to.** `DEVTO_API_KEY` isn't in the environment the
automation runs under. Absent key means silent skip by design.