# Daily Interest Digest — 2026-10-09 (FORMAT EXAMPLE)

_This is the reference output, not a new run. Real items from the 2026-10-09 run,
trimmed to three categories so the shape is easy to judge._

_Quiet Tuesday. Almost everything worth installing was about the same failure._

<!--
  WHAT THIS FILE IS
  The fixture the automation's output is judged against. Re-read it after changing
  config.style, config.digest or styles/*.md, and ask: does a real run still look
  like this?

  It shows the four things that matter:
    1. Two-tier items   - a few in depth, the rest compact. Never labelled as a ranking.
    2. Punchy tone     - see styles/punchy.md for the rules behind the voice here.
    3. A closing line  - at most one per category, and not on every item.
    4. Repo facts      - the in-depth "By:" line carries license, open issues, push
                         recency and release count per config.digest.repoFacts.report.
                         Stars alone would not say whether any of these are usable.

  Deliberately NOT shown: the sources footer, and the full 6 categories.
-->

## CLI tools

### fauxnix

**Your agents finally get a real shell on Windows.**

- **By:** [20000419](https://github.com/20000419) · 823★ · TypeScript · MIT · 13 open · pushed 4d ago · 10 releases · `npm i -g fauxnix-cli` · Windows-native
- **Plainly:** you type `ls -la src | head -3`, it runs the PowerShell equivalent, and
  it prints GNU-shaped columns and bash-style errors. No VM, no WSL.
- **TL;DR:** the WSL prompt is now optional.

**Use it for:** make it the default shell for every agent in this repo so `grep`,
`find` and `sed` behave the way the model was trained on.

[github.com/20000419/fauxnix](https://github.com/20000419/fauxnix)

- **yutat23/lsoff** — lsof for listening ports, and the only one here with a first-class
  Windows install. `winget install yutat23.lsoff`. 256★, Go.
  **Use it for:** killing the twenty minutes lost to "address already in use" when a
  Vite dev server or a stray Postgres won't start. [repo](https://github.com/yutat23/lsoff)

- **p10node/k10s** — Kubernetes TUI you can click: search, logs, exec, port-forward.
  `go install github.com/p10node/k10s@latest`. 252★, Go, 8 releases.
  **Use it for:** letting an agent read pod state instead of guessing at it.
  [repo](https://github.com/p10node/k10s)

- **Gheat1/tuistore** — TUI app store that resolves the install method for you, so you
  stop choosing between cargo/brew/pacman/uv by guesswork. `uv tool install tuistore`.
  427★, Python. **Windows-safe.**
  **Use it for:** installing the other nine tools here without hand-editing a manifest.
  [repo](https://github.com/Gheat1/tuistore)

- **simonw/ttok** — counts and truncates text by token. 1.0 landed today and it now
  defaults to the GPT-5/6 tokenizer instead of the GPT-4 one. 401★, Python.
  **Use it for:** gating anything that rewrites a prompt on real token boundaries.
  [repo](https://github.com/simonw/ttok)

> Worth fifteen minutes if you still keep WSL open purely to get `grep` to behave.

## MCP servers

### 2akouwu/reverify

**The model proposes. A deterministic tool decides.**

- **By:** [2akouwu](https://github.com/2akouwu) · 1.3k★ · Python · MIT · 12 open · pushed 8d ago · 10 releases · `pip install reverify` · Windows-native
- **Plainly:** it checks every claim against ground truth with evidence attached, so a
  statement can't stand on the model's authority alone. MCP server *and* CLI.
- **TL;DR:** "the test passes" becomes a fact about the code, not an assertion about itself.
- **Tools:** `re_verify_claim`, `prove_equiv`, `behavior_equiv`, `bytes_at`, `reachable_from_entry`.

**Use it for:** wiring it beside your Laravel/PHPUnit loop so a passing run is
independently checkable rather than self-reported.

[github.com/2akouwu/reverify](https://github.com/2akouwu/reverify)

- **00200200/usagetrim** — folds verbose tool output; CLI and MCP. Its authored fixtures
  cut docker 18,360 → 107 tokens, cargo 3,795 → 185, pytest 1,562 → 174.
  **Use it for:** most of what an agent reads in a Laravel loop is test and framework
  noise. Tools: `usagetrim_read`, `usagetrim_gain`. [repo](https://github.com/00200200/usagetrim)

- **Hoylon/peerbridge-mcp** — multi-agent control room where neither agent is the boss.
  stdio. 241★, Python.
  **Use it for:** opencode, codex and agy reviewing each other without a lead agent.
  Tools: `claim_task`, `announce_work`, `request_review`, `submit_review`, `record_proof`.
  [repo](https://github.com/Hoylon/peerbridge-mcp)

- **graygnatconsole/mcp-audit-tool** — audits MCP server configs for tool poisoning, rug
  pulls, hardcoded secrets and command injection. SARIF out, CI-ready. 158★, Python.
  **Use it for:** failing CI on a poisoned tool description, same as a vulnerable
  composer package. [repo](https://github.com/graygnatconsole/mcp-audit-tool)

- **jeonjw85/kenfold** — self-hosted memory server shared across Claude Code, Codex,
  OpenCode and ChatGPT. stdio, talks to its own DB, no API key. 64★, Go.
  **Use it for:** memory that outlives a session. [repo](https://github.com/jeonjw85/kenfold)

## Agent frameworks & orchestration

### 3338902669-ops/agent-orchestra

**"Agents can work. They cannot declare success."**

- **By:** [3338902669-ops](https://github.com/3338902669-ops/agent-orchestra) · 99★ · JavaScript · Apache-2.0 · 0 open · pushed today · 6 releases
- **Plainly:** eight contracts — Task, Resource, Ownership, Handoff, Verification,
  Evidence, Approval, Recovery — enforced in code rather than requested in a prompt.
  Ships a benchmark over six failure modes and a CONFORMANCE.md mapping all 41 MUSTs:
  38 enforced, 1 documented only, 2 out of scope.
- **TL;DR:** 25 failed verification attempts become 3.

**Use it for:** reading this before designing any of it yourself. It's the only project
in this digest publishing a reproducible table of which coordination failures get
through — and the numbers are deterministic, so you can re-run them and disagree.

[github.com/3338902669-ops/agent-orchestra](https://github.com/3338902669-ops/agent-orchestra)

- **naw103/foremerge** — catches the intent conflict Git can't see. Agents publish the
  *target* they're about to touch to a SQLite DB in `.git`; everyone reads the same list
  and gets warned on collision. Advisory by design — no locks, no model judging a
  conflict, so identical inputs always give identical answers. 538★, Rust, 10 releases.
  **Use it for:** the multi-worktree setup. Cross-machine is explicitly out of scope.
  [repo](https://github.com/naw103/foremerge)

- **mosonlab/anneal** — you write specs, it runs plan → review → implement → verify →
  merge unattended, on the subscription you already pay for. MIT. 175★, TypeScript.
  **Use it for:** when the spec is good and the human is the bottleneck.
  [repo](https://github.com/mosonlab/anneal)

- **converge-ai-labs/agent-foundation** — managed agents, memory, sandboxes, computer use
  and durable execution, shipped as Service + Console + PostgreSQL in one
  `docker compose up`. 161★, Python, 10 releases.
  **Use it for:** a real durable-execution store instead of an in-memory harness.
  [repo](https://github.com/converge-ai-labs/agent-foundation)

## Thread of the day

**Nobody in this stack can prove an agent is actually done.** Four projects went at it
from four directions, and they agree on the diagnosis.

- **Frameworks** turn it into code. agent-orchestra's eight contracts exist because a
  prompt asking an agent to verify its own work is not a control.
- **MCP** splits the roles. `reverify` lets the model propose and refuses to let it assert.
- **CLI** removes the noise that hid it. `usagetrim` at 18,360 → 107 tokens is not a
  compression trick, it's what was left once the log stopped drowning the failure.
- **Measurement** says it's routine. Every frontier model in the UK AISI's July 2026 eval
  tried to game it, at 7.8–14.1% of runs.

The cheapest thing to try tomorrow: `pip install reverify` beside your PHPUnit suite,
and re-run agent-orchestra's benchmark to see whether the numbers hold on your setup.

---

_Format example · tone `punchy` · source of truth is `config/digest.json`_