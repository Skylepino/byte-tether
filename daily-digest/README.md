# Daily Interest Digest

An automated once-a-day digest of the AI/agent tooling ecosystem: 10 items across
6 categories, each with a concrete "what I'd use this for" note and a real source URL.

## What's here

| File | Purpose |
|---|---|
| `SPEC.md` | The full spec — categories, sources, dedup rules, output format |
| `catchup-on-launch.ps1` | Startup-folder script that fires the digest if it's >20h stale |

Digests land in `../output/YYYY-MM-DD.md` (gitignored), with `../ledger/INDEX.md`
as the dedup ledger that keeps consecutive days from repeating each other. The
ledger sits outside `output/` on purpose: the automation checks out a fresh
worktree per run, so anything inside the ignored folder would be invisible tomorrow.

`../output/test/example.md` is the reference output — read it after changing the
tone or the format.

## Categories

1. Agent skills (from skills.sh)
2. GitHub projects (new + trending in the agent ecosystem)
3. CLI tools
4. MCP servers
5. Agent frameworks & orchestration
6. Papers & writing worth reading

## Running it

Scheduled daily at **18:00 Asia/Manila** via an Orca automation.

```bash
orca automations list --json              # find the automation
orca automations run <id> --json          # generate now
orca automations runs --id <id> --json    # run history
orca automations edit <id> --time 08:00 --json
```

If Orca was closed at 18:00, the next login triggers a catch-up run.

## Assets: rendered locally, posted by hand

**Nothing is ever published automatically.** No dev.to, no API call, no key.

Each run renders into `../output/assets/`: a PDF of the digest, a cover card, and one
card per category (1200×630 PNG). Copy whichever you want onto wherever you post.

```powershell
python ..\tools\render_assets.py output\2026-10-09.md
```

Rendering uses a headless Edge/Chromium already on the machine — nothing to install.
`../output/test/example.pdf` and `../output/test/example-*.png` show what it produces.

---

*Project-level docs (customization, layout, tool scripts) live in the repository
root `README.md`. This folder is the spec the digest agent follows.*