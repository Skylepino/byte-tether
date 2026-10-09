# Contributing

Thanks for looking. The bar here is deliberately low, and the rule is that **the
digest has to stay true to itself**.

## The one rule

The whole product is *"things I haven't seen before, with a real link and a reason
I'd use it."* A change that makes the digest easier to write but less trustworthy
is a regression, even if it's a nicer codebase.

Concretely, that means: **never weaken verification, the dedup ledger, or the
no-auto-publish stance.** Those three are the tool. Everything else is negotiable.

## Ask your agent

Most people will never read this file — they'll paste a prompt into opencode,
codex or claude instead. That is the intended path, and a well-behaved agent
following `AGENTS.md` will do the right thing on its own.

Ask for something like:

> Set up the Byte-Tether daily digest in this repo. Read `AGENTS.md` and
> `skills/daily-digest/SKILL.md` first. Don't change my categories, schedule or
> tone unless I ask.

The repo is set up so an agent can do this without being told which files matter:
`AGENTS.md` says what is authoritative, and your `config/digest.local.json` holds
every knob.

To fork it, copy the example config first — that's your working copy, and it stays
out of git:

```powershell
copy config\digest.example.json config\digest.local.json
```

## What a good PR looks like

| Change | Ask first? |
|---|---|
| New category, source or keyword in your **local** config | No — that's customization, the point |
| A new category in the committed template `config/digest.json` | No |
| New tone in `styles/` | No |
| A fix to a script in `tools/` | No |
| A new dependency | **Yes** — `tools/render_assets.py` is stdlib-only on purpose |
| Changing the output format | **Yes** — open a discussion first |
| Relaxing a hard rule in `AGENTS.md` or `SKILL.md` | **Yes** |
| Adding a third config file | **Yes** — two is a workflow, three is a fork problem |

**Never commit `config/digest.local.json`.** It's gitignored for a reason: it holds
your stack, your machine and your automation id. If you change the committed template,
make the change in both and keep the example realistic.

**If you change the format, the tone, or the config, regenerate the QA fixture:**

```powershell
python tools\render_assets.py --selftest
python tools\render_assets.py output\test\example.md --outdir output\test
git add output\test
```

`output/test/` is the reference output a real run gets compared against. If you
change the format and don't re-render it, the fixture silently stops being a
reference — and the next person can't tell what "correct" looks like.

## Style

Match what's already there. This is a small repo with no build step and no
transpiler; the only hard requirements are:

- **PowerShell** tools stay cross-platform-friendly (they already run on this
  machine, which is Windows 11 — don't introduce anything that assumes `jq`,
  `bash`, or POSIX paths).
- **Python** stays stdlib-only. Python 3, no `pip install`.
- Comment the *why*, not the *what*. One line is usually enough.

Don't reformat files you aren't otherwise changing.

## Commit messages

Short and factual, lowercase is fine:

```
add graphite category
fix duplicate automation on re-install
tighten verify step in SKILL.md
```

## Running it before you push

```powershell
powershell -File tools\banned-items.ps1          # does the ledger reader still work?
powershell -File tools\check-staleness.ps1 -Json # does the config still parse?
python tools\render_assets.py --selftest         # did you break the parser?
```

No test suite exists. These three are the closest thing, and they catch the
mistakes that actually happen here: a bad JSON path, a renamed script, an edited
regex in the renderer.

## Reporting a digest bug

If a run produced something wrong — a fabricated item, a broken link, a repeat of
yesterday's — the useful report is the **run id** and which category:

```powershell
orca automations runs --id <id> --json
```

The worktree path in the run record has the full transcript. That's where the
"where did this item come from" question gets answered.

## Security

No secrets, ever, in any file. API keys are read from the environment at run time
and nothing writes them to disk. If you add anything that touches a credential,
keep it that way.

---

MIT licensed. See [LICENSE](LICENSE).