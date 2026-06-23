from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SurveySession(Base):
    __tablename__ = "survey_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True, nullable=False)
    respondent_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    survey = relationship("Survey", back_populates="sessions")
    respondent = relationship("TelegramUser", back_populates="sessions")
    answers = relationship("Answer", back_populates="session", cascade="all, delete-orphan")
