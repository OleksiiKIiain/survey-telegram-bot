from fastapi import APIRouter, Depends, HTTPException
from deep_translator import GoogleTranslator

from app.api.deps import get_current_admin
from app.schemas.translation import TranslationRequest, TranslationResponse

router = APIRouter()

LANG_MAP = {
    "en": "english",
    "uk": "ukrainian",
}


@router.post("", response_model=TranslationResponse)
def translate(payload: TranslationRequest, _=Depends(get_current_admin)) -> TranslationResponse:
    source = LANG_MAP.get(payload.source_lang)
    target = LANG_MAP.get(payload.target_lang)
    if not source or not target:
        raise HTTPException(status_code=422, detail="Supported languages are en and uk")

    try:
        translated_lines: list[str] = []
        for line in payload.text.splitlines():
            if not line.strip():
                translated_lines.append("")
                continue
            translated_lines.append(GoogleTranslator(source=source, target=target).translate(line))
        return TranslationResponse(translated_text="\n".join(translated_lines))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Translation service is temporarily unavailable") from exc
