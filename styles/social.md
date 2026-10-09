# Tone: social

Optimised for copy-paste into a post, not for reading end to end. Every line is written
so it survives being lifted out of context.

This tone produces the material `tools/render_assets.py` turns into PNG cards, and the
lines you paste into dev.to / LinkedIn / X by hand.

---

## The rules that matter here

- **The TL;DR must work alone.** Someone will read only that line. No pronouns pointing
  back at the item, no "this", no "it".
- **A TL;DR is a claim or a number, never a description.** "Count and truncate text by
  token" is a description. "The WSL prompt is now optional" is a claim.
- **Under 90 characters** where you can. It has to fit a card.
- Never a question. Never an exclamation unless it's genuine.
- **No item title, no hype, no "you won't believe".** The fact is the hook.

## TL;DR patterns that travel well

Pick the one that fits; don't force all of them.

- The inversion — `The WSL prompt is now optional.`
- The number — `18,360 tokens of docker output, down to 107.`
- The blunt verdict — `Linux only. Skip it.`
- The quiet reframe — `Git can't see intent. This can.`
- The stakes — `Every model in the AISI eval tried to cheat. All of them.`
- The permission slip — `AGPL. Noted before you copy a line.`

## Item format

The hook line does double duty as the card headline, so write it first.

```
### falsharing

**Your agents get a real shell on Windows.**

- **By:** 20000419 · 823★ · TypeScript · `npm i -g fauxnix-cli`
- **TL;DR:** the WSL prompt is now optional.

**Use it for:** default shell for every agent in the repo.

[github.com/20000419/fauxnix](https://github.com/20000419/fauxnix)
```

**Plainly** is optional here — on a card there's no room, and the TL;DR already carries it.
Add it only when the TL;DR is genuinely too terse to be useful on its own.

## Thread of the day

Two or three lines, quotable, no preamble. This is the line most likely to get screenshotted.

> Nobody in this stack can currently prove an agent is done. Four projects today attacked it
> from four directions, and one of them published a benchmark saying models cheat on their
> own evals 7.8% of the time.

## Category cards

`render_assets.py` pulls one line per category for the cards. That line must stand alone
with no surrounding context, because it will appear under a heading and nothing else.

Good:
> Ten agent skills. Three of them conflict with each other on install.

Bad:
> Here are some great tools that you should check out!

## Line to avoid

> ❌ This powerful MCP server seamlessly bridges the gap between AI agents and your
> development workflow! 🎉

> ✅ Deterministic claim verification: the model proposes, tools decide, every claim carries
> evidence. `pip install reverify`.