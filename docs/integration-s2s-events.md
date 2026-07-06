# First-party conversion events (S2S) — 30-minute integration

ReelMatrix attributes content → signup → activation → paid **without
third-party cookies**: every post carries a UTM-tagged link, and your backend
reports conversions server-to-server. When real events exist for a post, they
override the modeled numbers in the Results view (the row's source flips to
`events`).

## 1. The tracking link

Every approved post already carries its link (Results → post table → `UTM ⧉`),
shaped like:

```
https://yoursite.com/?utm_source=linkedin&utm_medium=social&utm_campaign=v2-launch&utm_content=a1b2c3d4
```

`utm_content` is the 8-char asset id — **the join key**. Persist it on the
visitor at landing (cookie/localStorage/session), carry it through signup into
your user record.

## 2. Report events

`POST /api/v1/events` with the member header (a per-tenant ingest token
replaces this in production):

```bash
curl -X POST "$REELMATRIX_API/api/v1/events" \
  -H "X-Member-Id: $MEMBER_ID" \
  -H "Content-Type: application/json" \
  -d '{"event": "signup", "utm_content": "a1b2c3d4"}'
```

| Field | Required | Notes |
| --- | --- | --- |
| `event` | yes | `signup` \| `activation` \| `paid` |
| `utm_content` | yes | the join key from the tracking link |
| `utm_campaign` / `utm_source` / `utm_medium` | no | pass through if you have them |
| `click_id` | no | your own click/session id, for your reconciliation |
| `payload` | no | any JSON you want stored alongside |

Python (e.g. in your signup handler):

```python
import httpx

def report_conversion(event: str, utm_content: str) -> None:
    if not utm_content:
        return
    try:
        httpx.post(
            f"{REELMATRIX_API}/api/v1/events",
            headers={"X-Member-Id": MEMBER_ID},
            json={"event": event, "utm_content": utm_content},
            timeout=3,
        )
    except httpx.HTTPError:
        pass  # never let attribution break signup
```

Fire `activation` when the user becomes product-qualified (API key created /
first run), `paid` on conversion.

## 3. What you get

- Results view: that post's signup/activation/paid columns become **real**
  (source `events`), the funnel bars follow.
- The learning flywheel (`insights/learn`) starts training on real conversions
  instead of modeled ones — which is what makes next campaigns' channel and
  hook choices evidence-based.

## Semantics

- Events are **counted, not deduplicated** — send each conversion once.
- Events are first-party facts; they always beat modeled/synced numbers for
  the same post.
- Web-analytics sources (Plausible/GA4) cover traffic and signups;
  activation/paid are product events and only ever arrive through this
  endpoint.
