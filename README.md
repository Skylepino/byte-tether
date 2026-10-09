# Byte-Tether — Daily Interest Digest

A **self-contained daily digest automation** built on **Orca**, the agent
orchestrator. Once a day, a scheduled agent run
collects the things worth knowing in the AI/agent tooling ecosystem and writes them
to `output/YYYY-MM-DD.md` — each with a real source URL, who made it, and a concrete
note on what you'd actually do with it. It then renders a PDF and a set of social
cards **locally**, which you post by hand.

Everything is customizable: which agent runs it, when it runs, what topics it
covers, how many items per topic, and **how it sounds**.

It runs on Orca because Orca gives you the three things a daily job actually needs:
a scheduler that catches up if the machine was asleep, a fresh worktree per run so
nothing leaks into your working copy, and a choice of provider per job. The digest
itself is just markdown and config — if you already orchestrate something else, the
parts you'd replace are the three `tools/*.ps1` wrappers around `orca automations`.

---

## Set this up

### Ask your agent (recommended)

The repo is built so an agent can set it up without being told which files matter.
`AGENTS.md` states what's authoritative, `skills/daily-digest/SKILL.md` holds the
procedure, and `config/digest.json` holds every knob.

> Set up the Byte-Tether daily digest in this repo. Read `AGENTS.md` and
> `skills/daily-digest/SKILL.md` first. Don't change my categories, schedule or
> tone unless I ask.

Works with opencode, codex, claude, gemini, or anything else that reads files and
runs commands.

### Or do it yourself

```powershell
# 1. Everything needed for a run is already in this folder. Commit it — a
#    new_per_run automation checks out from git, so uncommitted = invisible.
git add -A; git commit -m "digest tooling"

# 2. Create the automation from config/digest.json.
#    Safe to re-run: it updates an existing automation for this repo rather
#    than making a second one that fires at the same hour every day.
powershell -File tools\install-automation.ps1

# 3. Fire one now
powershell -File tools\run-digest.ps1
```

Then re-read [`output/test/example.md`](output/test/example.md) — it's the reference
output, and it is what a real run should still resemble.

Requires Orca running, and an installed agent CLI (`opencode` by default).

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
| `digest.repoFacts.report` | Which repo signals to report (license, last commit, releases, contributing…) |
| `digest.repoFacts.how` | How to fetch each one, plus the API-call budget |
| `audience` | Who the "Use it for" lines are written for — stack, tools, skills dir |
| `style.tone` | Voice: `punchy`, `analyst`, `plain`, `social` |
| `style.avoid` | Banned phrases — the fingerprint of generated prose |
| `style.depthItems` | How many items get the full in-depth write-up |
| `style.closingLine` | How many "go look at this" nudges per category (scarce on purpose) |
| `assets.*` | PDF + social cards, rendered locally for **manual** posting |
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

### Change what gets reported about a repo

Stars alone measure popularity, not whether the thing is usable. `repoFacts.report`
lists the signals worth attaching to every GitHub item, and `repoFacts.how` says how
to fetch each:

```jsonc
"repoFacts": {
  "report": ["stars", "language", "license", "lastCommit", "releases", "install", "platform"],
  "how": { "license": "GET /repos/{owner}/{repo}/license or license.spdx_id. …" }
}
```

Three that change the answer rather than just decorating it:

- **No license** — you cannot legally use it in work. Reported, not hidden.
- **`pushed_at` over a year old** — abandoned, whatever the star count says.
- **Zero releases on a library** — pre-1.0. Pin your version or don't depend on it.

There is a real API budget here: unauthenticated, ~60 requests an hour and 10 search
calls a minute, against 60 items. The search result already carries stars, language,
`pushed_at`, `open_issues_count` and `license`, so spend the remaining calls on
`releases.atom` (free) and keep `CONTRIBUTING.md` checks for in-depth items. `how`
carries the full per-fact recipe.

Trim `report` down to `["stars", "language"]` for a quicker digest, or add your own
field with its recipe beside it.

### Change the tone

The voice is a **file**. Pick one by name, no prompt edits:

```jsonc
"style": { "tone": "punchy" }   // punchy | analyst | plain | social
```

