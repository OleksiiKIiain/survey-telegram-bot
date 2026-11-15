from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.answer import Answer
from app.models.question import Question
from app.models.respondent import TelegramUser
from app.models.survey import Survey
from app.models.survey_session import SurveySession
from app.schemas.analytics import AnalyticsOverview, QuestionAnalytics, RecentSession


def localized_pair(primary: str | None, en: str | None, uk: str | None) -> tuple[str | None, str | None]:
    return en or primary, uk or primary


def build_analytics(db: Session, survey_id: int | None = None, date_from: datetime | None = None, date_to: datetime | None = None) -> AnalyticsOverview:
    session_filters = []
    if survey_id:
        session_filters.append(SurveySession.survey_id == survey_id)
    if date_from:
        session_filters.append(SurveySession.started_at >= date_from)
    if date_to:
        session_filters.append(SurveySession.started_at <= date_to)

    total_respondents = db.scalar(select(func.count(func.distinct(SurveySession.respondent_id))).where(*session_filters)) or 0
    total_sessions = db.scalar(select(func.count(SurveySession.id)).where(*session_filters)) or 0
    completed_sessions = db.scalar(select(func.count(SurveySession.id)).where(SurveySession.status == "completed", *session_filters)) or 0
    active_surveys = db.scalar(select(func.count(Survey.id)).where(Survey.status == "active")) or 0
    status_rows = db.execute(select(SurveySession.status, func.count(SurveySession.id)).where(*session_filters).group_by(SurveySession.status)).all()

    questions_query = select(Question).options(selectinload(Question.options)).order_by(Question.position)
    if survey_id:
        questions_query = questions_query.where(Question.survey_id == survey_id)
    question_stats: list[QuestionAnalytics] = []
    for question in db.scalars(questions_query).all():
        answers = db.scalars(select(Answer).join(SurveySession).where(Answer.question_id == question.id, *session_filters)).all()
        question_text_en, question_text_uk = localized_pair(question.text, question.text_en, question.text_uk)
        stat = QuestionAnalytics(
            question_id=question.id,
            question_text=question.text,
            question_text_en=question_text_en,
            question_text_uk=question_text_uk,
            question_type=question.type,
            total_answers=len(answers),
        )
        if question.type == "single_choice":
            stat.distribution = [
                {
                    "name": option.text,
                    "name_en": option.text_en or option.text,
                    "name_uk": option.text_uk or option.text,
                    "value": sum(1 for answer in answers if answer.option_id == option.id),
                }
                for option in question.options
            ]
        elif question.type == "multiple_choice":
            stat.distribution = [
                {
                    "name": option.text,
                    "name_en": option.text_en or option.text,
                    "name_uk": option.text_uk or option.text,
                    "value": sum(1 for answer in answers if answer.option_ids and option.id in answer.option_ids),
                }
                for option in question.options
            ]
        elif question.type == "scale":
            values = [answer.number_value for answer in answers if answer.number_value is not None]
            stat.average = round(sum(values) / len(values), 2) if values else None
            stat.distribution = [{"name": str(value), "value": values.count(value)} for value in range(1 if question.scale_min is None else question.scale_min, (5 if question.scale_max is None else question.scale_max) + 1)]
        else:
            stat.text_answers = [answer.text_value for answer in answers if answer.text_value][:20]
        question_stats.append(stat)

    recent_rows = db.execute(
        select(SurveySession, Survey, TelegramUser)
        .join(Survey, Survey.id == SurveySession.survey_id)
        .join(TelegramUser, TelegramUser.id == SurveySession.respondent_id)
        .where(*session_filters)
        .order_by(SurveySession.started_at.desc())
        .limit(10)
    ).all()
    recent_sessions = [
        RecentSession(
            session_id=session.id,
            survey_title=survey.title,
            survey_title_en=survey.title_en or survey.title,
            survey_title_uk=survey.title_uk or survey.title,
            respondent=user.username or f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user.telegram_id),
            status=session.status,
            started_at=session.started_at,
            completed_at=session.completed_at,
        )
        for session, survey, user in recent_rows
    ]

    return AnalyticsOverview(
        total_respondents=total_respondents,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        unfinished_sessions=max(total_sessions - completed_sessions, 0),
        active_surveys=active_surveys,
        question_stats=question_stats,
        recent_sessions=recent_sessions,
        sessions_by_status=[{"name": status, "value": count} for status, count in status_rows],
    )
