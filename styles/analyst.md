# Tone: analyst

Dense, hedged, architecture-first. Best if the digest is mostly for your own reading
and you want the reasoning, not the pitch. The opposite of `punchy`.

---

## The voice

- Lead with the mechanism, not the benefit.
- Name the tradeoff every time there is one, including the ones the author doesn't mention.
- "This works because X, and stops working when Y" is the shape of a good sentence here.
- Assume a strong reader. No explaining what an MCP server is.

## Sentence rules

- Long sentences are allowed, but only when the clause chain carries real information.
- Quantify aggressively. Latency, error rate, token counts, LOC, commit date.
- Distinguish measured from claimed. If a benchmark is self-reported, say so.
- Calibrate: "reproducible", "self-reported", "single release, no published benchmark".

## Item format

Flat is fine — this tone doesn't need the hook scaffolding.

```
- **naw103/foremerge** — coordination protocol above Git. Agents publish the *target* they
  are about to touch to a SQLite DB in `.git`; every agent reads the same list and gets
  warned on collision. Advisory by design: no file locks, no model judging a conflict, so
  the same inputs always give the same answer. 538★ Rust, 10 releases.
  **Use it for:** the multi-worktree setup — its worked example (one agent migrating callers
  to `StripePaymentService` while another adds PayPal to the old `PaymentService`, Git
  merging both cleanly) is the failure you'd hit first.
  [repo](https://github.com/naw103/foremerge)
```

## What to say about limitations

Not optional in this tone. If it's Linux-only, say Linux-only. If there's one release and
no benchmark, say that. An item with a clear weakness is more useful than one without it.

## Closing line

Keep it, but make it a recommendation with a reason:

> If you only install one thing here, make it this one — it replaces a class of bug rather
> than a specific one.

## Category intro

Useful in this tone. One or two lines framing what the category's items have in common,
including the part of the field that's overhyped right now.

## Line to avoid

> ❌ This powerful new framework is revolutionizing the way developers build AI agents,
> offering a seamless and robust experience.

> ✅ Deterministic, advisory-only conflict detection via a shared SQLite intent log inside
> `.git`. Tradeoff: single-machine by design, and cross-machine coordination is explicitly
> out of scope. Useful precisely because it never locks — a crashed agent can't stall a
> fleet — at the cost of being unable to enforce anything.