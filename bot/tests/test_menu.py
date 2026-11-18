"""Menu routing tests. Telegram and backend network calls are mocked."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

from bot.i18n import tr
from bot.keyboards import menu_keyboard
from bot.main import SurveyFlow, ask_current, choose_language, language_command, list_surveys, router, show_menu
from bot.menu import COMMANDS, commands_for, set_chat_language, setup_menu


def labels(keyboard):
    return [button.text for row in keyboard.keyboard for button in row]


class MenuTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = MemoryStorage()
        self.state = FSMContext(self.storage, StorageKey(bot_id=1, chat_id=1, user_id=1))
        self.message = SimpleNamespace(answer=AsyncMock(), from_user=SimpleNamespace(id=1))
        await self.state.set_state(SurveyFlow.answering)
        await self.state.update_data(session_id=9, index=0, lang='uk', survey={
            'title': 'Survey', 'title_uk': 'Опитування',
            'questions': [{'id': 1, 'type': 'free_text', 'text': 'Comment'}],
        })

    async def asyncTearDown(self):
        await self.storage.close()

    async def test_idle_and_active_keyboards_are_localized(self):
        for lang in ('uk', 'en'):
            idle = menu_keyboard(lang)
            active = menu_keyboard(lang, active=True)
            self.assertTrue(idle.is_persistent)
            self.assertTrue(idle.resize_keyboard)
            self.assertIn(tr(lang, 'menu_surveys'), labels(idle))
            self.assertIn(tr(lang, 'menu_language'), labels(idle))
            self.assertNotIn(tr(lang, 'menu_surveys'), labels(active))
            self.assertNotIn(tr(lang, 'menu_language'), labels(active))
            self.assertEqual(set(labels(active)), {
                tr(lang, 'menu_status'), tr(lang, 'menu_help'), tr(lang, 'menu_cancel'),
            })

    async def test_show_menu_keeps_current_question(self):
        previous = await self.state.get_data()
        await show_menu(self.message, self.state)
        self.assertEqual(await self.state.get_data(), previous)
        self.assertEqual(await self.state.get_state(), SurveyFlow.answering.state)
        keyboard = self.message.answer.call_args.kwargs['reply_markup']
        self.assertNotIn('Опитування', labels(keyboard))

    async def test_surveys_menu_cannot_replace_active_survey(self):
        with patch('bot.main.api.surveys', new_callable=AsyncMock) as request:
            await list_surveys(self.message, self.state)
            request.assert_not_awaited()
        self.assertEqual((await self.state.get_data())['session_id'], 9)
        self.assertIn('/cancel', self.message.answer.call_args.args[0])

    async def test_language_command_is_blocked_during_survey(self):
        await language_command(self.message, self.state)
        self.assertEqual((await self.state.get_data())['lang'], 'uk')
        self.assertIn('/cancel', self.message.answer.call_args.args[0])

    async def test_completion_restores_idle_menu(self):
        await self.state.update_data(index=1)
        with patch('bot.main.api.complete', new_callable=AsyncMock) as request:
            await ask_current(self.message, self.state)
            request.assert_awaited_once_with(9)
        self.assertEqual(await self.state.get_data(), {'lang': 'uk'})
        self.assertIsNone(await self.state.get_state())
        self.assertIn('Опитування', labels(self.message.answer.call_args.kwargs['reply_markup']))

    async def test_language_selection_updates_both_menus_without_help(self):
        await self.state.clear()
        bot = SimpleNamespace(set_my_commands=AsyncMock())
        self.message.chat = SimpleNamespace(id=1)
        callback = SimpleNamespace(data='lang:uk', bot=bot, message=self.message,
                                   from_user=self.message.from_user, answer=AsyncMock())
        with patch('bot.main.api.upsert_user', new_callable=AsyncMock), \
                patch('bot.main.api.surveys', new_callable=AsyncMock, return_value=[]):
            await choose_language(callback, self.state)
        self.assertEqual((await self.state.get_data())['lang'], 'uk')
        self.assertIn('Опитування', labels(self.message.answer.call_args_list[0].kwargs['reply_markup']))
        bot.set_my_commands.assert_awaited_once()
        self.assertEqual(bot.set_my_commands.call_args.kwargs['scope'].chat_id, 1)
        self.assertFalse(any('Як користуватися' in call.args[0] for call in self.message.answer.call_args_list))

    async def test_telegram_command_menu_registration(self):
        bot = SimpleNamespace(set_my_commands=AsyncMock(), set_chat_menu_button=AsyncMock())
        await setup_menu(bot)
        self.assertEqual(bot.set_my_commands.await_count, 3)
        self.assertEqual([item.command for item in commands_for('uk')], list(COMMANDS))
        self.assertNotEqual(commands_for('uk')[0].description, commands_for('en')[0].description)
        bot.set_chat_menu_button.assert_awaited_once()
        self.assertEqual(bot.set_chat_menu_button.call_args.kwargs['menu_button'].type, 'commands')
        await set_chat_language(bot, 123, 'en')
        self.assertEqual(bot.set_my_commands.call_args.kwargs['scope'].chat_id, 123)
        self.assertEqual(bot.set_my_commands.call_args.args[0], commands_for('en'))


class MenuDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = Bot(token='123456:local-unit-test-token')
        self.dispatcher = Dispatcher()
        # Reuse production registrations without attaching the global router to test dispatchers.
        self.dispatcher.message.handlers.extend(router.message.handlers)
        self.state = self.dispatcher.fsm.get_context(bot=self.bot, chat_id=42, user_id=42)
        await self.state.set_state(SurveyFlow.answering)
        await self.state.update_data(session_id=9, index=0, lang='uk', survey={
            'title': 'Survey', 'questions': [{'id': 1, 'text': 'Comment', 'type': 'free_text'}],
        })

    async def asyncTearDown(self):
        await self.dispatcher.storage.close()
        await self.bot.session.close()

    async def dispatch(self, text):
        message = Message(message_id=1, date=datetime.now(timezone.utc), text=text,
                          chat=Chat(id=42, type='private'),
                          from_user=User(id=42, first_name='Test', is_bot=False))
        return await self.dispatcher.feed_update(self.bot, Update(update_id=1, message=message))

    async def test_buttons_and_commands_never_become_text_answers(self):
        texts = ['Опитування', 'Surveys', 'Мова', 'Language', 'Мій прогрес', 'My progress',
                 'Довідка', 'Help', '/menu', '/surveys', '/status', '/help', '/language', '/unknown']
        with patch.object(AiohttpSession, 'make_request', new_callable=AsyncMock, return_value=True), \
                patch('bot.main.api.save_answer', new_callable=AsyncMock) as save:
            for text in texts:
                with self.subTest(text=text):
                    await self.dispatch(text)
                    self.assertEqual((await self.state.get_data())['index'], 0)
                    self.assertEqual((await self.state.get_data())['session_id'], 9)
            save.assert_not_awaited()

    async def test_cancel_button_cancels_instead_of_saving_answer(self):
        with patch.object(AiohttpSession, 'make_request', new_callable=AsyncMock, return_value=True), \
                patch('bot.main.api.save_answer', new_callable=AsyncMock) as save, \
                patch('bot.main.api.cancel', new_callable=AsyncMock) as cancel:
            await self.dispatch('Скасувати опитування')
            cancel.assert_awaited_once_with(9)
            save.assert_not_awaited()
        self.assertIsNone(await self.state.get_state())
        self.assertEqual(await self.state.get_data(), {'lang': 'uk'})

    async def test_regular_text_answer_still_completes_survey(self):
        with patch.object(AiohttpSession, 'make_request', new_callable=AsyncMock, return_value=True), \
                patch('bot.main.api.save_answer', new_callable=AsyncMock) as save, \
                patch('bot.main.api.complete', new_callable=AsyncMock) as complete:
            await self.dispatch('A normal survey comment')
            save.assert_awaited_once_with(9, {'text_value': 'A normal survey comment', 'question_id': 1})
            complete.assert_awaited_once_with(9)


if __name__ == '__main__':
    unittest.main(verbosity=2)
