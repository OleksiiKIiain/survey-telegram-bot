from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.answer import Answer
from app.models.question import Question
from app.models.survey_session import SurveySession
from app.schemas.session import AnswerRead, SessionRead

router = APIRouter()


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(survey_id: int | None = None, db: Session = Depends(get_db), _=Depends(get_current_admin)) -> list[SurveySession]:
    query = select(SurveySession).order_by(SurveySession.started_at.desc())
    if survey_id:
        query = query.where(SurveySession.survey_id == survey_id)
    return list(db.scalars(query).all())


@router.get("/answers", response_model=list[AnswerRead])
def list_answers(survey_id: int | None = None, session_id: int | None = None, db: Session = Depends(get_db), _=Depends(get_current_admin)) -> list[AnswerRead]:
    query = (
        select(Answer)
        .join(SurveySession)
        .options(joinedload(Answer.question).selectinload(Question.options), joinedload(Answer.option))
        .order_by(Answer.created_at.desc())
    )
    if survey_id:
        query = query.where(SurveySession.survey_id == survey_id)
    if session_id:
        query = query.where(Answer.session_id == session_id)
    answers = db.scalars(query).all()
    def option_lists(answer: Answer) -> tuple[list[str], list[str], list[str]]:
        if not answer.question or not answer.option_ids:
            return [], [], []
        selected = set(answer.option_ids)
        options = [option for option in answer.question.options if option.id in selected]
        return (
            [option.text for option in options],
            [option.text_en or option.text for option in options],
            [option.text_uk or option.text for option in options],
        )

    result: list[AnswerRead] = []
    for answer in answers:
        option_texts, option_texts_en, option_texts_uk = option_lists(answer)
        result.append(
            AnswerRead.model_validate(
                {
                    **answer.__dict__,
                    "question_text": answer.question.text if answer.question else None,
                    "question_text_en": (answer.question.text_en or answer.question.text) if answer.question else None,
                    "question_text_uk": (answer.question.text_uk or answer.question.text) if answer.question else None,
                    "option_text": answer.option.text if answer.option else None,
                    "option_text_en": (answer.option.text_en or answer.option.text) if answer.option else None,
                    "option_text_uk": (answer.option.text_uk or answer.option.text) if answer.option else None,
                    "option_texts": option_texts,
                    "option_texts_en": option_texts_en,
                    "option_texts_uk": option_texts_uk,
                }
            )
        )
    return result
