# Tone: plain

Minimum editorialising. Accurate, dry, neutral. Useful when the digest is an archive you
may want to re-read in a year and wish it hadn't argued with itself.

---

## The voice

- Describe what the thing is and what it does. Nothing else.
- No adjectives that don't come from a measurement.
- No recommendations, no enthusiasm, no dread. The reader draws their own conclusion.
- Keep `config.style.avoid` in force. Neutral is not the same as padded.

## Sentence rules

- Short declarative sentences. Active voice.
- No hooks, no tension, no rhetorical questions.
- Keep it boring on purpose.

## Item format

```
- **20000419/fauxnix** — MCP server and CLI that runs Linux-style commands on Windows by
  translating them to PowerShell. No VM or WSL. 823★, TypeScript. Install: `npm i -g
  fauxnix-cli`. Release: 10, last 2026-10-05. Windows-native.
  **Use it for:** giving agents GNU-shaped shell commands on Windows.
  [repo](https://github.com/20000419/fauxnix)
```

Always include the hard facts: stars, language, release count, install command, platform.
In this tone those facts *are* the item.

## The closing line

Disabled by default in this tone. If `style.closingLine.enabled` is on, keep it factual:

> Runs on Windows natively. Not available for Linux-only tools; check the platform before
> adding to a shared script.

## Thread of the day

Name the pattern, don't sell it:

> Four independent projects this week addressed the same gap: verifying agent output rather
> than trusting it. agent-orchestra enforces contracts in code, reverify splits proposing
> from deciding, usagetrim removes the token noise that hid the problem, and the
> evals-gaming paper measures it at 7.8–14.1% of runs.

## Line to avoid

> ❌ This powerful new framework is revolutionizing the way developers build AI agents.

> ✅ Runs Linux-style commands on Windows by translating them to PowerShell. No VM or WSL.
> 823★, TypeScript, 10 releases. Install via npm.