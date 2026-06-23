from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.respondent import TelegramUser
from app.models.survey_session import SurveySession
from app.schemas.respondent import RespondentRead

router = APIRouter()


@router.get("", response_model=list[RespondentRead])
def list_respondents(db: Session = Depends(get_db), _=Depends(get_current_admin)) -> list[RespondentRead]:
    users = db.scalars(select(TelegramUser).order_by(TelegramUser.created_at.desc())).all()
    counts = dict(db.execute(select(SurveySession.respondent_id, func.count(SurveySession.id)).group_by(SurveySession.respondent_id)).all())
    return [RespondentRead.model_validate({**user.__dict__, "sessions_count": counts.get(user.id, 0)}) for user in users]
