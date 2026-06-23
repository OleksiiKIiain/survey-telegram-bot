from datetime import datetime

from pydantic import BaseModel


class RespondentCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


class RespondentRead(RespondentCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    sessions_count: int = 0

    model_config = {"from_attributes": True}