| File | Shape |
|---|---|
| `styles/punchy.md` | Default. Newsletter with opinions: short sentences, real numbers, one idea per item. |
| `styles/analyst.md` | Dense and hedged, mechanism-first. Limitations stated on every item. |
| `styles/plain.md` | Descriptive only. No recommendations, no editorialising. |
| `styles/social.md` | Built to be lifted out of context — TL;DRs that work alone. |

Adding a tone is just a new file in `styles/`. Then point `style.tone` at it.

`style.avoid` is the companion: a banned-phrase list (`delve`, `seamless`, `leverage`,
`not just X but Y`, …). Anything on it in a draft is a defect, not a style choice.

Two more dials in the same block:

- `depthItems` — how many items per run get the full in-depth write-up. Not a ranking;
  the output is never presented as "top N".
- `closingLine.maxPerCategory` — how many explicit "go look at this" nudges to write.
  Default `1`. Scarcity is the whole point; a nudge on every item is a mark-up job.

### Assets and posting

**Nothing is ever published.** No dev.to, no API call, no key — by design. Each run
renders local files into `output/assets/` and a human posts them by hand.

```powershell
python tools\render_assets.py output\2026-10-09.md
```

| File | What it is |
|---|---|
| `2026-10-09.pdf` | The whole digest, styled, A4 |
| `2026-10-09-cover.png` | Cover card: mood line + thread, 1200×630 |
| `2026-10-09-<category>.png` | One card per category, 1200×630 |

Rendering is markdown → HTML → headless Edge/Chromium, found automatically. **Nothing to
install** — no pandoc, no wkhtmltopdf, no ImageMagick. `tools/render_assets.py` is
stdlib-only Python 3. Set `DIGEST_BROWSER` if you need to point it at a specific binary.

```powershell
python tools\render_assets.py --selftest   # check the parser before trusting a render
```

The PDF is laid out as an **article**, not a markdown dump: serif prose on a narrow
measure, a masthead with a numbered "In this issue" overview, pull-quotes, and
label-value grids. Five pieces of markdown are recognised and given article treatment,
which is what lets the renderer compose itself:

| Markup | Becomes |
|---|---|
| Leading all-**bold** line of a section | a pull-quote |
| `- **By:**` / `- **Plainly:**` / `- **TL;DR:**` | a label-value grid |
| `**Use it for:**` | an accent-ruled callout |
| A bare URL alone on a line | a small grey source reference |
| `![alt](path)` | an illustration, full measure |

Add `--illustrate` for one generated editorial illustration under the masthead:

```powershell
python tools\render_assets.py output\2026-10-09.md --illustrate   # needs OPENAI_API_KEY
```

Illustrations are **generated, not fetched** — that keeps a render offline and means
nothing in the PDF carries someone else's licence. Without the key the script warns and
renders without art. It's opt-in per run; `assets.illustrations` in the config records
the intent.

---

## How it works

```
config/digest.json      ← all the knobs
      ↓
AGENTS.md               ← repo instructions, loaded first by any agent
      ↓
styles/<tone>.md        ← the voice
      ↓
skills/daily-digest/    ← the procedure (SKILL.md)
      ↓
daily-digest/SPEC.md    ← output format template
      ↓
output/YYYY-MM-DD.md    ← the digest
output/assets/          ← PDF + social cards (local, for you to post)
ledger/INDEX.md         ← dedup ledger, newest first
```

The one rule that makes it useful: **never list an item already in `ledger/INDEX.md`
inside the dedup window.** A digest that repeats yesterday is worthless, so the
ledger is read *before* anything is selected.

```
Run N:   read ledger → build blocklist → verify against live sources → write digest → prepend ledger → render assets
```

### For agents

An agent reading this repo should only need these four files, in this order:

| File | Why |
|---|---|
| `AGENTS.md` | What's authoritative, and the hard rules. Read first. |
| `config/digest.json` | Categories, counts, sources, dedup window, tone, audience. |
| `skills/daily-digest/SKILL.md` | The step-by-step procedure. |
| `ledger/INDEX.md` | What is banned. Read *before* selecting anything. |

`config/digest.json` wins over `AGENTS.md` whenever they disagree, so a user who
edits their config never needs to also edit prose.

Two behaviours an agent must not "helpfully" break:

