from enum import StrEnum


class SurveyStatus(StrEnum):
    draft = "draft"
    active = "active"
    closed = "closed"


class QuestionType(StrEnum):
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"
    free_text = "free_text"
    scale = "scale"


class SessionStatus(StrEnum):
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
