from fastapi import APIRouter, Depends, HTTPException
from deep_translator import GoogleTranslator
import html
import requests

from app.api.deps import get_current_admin
from app.core.config import settings
from app.schemas.translation import TranslationRequest, TranslationResponse

router = APIRouter()

LANG_MAP = {
    "en": "english",
    "uk": "ukrainian",
}


def utf8_segments(text: str, limit: int = 500) -> list[str]:
    segments: list[str] = []
    while text:
        end = 0
        size = 0
        for char in text:
            width = len(char.encode("utf-8"))
            if size + width > limit:
                break
            size += width
            end += 1
        if end < len(text):
            boundary = text.rfind(" ", 0, end)
            if boundary > 0:
                end = boundary + 1
        segments.append(text[:end])
        text = text[end:]
    return segments


def mymemory_translate(text: str, source: str, target: str) -> str:
    results: list[str] = []
    for segment in utf8_segments(text):
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": segment, "langpair": f"{source}|{target}"},
            timeout=(4, 12),
        )
        response.raise_for_status()
        data = response.json()
        translated = data.get("responseData", {}).get("translatedText")
        if data.get("responseStatus") != 200 or not isinstance(translated, str) or not translated.strip():
            raise ValueError("Translation provider did not return a translation")
        results.append(html.unescape(translated).strip())
    return " ".join(results)


@router.post("", response_model=TranslationResponse)
def translate(payload: TranslationRequest, _=Depends(get_current_admin)) -> TranslationResponse:
    source = LANG_MAP.get(payload.source_lang)
    target = LANG_MAP.get(payload.target_lang)
    if not source or not target:
        raise HTTPException(status_code=422, detail="Supported languages are en and uk")
    if payload.source_lang == payload.target_lang:
        return TranslationResponse(translated_text=payload.text)

    try:
        translated_lines: list[str] = []
        for line in payload.text.splitlines():
            if not line.strip():
                translated_lines.append("")
                continue
            if settings.translation_provider == "google":
                translated_lines.append(GoogleTranslator(source=source, target=target).translate(line))
            else:
                translated_lines.append(mymemory_translate(line, payload.source_lang, payload.target_lang))
        return TranslationResponse(translated_text="\n".join(translated_lines))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Translation service is temporarily unavailable") from exc
