from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import QuestionType, SurveyStatus


class OptionBase(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    text_en: str | None = None
    text_uk: str | None = None
    position: int = 0


class OptionCreate(OptionBase):
    pass


class OptionRead(OptionBase):
    id: int

    model_config = {"from_attributes": True}


class QuestionBase(BaseModel):
    text: str = Field(min_length=1)
    text_en: str | None = None
    text_uk: str | None = None
    type: QuestionType
    is_required: bool = True
    position: int = 0
    scale_min: int | None = None
    scale_max: int | None = None

    @model_validator(mode="after")
    def validate_scale(self):
        if self.type == QuestionType.scale:
            self.scale_min = self.scale_min or 1
            self.scale_max = self.scale_max or 5
            if self.scale_min >= self.scale_max:
                raise ValueError("scale_min must be less than scale_max")
        return self


class QuestionCreate(QuestionBase):
    options: list[OptionCreate] = []


class QuestionUpdate(BaseModel):
    text: str | None = None
    text_en: str | None = None
    text_uk: str | None = None
    type: QuestionType | None = None
    is_required: bool | None = None
    position: int | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    options: list[OptionCreate] | None = None


class QuestionRead(QuestionBase):
    id: int
    options: list[OptionRead] = []

    model_config = {"from_attributes": True}


class SurveyBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    title_en: str | None = None
    title_uk: str | None = None
    description: str | None = None
    description_en: str | None = None
    description_uk: str | None = None
    status: SurveyStatus = SurveyStatus.draft


class SurveyCreate(SurveyBase):
    questions: list[QuestionCreate] = []


class SurveyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    title_en: str | None = None
    title_uk: str | None = None
    description: str | None = None
    description_en: str | None = None
    description_uk: str | None = None
    status: SurveyStatus | None = None


class SurveyRead(SurveyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    questions_count: int = 0
    responses_count: int = 0

    model_config = {"from_attributes": True}


class SurveyDetail(SurveyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    questions: list[QuestionRead] = []

    model_config = {"from_attributes": True}
