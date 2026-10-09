# Daily Interest Digest

An automated once-a-day digest of the AI/agent tooling ecosystem: 10 items across
6 categories, each with a concrete "what I'd use this for" note and a real source URL.

## What's here

| File | Purpose |
|---|---|
| `SPEC.md` | The full spec — categories, sources, dedup rules, output format |
| `catchup-on-launch.ps1` | Startup-folder script that fires the digest if it's >20h stale |

Digests land in `../output/YYYY-MM-DD.md`, with `../output/INDEX.md` as the
dedup ledger that keeps consecutive days from repeating each other.

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

## Optional: auto-post to dev.to

Set `DEVTO_API_KEY` in the environment and the digest will also render a social
card and POST a **draft** to dev.to. Without the key it skips silently.
Drafts are deliberate — proofread before anything publishes under your name.

---

*Project-level docs (customization, layout, tool scripts) live in the repository
root `README.md`. This folder is the spec the digest agent follows.*