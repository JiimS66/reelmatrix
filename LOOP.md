# LOOP.md — TestSprite CLI fail → fix → rerun log

Built for **TestSprite Hackathon Season 3 (Build the Loop)**. This file is the living log
of every create → run → failure-bundle → fix → rerun round executed with the open-source
TestSprite CLI against the live deployment. Rounds are appended as they happen, not
reconstructed afterwards.

## Meta

| | |
| --- | --- |
| TestSprite account (Account A) | `lupengcheng1729@gmail.com` |
| Frontend project (Account A) | `reelmatrix` · id `c02a8edd-8926-4dd3-9f0b-f62b114563c8` |
| Backend project (Account A) | `reelmatrix-api` · id `8f1a9a08-31f1-4bab-91e3-8d51627bcf40` |
| TestSprite account (Account B) | `JiimSmith66@outlook.com` |
| Frontend project (Account B) | `ReelMatrix` · id `0e9b9bee-2ca7-4553-9706-3857a3e65289` |
| Backend project (Account B) | `reelmatrix-api` · id `364babc2-b2b6-43e8-a6b2-4edd5f535e07` |
| CLI version | `0.2.0` |
| Live app | http://121.43.99.199:3000 (web) · http://121.43.99.199:8000 (API) |
| Deploy marker | `GET /health` → `{status, commit}` — every rerun first verifies the fix is live |
| Date range | 2026-07-01 → (ongoing) |

## Summary

| Round | Test ID | What failed | Root cause | Fix commit | Rerun result |
| --- | --- | --- | --- | --- | --- |
| _pending_ | | | | | |

_Fix rounds are logged as they happen. The initial 4-test slice below ran green against
the live deployment; the suite deepens (edge inputs, review flow, brand hub, `/health`
deploy marker) after the next deploy, per the honesty rule — coverage grows until real
failures surface._

## Initial suite — first runs (2026-07-01, live target)

| Test ID | Type | Behavior | First terminal verdict |
| --- | --- | --- | --- |
| `cddeeaee-7b01-45ab-bbbe-1038ea716adc` | backend | Team roster reads + a strategy session write (turn-1 draft offers audiences & angles) | **passed** (after the suite-setup fix below) |
| `bfd1970e-5d37-4c6c-8577-71d6bb356d34` | backend | Legacy `POST /api/v1/campaign/generate` returns a full plan | **passed** |
| `e9256603-ea41-4c86-b6cd-ad7866575c25` | frontend | Strategy advisor drafts a one-page strategy and folds in a feedback round | **passed** |
| `2e6a5f9d-d537-4d5a-a195-07f3d9797005` | frontend | Locking the strategy drafts first cross-channel content | **passed** (run `835ee1da`, 7/7 steps) |

### Suite-setup note (not counted as a fix round — test-harness config, not a product bug)

The first backend run came back `blocked` with `name 'BASE_URL' is not defined`. Pulling
the failure bundle (`testsprite test artifact get …`) showed the platform rewrites backend
code to read an injected `BASE_URL` sourced from the project's default URL — which was
empty because `project create --type backend` had been called without `--url`. Fix: made
the test code self-contained (it defines its own target base URL) via
`testsprite test code put … --expected-version v1`, and set the project default URL with
`project update`. Rerun → **passed**. Kept here as evidence of the create → run → bundle →
fix → rerun mechanics; product-bug rounds are logged below as they occur.

## Rounds

_(appended per round: failure summary with key bundle log lines / screenshots →
diagnosis → fix → rerun evidence)_

## Final suite

_(full `testsprite test list` output + pass rate at submission time)_

## Artifacts

Failure bundles are committed under `.testsprite/failure/<test_id>/` (summaries, logs, and
key screenshots; media files larger than 5 MB are excluded and noted per round).
