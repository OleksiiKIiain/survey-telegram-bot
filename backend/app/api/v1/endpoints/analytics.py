from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.schemas.analytics import AnalyticsOverview
from app.services.analytics import build_analytics

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    survey_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
) -> AnalyticsOverview:
    return build_analytics(db, survey_id=survey_id, date_from=date_from, date_to=date_to)
