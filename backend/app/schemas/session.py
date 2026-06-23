from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import SessionStatus
from app.schemas.survey import SurveyDetail


class SessionCreate(BaseModel):
    survey_id: int
    respondent_id: int


class SessionRead(BaseModel):
    id: int
    survey_id: int
    respondent_id: int
    status: SessionStatus
    started_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AnswerCreate(BaseModel):
    question_id: int
    option_id: int | None = None
    option_ids: list[int] | None = None
    text_value: str | None = None
    number_value: int | None = None


class AnswerRead(AnswerCreate):
    id: int
    session_id: int
    created_at: datetime
    question_text: str | None = None
    question_text_en: str | None = None
    question_text_uk: str | None = None
    option_text: str | None = None
    option_text_en: str | None = None
    option_text_uk: str | None = None
    option_texts: list[str] = []
    option_texts_en: list[str] = []
    option_texts_uk: list[str] = []

    model_config = {"from_attributes": True}


class PublicSessionPayload(BaseModel):
    session: SessionRead
    survey: SurveyDetail
    answered_question_ids: list[int]
