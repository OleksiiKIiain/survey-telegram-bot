from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.survey import Survey
from app.models.survey_session import SurveySession
from app.schemas.survey import QuestionCreate, QuestionUpdate, SurveyCreate, SurveyUpdate


def get_survey_or_404(db: Session, survey_id: int) -> Survey | None:
    return db.scalar(select(Survey).where(Survey.id == survey_id).options(selectinload(Survey.questions).selectinload(Question.options)))


def create_survey(db: Session, payload: SurveyCreate, admin_id: int) -> Survey:
    survey = Survey(
        title=payload.title,
        title_en=payload.title_en,
        title_uk=payload.title_uk,
        description=payload.description,
        description_en=payload.description_en,
        description_uk=payload.description_uk,
        status=payload.status,
        created_by_id=admin_id,
    )
    db.add(survey)
    db.flush()
    for index, question in enumerate(payload.questions):
        create_question(db, survey.id, question, default_position=index)
    db.flush()
    return survey


def update_survey(db: Session, survey: Survey, payload: SurveyUpdate) -> Survey:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(survey, key, value)
    db.flush()
    return survey


def create_question(db: Session, survey_id: int, payload: QuestionCreate, default_position: int | None = None) -> Question:
    question = Question(
        survey_id=survey_id,
        text=payload.text,
        text_en=payload.text_en,
        text_uk=payload.text_uk,
        type=payload.type,
        is_required=payload.is_required,
        position=payload.position if payload.position is not None else (default_position or 0),
        scale_min=payload.scale_min,
        scale_max=payload.scale_max,
    )
    db.add(question)
    db.flush()
    for index, option in enumerate(payload.options):
        db.add(QuestionOption(question_id=question.id, text=option.text, text_en=option.text_en, text_uk=option.text_uk, position=option.position or index))
    db.flush()
    return question


def update_question(db: Session, question: Question, payload: QuestionUpdate) -> Question:
    data = payload.model_dump(exclude_unset=True)
    options = data.pop("options", None)
    for key, value in data.items():
        setattr(question, key, value)
    if options is not None:
        existing_by_id = {option.id: option for option in question.options}
        seen_ids: set[int] = set()
        for index, option in enumerate(options):
            option_id = option.get("id")
            if option_id and option_id in existing_by_id:
                item = existing_by_id[option_id]
                item.text = option["text"]
                item.text_en = option.get("text_en")
                item.text_uk = option.get("text_uk")
                item.position = option.get("position") or index
                seen_ids.add(option_id)
            else:
                db.add(QuestionOption(
                    question_id=question.id,
                    text=option["text"],
                    text_en=option.get("text_en"),
                    text_uk=option.get("text_uk"),
                    position=option.get("position") or index,
                ))
        for option_id, item in existing_by_id.items():
            if option_id not in seen_ids:
                db.delete(item)
    db.flush()
    return question


def survey_counts(db: Session) -> dict[int, tuple[int, int]]:
    question_rows = db.execute(select(Question.survey_id, func.count(Question.id)).group_by(Question.survey_id)).all()
    response_rows = db.execute(
        select(SurveySession.survey_id, func.count(SurveySession.id)).where(SurveySession.status == "completed").group_by(SurveySession.survey_id)
    ).all()
    counts: dict[int, tuple[int, int]] = {}
    for survey_id, count in question_rows:
        counts[survey_id] = (count, counts.get(survey_id, (0, 0))[1])
    for survey_id, count in response_rows:
        counts[survey_id] = (counts.get(survey_id, (0, 0))[0], count)
    return counts
