from pydantic import BaseModel, Field


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1)
    source_lang: str
    target_lang: str


class TranslationResponse(BaseModel):
    translated_text: str
