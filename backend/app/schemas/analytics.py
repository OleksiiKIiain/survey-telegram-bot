from datetime import datetime
from typing import Any

from pydantic import BaseModel


class QuestionAnalytics(BaseModel):
    question_id: int
    question_text: str
    question_text_en: str | None = None
    question_text_uk: str | None = None
    question_type: str
    total_answers: int
    distribution: list[dict[str, Any]] = []
    average: float | None = None
    text_answers: list[str] = []


class RecentSession(BaseModel):
    session_id: int
    survey_title: str
    survey_title_en: str | None = None
    survey_title_uk: str | None = None
    respondent: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None


class AnalyticsOverview(BaseModel):
    total_respondents: int
    total_sessions: int
    completed_sessions: int
    unfinished_sessions: int
    active_surveys: int
    question_stats: list[QuestionAnalytics]
    recent_sessions: list[RecentSession]
    sessions_by_status: list[dict[str, int | str]]
