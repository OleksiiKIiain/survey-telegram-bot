import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.api import api
from bot.config import settings
from bot.i18n import tr
from bot.keyboards import language_keyboard, localized, multiple_choice_keyboard, scale_keyboard, single_choice_keyboard, surveys_keyboard

logging.basicConfig(level=logging.INFO)
router = Router()


class SurveyFlow(StatesGroup):
    answering = State()


def question_text(question: dict, index: int, total: int, lang: str | None) -> str:
    required = "*" if question.get("is_required") else ""
    return tr(lang, "question", current=index + 1, total=total, required=required, text=localized(question, "text", lang))


async def ask_current(event: Message | CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    questions = data["survey"]["questions"]
    index = data["index"]
    target = event.message if isinstance(event, CallbackQuery) else event
    if index >= len(questions):
        await api.complete(data["session_id"])
        await state.clear()
        await target.answer(tr(lang, "completed"))
        return

    question = questions[index]
    text = question_text(question, index, len(questions), lang)
    if question["type"] == "single_choice":
        await target.answer(text, reply_markup=single_choice_keyboard(question, lang))
    elif question["type"] == "multiple_choice":
        await state.update_data(selected=[])
        await target.answer(text + tr(lang, "multi_hint"), reply_markup=multiple_choice_keyboard(question, [], tr(lang, "done"), tr(lang, "selected_mark"), lang))
    elif question["type"] == "scale":
        await target.answer(text, reply_markup=scale_keyboard(question))
    else:
        await target.answer(text + tr(lang, "text_hint"))


async def save_and_next(state: FSMContext, payload: dict, event: Message | CallbackQuery) -> None:
    data = await state.get_data()
    question = data["survey"]["questions"][data["index"]]
    payload["question_id"] = question["id"]
    await api.save_answer(data["session_id"], payload)
    await state.update_data(index=data["index"] + 1)
    await ask_current(event, state)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("session_id"):
        lang = data.get("lang")
        await message.answer(tr(lang, "active_session", title=localized(data["survey"], "title", lang)))
        return
    await state.clear()
    await api.upsert_user(message.from_user)
    await message.answer(tr(None, "choose_language"), reply_markup=language_keyboard())


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(tr(data.get("lang"), "help"))


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    if not data.get("session_id"):
        await message.answer(tr(lang, "nothing_to_cancel"))
        return
    await state.clear()
    await message.answer(tr(lang, "cancelled"))


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":", 1)[1]
    await state.update_data(lang=lang)
    await api.upsert_user(callback.from_user)
    surveys = await api.surveys()
    if not surveys:
        await callback.message.answer(tr(lang, "no_surveys"))
        await callback.answer(tr(lang, "language_saved"))
        return
    await callback.answer(tr(lang, "language_saved"))
    await callback.message.answer(tr(lang, "welcome"), reply_markup=surveys_keyboard(surveys, lang))


@router.message(Command("status"))
async def status(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    if not data.get("session_id"):
        await message.answer(tr(lang, "not_in_survey"))
        return
    await message.answer(
        tr(
            lang,
            "current_status",
            title=localized(data["survey"], "title", lang),
            current=data["index"] + 1,
            total=len(data["survey"]["questions"]),
        )
    )


@router.callback_query(F.data.startswith("survey:"))
async def choose_survey(callback: CallbackQuery, state: FSMContext) -> None:
    previous = await state.get_data()
    if previous.get("session_id"):
        await callback.answer()
        await callback.message.answer(tr(previous.get("lang"), "active_session", title=localized(previous["survey"], "title", previous.get("lang"))))
        return
    respondent = await api.upsert_user(callback.from_user)
    survey_id = int(callback.data.split(":", 1)[1])
    payload = await api.start_session(survey_id, respondent["id"])
    lang = previous.get("lang")
    await state.set_state(SurveyFlow.answering)
    await state.update_data(session_id=payload["session"]["id"], survey=payload["survey"], index=0, selected=[], lang=lang)
    await callback.answer()
    await callback.message.answer(tr(lang, "starting", title=localized(payload["survey"], "title", lang)))
    await ask_current(callback, state)


@router.callback_query(SurveyFlow.answering, F.data.startswith("single:"))
async def single(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await save_and_next(state, {"option_id": int(callback.data.split(":", 1)[1])}, callback)


@router.callback_query(SurveyFlow.answering, F.data.startswith("scale:"))
async def scale(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await save_and_next(state, {"number_value": int(callback.data.split(":", 1)[1])}, callback)


@router.callback_query(SurveyFlow.answering, F.data.startswith("multi:"))
async def multi_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected = list(data.get("selected", []))
    option_id = int(callback.data.split(":", 1)[1])
    if option_id in selected:
        selected.remove(option_id)
    else:
        selected.append(option_id)
    await state.update_data(selected=selected)
    question = data["survey"]["questions"][data["index"]]
    lang = data.get("lang")
    await callback.message.edit_reply_markup(reply_markup=multiple_choice_keyboard(question, selected, tr(lang, "done"), tr(lang, "selected_mark"), lang))
    await callback.answer()


@router.callback_query(SurveyFlow.answering, F.data == "multi_done")
async def multi_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected = data.get("selected", [])
    lang = data.get("lang")
    if not selected:
        await callback.answer(tr(lang, "choose_one"), show_alert=True)
        return
    await callback.answer()
    await save_and_next(state, {"option_ids": selected}, callback)


@router.message(SurveyFlow.answering)
async def text_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    question = data["survey"]["questions"][data["index"]]
    if question["type"] != "free_text":
        await message.answer(tr(lang, "use_buttons"))
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(tr(lang, "empty_text"))
        return
    await save_and_next(state, {"text_value": text}, message)


async def main() -> None:
    if not settings.telegram_bot_token or settings.telegram_bot_token.startswith("put-your"):
        logging.warning("TELEGRAM_BOT_TOKEN is not configured. Bot service is idle.")
        while True:
            await asyncio.sleep(3600)
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
