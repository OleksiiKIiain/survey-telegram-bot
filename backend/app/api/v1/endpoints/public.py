from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.answer import Answer
from app.models.question import Question
from app.models.respondent import TelegramUser
from app.models.survey import Survey
from app.models.survey_session import SurveySession
from app.schemas.respondent import RespondentCreate, RespondentRead
from app.schemas.session import AnswerCreate, PublicSessionPayload, SessionCreate, SessionRead
from app.schemas.survey import SurveyDetail, SurveyRead
from app.services.surveys import get_survey_or_404, survey_counts

router = APIRouter()


@router.get("/surveys", response_model=list[SurveyRead])
def active_surveys(db: Session = Depends(get_db)) -> list[SurveyRead]:
    surveys = db.scalars(select(Survey).where(Survey.status == "active").order_by(Survey.created_at.desc())).all()
    counts = survey_counts(db)
    return [
        SurveyRead.model_validate({**survey.__dict__, "questions_count": counts.get(survey.id, (0, 0))[0], "responses_count": counts.get(survey.id, (0, 0))[1]})
        for survey in surveys
    ]


@router.get("/surveys/{survey_id}", response_model=SurveyDetail)
def public_survey_detail(survey_id: int, db: Session = Depends(get_db)) -> Survey:
    survey = get_survey_or_404(db, survey_id)
    if not survey or survey.status != "active":
        raise HTTPException(status_code=404, detail="Active survey not found")
    return survey


@router.post("/respondents", response_model=RespondentRead, status_code=status.HTTP_201_CREATED)
def upsert_respondent(payload: RespondentCreate, db: Session = Depends(get_db)) -> RespondentRead:
    user = db.scalar(select(TelegramUser).where(TelegramUser.telegram_id == payload.telegram_id))
    if not user:
        user = TelegramUser(**payload.model_dump())
        db.add(user)
    else:
        for key, value in payload.model_dump().items():
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return RespondentRead.model_validate({**user.__dict__, "sessions_count": len(user.sessions)})


@router.post("/sessions", response_model=PublicSessionPayload, status_code=status.HTTP_201_CREATED)
def start_session(payload: SessionCreate, db: Session = Depends(get_db)) -> PublicSessionPayload:
    survey = get_survey_or_404(db, payload.survey_id)
    respondent = db.get(TelegramUser, payload.respondent_id)
    if not survey or survey.status != "active":
        raise HTTPException(status_code=404, detail="Active survey not found")
    if not respondent:
        raise HTTPException(status_code=404, detail="Respondent not found")
    session = SurveySession(survey_id=survey.id, respondent_id=respondent.id, status="in_progress")
    db.add(session)
    db.commit()
    db.refresh(session)
    return PublicSessionPayload(session=session, survey=survey, answered_question_ids=[])


@router.get("/sessions/{session_id}", response_model=PublicSessionPayload)
def get_session(session_id: int, db: Session = Depends(get_db)) -> PublicSessionPayload:
    session = db.get(SurveySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    survey = get_survey_or_404(db, session.survey_id)
    answered = db.scalars(select(Answer.question_id).where(Answer.session_id == session.id)).all()
    return PublicSessionPayload(session=session, survey=survey, answered_question_ids=list(answered))


@router.post("/sessions/{session_id}/answers", status_code=status.HTTP_201_CREATED)
def save_answer(session_id: int, payload: AnswerCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    session = db.get(SurveySession, session_id)
    question = db.scalar(select(Question).where(Question.id == payload.question_id).options(selectinload(Question.options)))
    if not session or session.status != "in_progress":
        raise HTTPException(status_code=400, detail="Session is not active")
    if not question or question.survey_id != session.survey_id:
        raise HTTPException(status_code=400, detail="Question does not belong to session survey")

    option_ids = [option.id for option in question.options]
    if question.type == "single_choice" and payload.option_id not in option_ids:
        raise HTTPException(status_code=422, detail="Invalid option")
    if question.type == "multiple_choice" and (not payload.option_ids or any(item not in option_ids for item in payload.option_ids)):
        raise HTTPException(status_code=422, detail="Invalid options")
    if question.type == "free_text" and not payload.text_value:
        raise HTTPException(status_code=422, detail="Text answer is required")
    if question.type == "scale" and (payload.number_value is None or payload.number_value < (question.scale_min or 1) or payload.number_value > (question.scale_max or 5)):
        raise HTTPException(status_code=422, detail="Invalid scale value")

    db.query(Answer).filter(Answer.session_id == session_id, Answer.question_id == payload.question_id).delete()
    db.add(Answer(session_id=session_id, **payload.model_dump()))
    db.commit()
    return {"status": "saved"}


@router.post("/sessions/{session_id}/complete", response_model=SessionRead)
def complete_session(session_id: int, db: Session = Depends(get_db)) -> SurveySession:
    session = db.get(SurveySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session
