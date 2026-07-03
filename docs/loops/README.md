# Loop evidence

Curated, committed evidence for every TestSprite fail → fix → rerun round logged in
[`LOOP.md`](../../LOOP.md).

One directory per round: `docs/loops/<NN>-<test_id_short>/` containing

- `summary.md` — what failed, root cause, fix commit, rerun result (mirrors the LOOP.md entry)
- key excerpts from the failure bundle (log lines, the failing step)
- one or two screenshots when they carry signal

Raw bundles are pulled to `.testsprite/failure/` at loop time; that directory is
runtime-only and git-ignored. Media files over 5 MB stay out of the repo and are noted
in the round's `summary.md`.
