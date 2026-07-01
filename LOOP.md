# LOOP.md — TestSprite CLI fail → fix → rerun log

Built for **TestSprite Hackathon Season 3 (Build the Loop)**. This file is the living log
of every create → run → failure-bundle → fix → rerun round executed with the open-source
TestSprite CLI against the live deployment. Rounds are appended as they happen, not
reconstructed afterwards.

## Meta

| | |
| --- | --- |
| TestSprite account | `lupengcheng1729@gmail.com` |
| Frontend project | `reelmatrix` · id `c02a8edd-8926-4dd3-9f0b-f62b114563c8` |
| Backend project | `reelmatrix-api` · id `8f1a9a08-31f1-4bab-91e3-8d51627bcf40` |
| CLI version | `0.2.0` |
| Live app | http://121.43.99.199:3000 (web) · http://121.43.99.199:8000 (API) |
| Deploy marker | `GET /health` → `{status, commit}` — every rerun first verifies the fix is live |
| Date range | 2026-07-01 → (ongoing) |

## Summary

| Round | Test ID | What failed | Root cause | Fix commit | Rerun result |
| --- | --- | --- | --- | --- | --- |
| _pending_ | | | | | |

_Suite creation is scheduled after the current build ships to the live server, so tests are
banked against the UX being submitted. Rounds will be logged below as they run._

## Rounds

_(appended per round: failure summary with key bundle log lines / screenshots →
diagnosis → fix → rerun evidence)_

## Final suite

_(full `testsprite test list` output + pass rate at submission time)_

## Artifacts

Failure bundles are committed under `.testsprite/failure/<test_id>/` (summaries, logs, and
key screenshots; media files larger than 5 MB are excluded and noted per round).
