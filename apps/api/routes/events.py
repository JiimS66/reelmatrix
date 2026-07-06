"""First-party conversion ingest (S2S postback style).

The customer's backend fires signup/activation/paid events tagged with the UTM
content id ReelMatrix minted on the tracking link — server-to-server, no
third-party cookies. When real events exist for a post they override the
mock/synced funnel numbers in the performance view.

Auth is the same development stub as the team API (``X-Member-Id``); a real
deployment swaps this for a per-tenant ingest token.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from apps.api.routes.team import get_current_member
from apps.api.schemas.team import ConversionEventRequest
from core.db.engine import get_session
from core.db.models import ConversionEvent, Member
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/events", tags=["events"])


class IngestResult(BaseModel):
    ok: bool
    stored: int
    total_for_content: int


@router.post("", response_model=IngestResult)
def ingest_event(
    payload: ConversionEventRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> IngestResult:
    session.add(
        ConversionEvent(
            tenant_id=actor.tenant_id,
            event=payload.event,
            utm_campaign=payload.utm_campaign,
            utm_source=payload.utm_source,
            utm_medium=payload.utm_medium,
            utm_content=payload.utm_content,
            click_id=payload.click_id,
            payload=payload.payload,
        )
    )
    session.commit()
    total = len(
        session.exec(
            select(ConversionEvent).where(
                ConversionEvent.tenant_id == actor.tenant_id,
                ConversionEvent.utm_content == payload.utm_content,
            )
        ).all()
    )
    return IngestResult(ok=True, stored=1, total_for_content=total)
