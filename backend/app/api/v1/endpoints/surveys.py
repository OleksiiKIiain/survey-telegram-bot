from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.models.question import Question
from app.models.survey import Survey
from app.schemas.survey import QuestionCreate, QuestionRead, QuestionUpdate, SurveyCreate, SurveyDetail, SurveyRead, SurveyUpdate
from app.services.audit import log_action
from app.services.surveys import create_question, create_survey, get_survey_or_404, survey_counts, update_question, update_survey

router = APIRouter()


def to_survey_read(survey: Survey, counts: dict[int, tuple[int, int]]) -> SurveyRead:
    q_count, r_count = counts.get(survey.id, (0, 0))
    return SurveyRead.model_validate({**survey.__dict__, "questions_count": q_count, "responses_count": r_count})


@router.get("", response_model=list[SurveyRead])
def list_surveys(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> list[SurveyRead]:
    surveys = db.scalars(select(Survey).order_by(Survey.created_at.desc())).all()
    counts = survey_counts(db)
    return [to_survey_read(survey, counts) for survey in surveys]


@router.post("", response_model=SurveyDetail, status_code=status.HTTP_201_CREATED)
def create(payload: SurveyCreate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> Survey:
    survey = create_survey(db, payload, current_admin.id)
    log_action(db, current_admin.id, "create", "survey", survey.id, {"title": survey.title})
    db.commit()
    return get_survey_or_404(db, survey.id)


@router.get("/{survey_id}", response_model=SurveyDetail)
def detail(survey_id: int, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> Survey:
    survey = get_survey_or_404(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


@router.patch("/{survey_id}", response_model=SurveyDetail)
def update(survey_id: int, payload: SurveyUpdate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> Survey:
    survey = get_survey_or_404(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    update_survey(db, survey, payload)
    log_action(db, current_admin.id, "update", "survey", survey.id, payload.model_dump(exclude_unset=True))
    db.commit()
    return get_survey_or_404(db, survey.id)


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(survey_id: int, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> None:
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    db.delete(survey)
    log_action(db, current_admin.id, "delete", "survey", survey_id)
    db.commit()


@router.post("/{survey_id}/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def add_question(survey_id: int, payload: QuestionCreate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> Question:
    if not db.get(Survey, survey_id):
        raise HTTPException(status_code=404, detail="Survey not found")
    question = create_question(db, survey_id, payload)
    log_action(db, current_admin.id, "create", "question", question.id, {"survey_id": survey_id})
    db.commit()
    db.refresh(question)
    return question


@router.patch("/{survey_id}/questions/{question_id}", response_model=QuestionRead)
def edit_question(survey_id: int, question_id: int, payload: QuestionUpdate, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> Question:
    question = db.scalar(select(Question).where(Question.id == question_id, Question.survey_id == survey_id).options(selectinload(Question.options)))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    update_question(db, question, payload)
    log_action(db, current_admin.id, "update", "question", question.id, payload.model_dump(exclude_unset=True))
    db.commit()
    return question


@router.delete("/{survey_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_question(survey_id: int, question_id: int, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)) -> None:
    question = db.scalar(select(Question).where(Question.id == question_id, Question.survey_id == survey_id))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    log_action(db, current_admin.id, "delete", "question", question_id, {"survey_id": survey_id})
    db.commit()
