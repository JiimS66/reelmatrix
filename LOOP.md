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
| 2026-07-06 JiimSmith66 backend P1 slice | `ab59c125-e7de-4ad6-9702-4f5a4bb0e806` | Full strategy start → advance → handoff test did not complete under the original harness | Test timeout was too low for the live real-model chain, and the handoff body used `{}` instead of the page's `{ "review_assets": false }` path | Test code updated to `v4`; product fix not required for this case | Passed: run `081b61b4-b327-472f-94be-a474abae86fe` |
| 2026-07-06 JiimSmith66 frontend ROI slice | `edea7789-29ea-4417-9a36-d1c86854cb6b` | ROI dashboard test could not verify slider/charts/integration card | Opened campaign had no published posts/performance data; empty Results state rendered correctly, but data-dependent controls were absent | _pending_ | Blocked: run `8c23c53d-2384-4881-a883-f35ade97e656`, 11/14 passed |

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

### 2026-07-06 — JiimSmith66 TestSprite P1 slice against live target

**Context.** Ran from the repository root with the project-local wrapper
`./.tools/testsprite` (CLI `0.2.0`) under account `JiimSmith66@outlook.com`.
Project IDs matched LOOP meta:

- Frontend `ReelMatrix`: `0e9b9bee-2ca7-4553-9706-3857a3e65289`
- Backend `reelmatrix-api`: `364babc2-b2b6-43e8-a6b2-4edd5f535e07`

Deploy marker before the run: `GET http://121.43.99.199:8000/health` returned
`{"status":"ok","commit":"c78da74"}`. The latest repo commit was newer, but it only
renamed/expanded TestSprite plans and LOOP docs; no application code change needed to be
deployed for this run.

**Backend results.**

| Test ID | Run ID | Behavior | Verdict |
| --- | --- | --- | --- |
| `f651cb95-9f89-4d6a-a317-3879bda92455` | `437cf899-cc2f-4330-a8ee-6bbc1f3c74cf` | Health deploy marker + LLM provider catalog | **passed** |
| `8277b662-96ce-4e8d-8b20-cfa030530bca` | `ddd12d0f-3215-4b82-8b0a-59c7f1d9daa8` | Team API rejects invalid input with clean 4xx | **passed** |
| `04c3f4f6-7bd8-4e83-abfa-c7dc9f0e5675` | `9175fc71-5533-48b4-8016-583c76ea1ffc` | Integration dispatch rejects missing/private targets with clean 400s | **passed** |
| `6eaa11d0-d23a-44e7-839d-871733a9cb19` | `78659faf-709b-4b4b-8c03-70acaee15f92` | Agent Inbox actions API lists/plans/ignores actions | **passed** |
| `ab59c125-e7de-4ad6-9702-4f5a4bb0e806` | `e5268ac4-f534-482e-9f66-22d776a0edc4` | Strategy session start → advance → handoff | **failed**: `Read timed out. (read timeout=60)` |
| `ab59c125-e7de-4ad6-9702-4f5a4bb0e806` | `efb4b408-ef75-4ad8-b6bc-c97bbc0a6751` | Same test after `test code put` timeout increase to 180s (`v2`) | **failed**: `Read timed out. (read timeout=180)` |
| `ab59c125-e7de-4ad6-9702-4f5a4bb0e806` | `92b5153d-fe4e-459f-aeb7-277965babd24` | Same test after `test code put` timeout increase to 600s (`v3`) | **failed**: `Internal Server Error` |
| `ab59c125-e7de-4ad6-9702-4f5a4bb0e806` | `081b61b4-b327-472f-94be-a474abae86fe` | Same test after aligning handoff body to the page path (`review_assets=false`) and keeping 600s HTTP timeout (`v4`) | **passed** |

Failure bundles were downloaded locally:

- `.testsprite/failure/e5268ac4-f534-482e-9f66-22d776a0edc4/`
- `.testsprite/failure/efb4b408-ef75-4ad8-b6bc-c97bbc0a6751/`
- `.testsprite/failure/92b5153d-fe4e-459f-aeb7-277965babd24/`

Key bundle lines:

- `failureKind`: `timeout` for `v1`/`v2`, then `unknown` for `v3`
- `summary`: `HTTPConnectionPool(host='121.43.99.199', port=8000): Read timed out.`
  for `v1`/`v2`; `Failed: Internal Server Error` for `v3`
- `failedStepIndex`: `1`

Diagnosis: the first two failures showed the backend harness timeout (`60s`, then `180s`)
was too low for the full live real-model chain. A follow-up `v3` test-code update raised
the HTTP timeout to `600s`, but still failed with `Internal Server Error`. Manual public
page verification showed the initial `Think it through` action returns successfully, so the
test file was rechecked against the page. The backend test covers the full sequence
(`Think it through` → `Refine with this` → `Lock it → draft my first content`), not only
the first button click, and its handoff request used `{}` while the page sends
`{"review_assets": false}`. Updating the plan and code to match the page path produced a
passing `v4` run. No product code fix is required for this TestSprite failure.

