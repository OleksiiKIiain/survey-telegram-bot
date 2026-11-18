from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, MenuButtonCommands

from bot.i18n import tr

COMMANDS = ("start", "menu", "surveys", "language", "status", "help", "cancel")


def commands_for(lang: str) -> list[BotCommand]:
    return [BotCommand(command=command, description=tr(lang, f"command_{command}")) for command in COMMANDS]


async def setup_menu(bot: Bot) -> None:
    await bot.set_my_commands(commands_for("uk"))
    for lang in ("uk", "en"):
        await bot.set_my_commands(commands_for(lang), language_code=lang)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def set_chat_language(bot: Bot, chat_id: int, lang: str) -> None:
    # A chat-specific scope follows the bot's selected language, not the Telegram client language.
    await bot.set_my_commands(commands_for(lang), scope=BotCommandScopeChat(chat_id=chat_id))
