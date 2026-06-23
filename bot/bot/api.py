from typing import Any

import aiohttp

from bot.config import settings


class ApiClient:
    def __init__(self) -> None:
        self.base_url = settings.api_base_url.rstrip("/")

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, f"{self.base_url}{path}", **kwargs) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise RuntimeError(f"API error {response.status}: {text}")
                if response.content_type == "application/json":
                    return await response.json()
                return await response.text()

    async def upsert_user(self, user: Any) -> dict[str, Any]:
        return await self.request("POST", "/public/respondents", json={
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language_code": user.language_code,
        })

    async def surveys(self) -> list[dict[str, Any]]:
        return await self.request("GET", "/public/surveys")

    async def start_session(self, survey_id: int, respondent_id: int) -> dict[str, Any]:
        return await self.request("POST", "/public/sessions", json={"survey_id": survey_id, "respondent_id": respondent_id})

    async def save_answer(self, session_id: int, payload: dict[str, Any]) -> None:
        await self.request("POST", f"/public/sessions/{session_id}/answers", json=payload)

    async def complete(self, session_id: int) -> dict[str, Any]:
        return await self.request("POST", f"/public/sessions/{session_id}/complete")


api = ApiClient()