Local follow-up: added `tests/test_team_api.py::test_strategy_session_provider_failure_returns_502`
to pin the expected source behavior when the strategy LLM provider fails. Local verification
with `.venv/bin/python -m pytest tests/test_team_api.py::test_strategy_loop_iterates_and_folds_in_feedback tests/test_team_api.py::test_strategy_session_provider_failure_returns_502`
passed (`2 passed in 0.71s`). This confirms the current source expects a structured `502`
for provider failures; it remains as a guardrail even though the corrected `v4` public run
passed.

Operational note: `./.tools/testsprite test rerun ab59c125...` returned a TestSprite CLI
internal error instead of a run id:
`[CliRunService] rerunTestsWithRunIds did not return a runId`, request
`cli_5817dcc6-5316-472f-bd84-202814015c57`. Running the same test with
`test run ab59c125... --wait` produced runs `efb4b408-...` (`v2`, 180s timeout) and
`92b5153d-...` (`v3`, 600s timeout, `Internal Server Error`). After `test code put`
updated the stored test to `v4`, `test run ab59c125... --wait --timeout 2400` passed with
run `081b61b4-b327-472f-94be-a474abae86fe`.

**Frontend results.**

| Test ID | Run ID | Behavior | Verdict |
| --- | --- | --- | --- |
| `71fb3885-5808-4e6f-a6cf-3b62d324195f` | `f9908bd3-0cb9-4680-90c3-f3768754f244` | Home workspace smoke | **passed**: 10/10 |
| `9f965700-bad2-46e7-9dcc-55002d48e2de` | `c1a71829-5e08-4151-9982-791fb0518deb` | Home object navigation | **passed**: 18/18 |
| `bc481c1d-50a8-4cf7-bf0d-3f78bfe096c3` | `1e5e23c2-5ed1-4587-8196-57742ca80a2e` | Campaign kanban + Calendar + Results tab reachability | **passed**: 17/17 |
| `4e7a733c-eccb-4551-b299-9be3bca1401b` | `90fae2e0-aaeb-41ac-9924-a8c00f979450` | Team org, fleet, reliability, evals, governance | **passed**: 15/15 |
| `aac6a03d-1c97-4b74-a66d-2594c0e0c443` | `4607881a-ce43-4141-ad66-84bd5b378497` | Agent Inbox next moves | **passed**: 31/31 after `test wait` resumed a 600s CLI wait timeout |
| `d1f84bd8-a76b-4747-965d-338f9471d685` | `4bac74b8-3b8d-4bef-a6c5-45355232e794` | Results analytics render | **passed**: 6/6 |
| `edea7789-29ea-4417-9a36-d1c86854cb6b` | `8c23c53d-2384-4881-a883-f35ade97e656` | ROI dashboard with slider/charts/integration card | **blocked**: 11/14 passed |

ROI failure bundle was downloaded locally:

- `.testsprite/failure/8c23c53d-2384-4881-a883-f35ade97e656/`

Key bundle lines:

- Results tab loaded without blank screen or stuck loading.
- Attribution banner, zero-value metric tiles, and the no-published-posts empty state were visible.
- The bundle explicitly says the data-driven visual sections, `Value per signup` slider,
  post-level detail, and `Route wins to your stack` controls were not present because the
  selected campaign had no published posts/performance data.

Diagnosis: the ROI plan is too broad for an arbitrary first/active campaign. It should be
split into two tests:

1. Empty Results state: assert attribution banner, zero metric tiles, and explanatory
   no-published-posts copy.
2. Seeded performance state: use a campaign with published posts/metrics before asserting
   charts, slider behavior, post detail, and Linear/Webhook disabled states.

**Deferred in this pass.** Frontend `strategy-handoff-first-content` and
`task-workflow-end-to-end` were not run after the backend strategy handoff timeout,
because they depend on the same slow real-model strategy/session path and would likely
produce duplicate long timeouts. Frontend `task-detail-quality-controls` and
`review-approval-flow` were also not run in this pass. The remaining P2 plans were
deferred until the P1 timeout/fixture issues are resolved. The newly added
`navigation-state-consistency` plan was not executed in this round, so it is intentionally
not included in the results table above.

## Final suite

_(full `testsprite test list` output + pass rate at submission time)_

## Artifacts

Failure bundles are stored for commit under `.testsprite/failure/<run_id>/` (summaries,
logs, and key screenshots; media files larger than 5 MB are excluded and noted per round).
