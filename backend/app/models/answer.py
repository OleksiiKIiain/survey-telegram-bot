from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("survey_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False)
    option_id: Mapped[int | None] = mapped_column(ForeignKey("question_options.id", ondelete="SET NULL"), nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    number_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    option_ids: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("SurveySession", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    option = relationship("QuestionOption")
