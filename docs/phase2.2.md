# Phase 2.2: Browser Campaign History

## Product angle

Phase 2.2 makes ReelMatrix feel more like a working AI Campaign Studio instead of a one-shot generator. A small team can generate a campaign package, refresh the browser, reopen the previous package, continue editing draft assets, and export the latest version.

This is intentionally browser-local persistence. It validates the workflow value before adding accounts, databases, or team workspaces.

## In scope

- Save generated campaign workflow responses in browser localStorage.
- Keep the request, provider id, ideation result, campaign plan, market adaptation, and draft assets together.
- Show a campaign history panel under the brief form.
- Load a saved campaign package back into the workspace.
- Delete saved campaign records from the browser.
- Persist edited draft asset copy back into the active history record.
- Limit history to the 10 most recently updated records.
- Recover safely from corrupted localStorage data.

## Out of scope

- Cloud database persistence
- Authentication or user accounts
- Multi-user team workspaces
- Cross-device sync
- Version history per asset
- Server-side campaign storage APIs
- Export formats beyond the existing Markdown flow

## Acceptance criteria

1. A generated campaign package appears in the Campaign history panel.
2. Refreshing the browser keeps recent saved packages available.
3. Clicking a saved package restores its ideation and campaign plan workspace.
4. Editing a draft asset updates the active saved record.
5. Deleting a saved package removes it from the browser history.
6. Invalid localStorage data does not crash the app.
7. Frontend tests cover persistence utilities, history panel behavior, and workspace edit callbacks.

## Recommended next phase

Phase 2.3 should decide whether the product is moving toward deeper editing or stronger generation quality. The highest-value options are:

- per-asset regenerate actions with channel-specific instructions
- brand context fields such as proof points, forbidden words, competitors, and tone rules
- richer export formats such as `.docx` campaign brief or CSV content calendar
- sample templates for SaaS, ecommerce, agency, and creator-led products
