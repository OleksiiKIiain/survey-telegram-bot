from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.i18n import tr


def menu_keyboard(lang: str | None, active: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=tr(lang, "menu_status")), KeyboardButton(text=tr(lang, "menu_help"))]]
    if active:
        rows.append([KeyboardButton(text=tr(lang, "menu_cancel"))])
    else:
        rows.insert(0, [KeyboardButton(text=tr(lang, "menu_surveys"))])
        rows.append([KeyboardButton(text=tr(lang, "menu_language"))])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=tr(lang, "menu_placeholder"),
    )


def menu_labels(key: str) -> set[str]:
    return {tr("uk", key), tr("en", key)}


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="English", callback_data="lang:en"),
            InlineKeyboardButton(text="Українська", callback_data="lang:uk"),
        ]
    ])


def localized(item: dict, field: str, lang: str | None) -> str:
    if lang == "uk":
        return item.get(f"{field}_uk") or item.get(f"{field}_en") or item.get(field) or ""
    return item.get(f"{field}_en") or item.get(field) or item.get(f"{field}_uk") or ""


def surveys_keyboard(surveys: list[dict], lang: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=localized(item, "title", lang), callback_data=f"survey:{item['id']}")]
        for item in surveys
    ])


def single_choice_keyboard(question: dict, lang: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=localized(option, "text", lang), callback_data=f"single:{option['id']}")]
        for option in question.get("options", [])
    ])


def multiple_choice_keyboard(question: dict, selected: list[int], done_text: str = "Done", selected_mark: str = "* ", lang: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    for option in question.get("options", []):
        mark = selected_mark if option["id"] in selected else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{localized(option, 'text', lang)}", callback_data=f"multi:{option['id']}")])
    rows.append([InlineKeyboardButton(text=done_text, callback_data="multi_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def scale_keyboard(question: dict) -> InlineKeyboardMarkup:
    min_value = 1 if question.get("scale_min") is None else question["scale_min"]
    max_value = 5 if question.get("scale_max") is None else question["scale_max"]
    buttons = [InlineKeyboardButton(text=str(value), callback_data=f"scale:{value}") for value in range(min_value, max_value + 1)]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[index:index + 5] for index in range(0, len(buttons), 5)])