- **Never auto-publish.** No API call, no key, no posting anywhere. The agent renders
  local files and stops. This is the whole safety model.
- **Never commit from a dirty tree assumption.** `new_per_run` checks out from git,
  so an uncommitted `config/digest.json` means the run silently uses the old one.

### For humans

What you actually touch, in order of how often you'll touch it:

| When | Do this |
|---|---|
| Wanted a different topic | edit `categories[]` in `config/digest.json` |
| Wanted a different hour | edit `schedule.rrule`, re-run `install-automation.ps1` |
| Hated the voice | point `style.tone` at another file in `styles/` |
| Wanted fewer items | edit `digest.itemsPerCategory` |
| Stopped getting posts | check `orca automations list --json` for an orphan |
| Wanted to contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |

You never edit the automation prompt. It is four lines that tell the agent to read
`AGENTS.md` and the config — that's what makes customization a config edit instead of
a prompt edit that breaks the next time you change something else.

Contributors and forks are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). MIT
licensed, see [LICENSE](LICENSE).

### Why the ledger isn't in `output/`

`output/` is gitignored — those are artifacts, a file per day forever. But the
automation runs in a **fresh worktree per run**, checking out from git. A ledger
living in the ignored folder would be invisible to tomorrow's run: empty blocklist,
same items again. So it sits at `ledger/INDEX.md`, outside `output/`, committed every
run. `output/test/` is tracked for the same reason — it's the reference example you
check after changing the tone or the format.

---

## Layout

| Path | What it is |
|---|---|
| `config/digest.json` | Every knob. Edit this, not the prompt. |
| `AGENTS.md` | Repo instructions for any agent working here |
| `styles/` | Voice presets. Pick with `style.tone`. |
| `CONTRIBUTING.md` | How to contribute; also the prompt to hand your own agent |
| `skills/daily-digest/SKILL.md` | The digest procedure |
| `daily-digest/SPEC.md` | Output format template |
| `daily-digest/catchup-on-launch.ps1` | Login-hook catch-up |
| `tools/` | Helper scripts (below) |
| `ledger/INDEX.md` | Dedup ledger — **tracked** |
| `output/YYYY-MM-DD.md` | One file per run — **not tracked** |
| `output/assets/` | Generated PDF + cards — **not tracked** |
| `output/test/` | Reference example + checklist — **tracked** |

### Tools

| Script | What it does |
|---|---|
| `tools/install-automation.ps1` | Create the automation from config, write the id back |
| `tools/run-digest.ps1` | Fire a run now |
| `tools/banned-items.ps1` | Print the banned set for the dedup window |
| `tools/check-staleness.ps1` | Report digest age; fire if stale (`-Force` to always) |
| `tools/render_assets.py` | Digest markdown → PDF + social cards, locally |

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

**The digest repeated itself.** Check that `ledger/INDEX.md` is committed and still
exists at the path `digest.indexFile` names. If the ledger ever lands inside the
gitignored `output/`, every run starts with an empty blocklist.

**`git status` shows daily digests.** It shouldn't — `output/` is ignored on purpose.
Check `.gitignore` still has `/output/*` followed by `!/output/test/`.

**`orca automations list` reports the automation as an orphan.** It points at a
project id that no longer resolves — usually because the repo was re-added to Orca.
Re-create it: `tools\install-automation.ps1`.

**Categories come back short.** Working as intended. The rule is never pad. A short
honest category beats a padded one.

**The PDF or cards didn't render.** `tools/render_assets.py` needs a Chromium-family
browser. It looks for Edge/Chrome automatically; set `DIGEST_BROWSER` to point at one
explicitly. Without it the script writes HTML and warns rather than failing the digest.

**The writing reads like AI.** Check `style.avoid` — those phrases are the fingerprint.
Then check `style.tone` matches the voice file you expect, and read
`output/test/example.md` for what good looks like.

**A config change didn't take effect.** Only `agent.provider` and `schedule.*` need
`tools\install-automation.ps1` re-run — everything else is read fresh from
`config/digest.json` on every run, because the prompt just tells the agent to read it.
And check it got committed; an uncommitted config is invisible to the run.

**Two automations firing the same digest.** A duplicate from an earlier
`install-automation.ps1`. Check `orca automations list --json`, remove the one whose
`runContext.path` isn't this repo.