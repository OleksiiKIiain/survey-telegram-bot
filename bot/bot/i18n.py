from typing import Literal

Lang = Literal["en", "uk"]

TEXTS: dict[Lang, dict[str, str]] = {
    "en": {
        "choose_language": "Choose language:",
        "language_saved": "Language saved.",
        "welcome": "Welcome. Choose an available survey:",
        "help": (
            "How to use the bot:\n"
            "1. Send /start.\n"
            "2. Choose a language.\n"
            "3. Select one active survey.\n"
            "4. Answer questions step by step.\n"
            "5. Use /status to see progress.\n"
            "6. Use /cancel to stop the current survey."
        ),
        "active_session": "You are already taking a survey: {title}.\nFinish it first or send /cancel to stop it.",
        "cancelled": "Current survey was cancelled. Send /start to choose another survey.",
        "nothing_to_cancel": "There is no active survey to cancel.",
        "no_surveys": "No active surveys yet. Please try again later.",
        "not_in_survey": "You are not taking a survey now. Send /start to begin.",
        "current_status": "Current survey: {title}\nQuestion: {current}/{total}",
        "starting": "Starting: {title}",
        "question": "Question {current}/{total}{required}\n\n{text}",
        "multi_hint": "\n\nChoose one or more options and press Done.",
        "text_hint": "\n\nSend your answer as text.",
        "completed": "Thank you. The survey is complete and your answers are saved.",
        "use_buttons": "Please use the buttons below the question.",
        "empty_text": "Text answer cannot be empty.",
        "choose_one": "Choose at least one option",
        "done": "Done",
        "selected_mark": "* ",
    },
    "uk": {
        "choose_language": "Оберіть мову:",
        "language_saved": "Мову збережено.",
        "welcome": "Вітаю. Оберіть доступне опитування:",
        "help": (
            "Як користуватися ботом:\n"
            "1. Надішліть /start.\n"
            "2. Оберіть мову.\n"
            "3. Виберіть одне активне опитування.\n"
            "4. Відповідайте на питання покроково.\n"
            "5. Команда /status показує прогрес.\n"
            "6. Команда /cancel скасовує поточне проходження."
        ),
        "active_session": "Ви вже проходите опитування: {title}.\nСпочатку завершіть його або надішліть /cancel, щоб скасувати.",
        "cancelled": "Поточне проходження скасовано. Надішліть /start, щоб обрати інше опитування.",
        "nothing_to_cancel": "Зараз немає активного опитування для скасування.",
        "no_surveys": "Поки немає активних опитувань. Спробуйте пізніше.",
        "not_in_survey": "Зараз ви не проходите опитування. Надішліть /start, щоб почати.",
        "current_status": "Поточне опитування: {title}\nПитання: {current}/{total}",
        "starting": "Починаємо: {title}",
        "question": "Питання {current}/{total}{required}\n\n{text}",
        "multi_hint": "\n\nОберіть один або кілька варіантів і натисніть Готово.",
        "text_hint": "\n\nНадішліть відповідь текстом.",
        "completed": "Дякую! Опитування завершено, відповіді збережено.",
        "use_buttons": "Будь ласка, скористайтеся кнопками під питанням.",
        "empty_text": "Текстова відповідь не може бути порожньою.",
        "choose_one": "Оберіть хоча б один варіант",
        "done": "Готово",
        "selected_mark": "* ",
    },
}


def normalize_lang(value: str | None) -> Lang:
    return "uk" if value == "uk" else "en"


def tr(lang: str | None, key: str, **kwargs: object) -> str:
    selected = normalize_lang(lang)
    return TEXTS[selected][key].format(**kwargs)
