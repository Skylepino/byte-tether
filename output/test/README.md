# output/test — the QA fixture

Everything in here is **tracked in git** on purpose, even though the rest of `output/`
is ignored. This folder is what a real run's output gets compared against.

## Why it exists

Whenever `config/digest.json`, `styles/*.md` or the output format changes, the question
is "does a run still look right?" and the honest answer used to require firing a real
run and waiting for live sources.

Instead: read `example.md` and ask whether a fresh run would still resemble it.

## What's here

| File | What it is |
|---|---|
| `example.md` | Reference output. Real items from the 2026-10-09 run, trimmed to 3 of 6 categories so the shape is quick to judge. |
| `example.pdf` | The above rendered to PDF — what a real run's PDF looks like. |
| `example-*.png` | Cover card plus one card per category, 1200×630. |

## Checks worth doing after any change

1. **Tone.** Read three items out loud. Do they sound like a person or like a summary
   generator? Anything in `config.style.avoid` appearing verbatim is a failure.
2. **No ranking.** Tier A items are *explained*, not *best*. If it reads like a "top 5",
   something got labelled that shouldn't be.
3. **Author present.** Every in-depth item names who made it and links them.
4. **TL;DR stands alone.** Someone reading only that line should get the point.
5. **"Use it for" is a verb.** An action, not a restatement of the README.
6. **Closing line is scarce.** At most one per category, none on in-depth items.
7. **Cards fit.** Open the PNGs. If a headline is cut mid-word or chips are pushed off
   the bottom, `clip()` limits in `tools/render_assets.py` need lowering.

## Regenerating

```powershell
python tools\render_assets.py --selftest          # parser self-check
python tools\render_assets.py output\test\example.md --outdir output\test
```

The self-test must pass before you trust a re-render. It caught three real bugs while
this format was being built: double-wrapped links, `- **By:**` parsed as an item name,
and `_text_` italics not being recognised.

## Writing a new example

Replace `example.md` wholesale after a real run you liked, keep the date honest, and
re-render the assets. Don't hand-edit the PDF or the PNGs.