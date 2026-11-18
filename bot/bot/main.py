import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import CallbackQuery, Message

from bot.api import api
from bot.config import settings
from bot.i18n import tr
from bot.keyboards import language_keyboard, localized, menu_keyboard, menu_labels, multiple_choice_keyboard, scale_keyboard, single_choice_keyboard, surveys_keyboard
from bot.menu import set_chat_language, setup_menu

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
        await state.update_data(lang=lang)
        await target.answer(tr(lang, "completed"), reply_markup=menu_keyboard(lang))
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
    if isinstance(event, CallbackQuery):
        await event.message.edit_reply_markup(reply_markup=None)
    await state.update_data(index=data["index"] + 1)
    await ask_current(event, state)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("session_id"):
        lang = data.get("lang")
        await message.answer(tr(lang, "active_session", title=localized(data["survey"], "title", lang)), reply_markup=menu_keyboard(lang, active=True))
        return
    await state.clear()
    await api.upsert_user(message.from_user)
    await message.answer(tr(None, "choose_language"), reply_markup=language_keyboard())


@router.message(Command("menu"))
async def show_menu(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    active = bool(data.get("session_id"))
    lang = data.get("lang")
    await message.answer(tr(lang, "menu_active" if active else "menu_title"), reply_markup=menu_keyboard(lang, active))


@router.message(Command("surveys"))
@router.message(F.text.in_(menu_labels("menu_surveys")))
async def list_surveys(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    if data.get("session_id"):
        await message.answer(tr(lang, "active_session", title=localized(data["survey"], "title", lang)), reply_markup=menu_keyboard(lang, active=True))
        return
    await api.upsert_user(message.from_user)
    surveys = await api.surveys()
    await message.answer(tr(lang, "menu_title"), reply_markup=menu_keyboard(lang))
    if not surveys:
        await message.answer(tr(lang, "no_surveys"))
        return
    await message.answer(tr(lang, "welcome"), reply_markup=surveys_keyboard(surveys, lang))


@router.message(Command("language"))
@router.message(F.text.in_(menu_labels("menu_language")))
async def language_command(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    if data.get("session_id"):
        await message.answer(tr(lang, "active_session", title=localized(data["survey"], "title", lang)), reply_markup=menu_keyboard(lang, active=True))
        return
    await message.answer(tr(lang, "choose_language"), reply_markup=language_keyboard())


@router.message(Command("help"))
@router.message(F.text.in_(menu_labels("menu_help")))
async def help_command(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    await message.answer(tr(lang, "help"), reply_markup=menu_keyboard(lang, active=bool(data.get("session_id"))))


@router.message(Command("cancel"))
@router.message(F.text.in_(menu_labels("menu_cancel")))
async def cancel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    if not data.get("session_id"):
        await message.answer(tr(lang, "nothing_to_cancel"), reply_markup=menu_keyboard(lang))
        return
    await api.cancel(data["session_id"])
    await state.clear()
    await state.update_data(lang=lang)
    await message.answer(tr(lang, "cancelled"), reply_markup=menu_keyboard(lang))


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("session_id"):
        await callback.answer()
        await callback.message.answer(tr(data.get("lang"), "active_session", title=localized(data["survey"], "title", data.get("lang"))))
        return
    lang = callback.data.split(":", 1)[1]
    if lang not in ("uk", "en"):
        await callback.answer()
        return
    await state.update_data(lang=lang)
    await set_chat_language(callback.bot, callback.message.chat.id, lang)
    await api.upsert_user(callback.from_user)
    surveys = await api.surveys()
    await callback.message.answer(tr(lang, "menu_title"), reply_markup=menu_keyboard(lang))
    if not surveys:
        await callback.message.answer(tr(lang, "no_surveys"))
        await callback.answer(tr(lang, "language_saved"))
        return
    await callback.answer(tr(lang, "language_saved"))
    await callback.message.answer(tr(lang, "welcome"), reply_markup=surveys_keyboard(surveys, lang))


@router.message(Command("status"))
@router.message(F.text.in_(menu_labels("menu_status")))
async def status(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    if not data.get("session_id"):
        await message.answer(tr(lang, "not_in_survey"), reply_markup=menu_keyboard(lang))
        return
    await message.answer(
        tr(
            lang,
            "current_status",
            title=localized(data["survey"], "title", lang),
            current=data["index"] + 1,
            total=len(data["survey"]["questions"]),
        ),
        reply_markup=menu_keyboard(lang, active=True),
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
    await callback.message.answer(tr(lang, "starting", title=localized(payload["survey"], "title", lang)), reply_markup=menu_keyboard(lang, active=True))
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


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang")
    await message.answer(tr(lang, "unknown_command"), reply_markup=menu_keyboard(lang, active=bool(data.get("session_id"))))


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


@router.message()
async def idle_message(message: Message, state: FSMContext) -> None:
    await show_menu(message, state)


async def main() -> None:
    if not settings.telegram_bot_token or settings.telegram_bot_token.startswith("put-your"):
        logging.warning("TELEGRAM_BOT_TOKEN is not configured. Bot service is idle.")
        while True:
            await asyncio.sleep(3600)
    bot = Bot(token=settings.telegram_bot_token)
    await setup_menu(bot)
    dp = Dispatcher(events_isolation=SimpleEventIsolation())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
