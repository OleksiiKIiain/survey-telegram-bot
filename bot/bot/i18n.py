from typing import Literal

Lang = Literal["en", "uk"]

TEXTS: dict[Lang, dict[str, str]] = {
    "en": {
        "menu_title": "Main menu",
        "menu_active": "Survey menu",
        "menu_placeholder": "Choose an action",
        "menu_surveys": "Surveys",
        "menu_language": "Language",
        "menu_status": "My progress",
        "menu_help": "Help",
        "menu_cancel": "Cancel survey",
        "unknown_command": "Unknown command. Choose an action from the menu.",
        "command_start": "Start the bot",
        "command_menu": "Open the main menu",
        "command_surveys": "View available surveys",
        "command_language": "Choose your language",
        "command_status": "View survey progress",
        "command_help": "How to use the bot",
        "command_cancel": "Cancel the current survey",
        "choose_language": "Choose language:",
        "language_saved": "Language saved.",
        "welcome": "Welcome. Choose an available survey:",
        "help": (
            "How to use the bot:\n"
            "1. Press Start or send /start.\n"
            "2. Choose a language.\n"
            "3. Select one active survey.\n"
            "4. Answer questions step by step.\n"
            "5. Press My progress or use /status to see progress.\n"
            "6. Press Cancel survey or use /cancel to stop the survey.\n"
            "Open /menu to show the buttons again."
        ),
        "active_session": "You are already taking a survey: {title}.\nFinish it first or send /cancel to stop it.",
        "cancelled": "Current survey was cancelled. Press Surveys to choose another survey.",
        "nothing_to_cancel": "There is no active survey to cancel.",
        "no_surveys": "No active surveys yet. Please try again later.",
        "not_in_survey": "You are not taking a survey now. Press Surveys to begin.",
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
        "menu_title": "Головне меню",
        "menu_active": "Меню опитування",
        "menu_placeholder": "Оберіть дію",
        "menu_surveys": "Опитування",
        "menu_language": "Мова",
        "menu_status": "Мій прогрес",
        "menu_help": "Довідка",
        "menu_cancel": "Скасувати опитування",
        "unknown_command": "Невідома команда. Оберіть дію в меню.",
        "command_start": "Почати роботу з ботом",
        "command_menu": "Відкрити головне меню",
        "command_surveys": "Переглянути доступні опитування",
        "command_language": "Обрати мову",
        "command_status": "Переглянути прогрес опитування",
        "command_help": "Як користуватися ботом",
        "command_cancel": "Скасувати поточне проходження",
        "choose_language": "Оберіть мову:",
        "language_saved": "Мову збережено.",
        "welcome": "Вітаю. Оберіть доступне опитування:",
        "help": (
            "Як користуватися ботом:\n"
            "1. Натисніть Почати або надішліть /start.\n"
            "2. Оберіть мову.\n"
            "3. Виберіть одне активне опитування.\n"
            "4. Відповідайте на питання покроково.\n"
            "5. Кнопка Мій прогрес або /status показує прогрес.\n"
            "6. Кнопка Скасувати опитування або /cancel скасовує проходження.\n"
            "Команда /menu повторно відкриває кнопки меню."
        ),
        "active_session": "Ви вже проходите опитування: {title}.\nСпочатку завершіть його або надішліть /cancel, щоб скасувати.",
        "cancelled": "Поточне проходження скасовано. Натисніть Опитування, щоб обрати інше.",
        "nothing_to_cancel": "Зараз немає активного опитування для скасування.",
        "no_surveys": "Поки немає активних опитувань. Спробуйте пізніше.",
        "not_in_survey": "Зараз ви не проходите опитування. Натисніть Опитування, щоб почати.",
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
