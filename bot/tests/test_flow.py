"""Handler unit tests with mocked network calls, NOT Telegram E2E."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from bot.main import SurveyFlow, cancel, choose_language, choose_survey, help_command, start
from bot.keyboards import localized, scale_keyboard


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage=MemoryStorage()
        self.state=FSMContext(self.storage,StorageKey(bot_id=1,chat_id=1,user_id=1))
        self.message=SimpleNamespace(answer=AsyncMock(),from_user=SimpleNamespace(id=1))
        self.callback=SimpleNamespace(data='survey:2',message=self.message,answer=AsyncMock(),from_user=SimpleNamespace(id=1))
        await self.state.set_state(SurveyFlow.answering)
        await self.state.update_data(session_id=9,lang='uk',survey={'title':'Survey','title_uk':'Опитування','questions':[]})

    async def asyncTearDown(self):
        await self.storage.close()

    async def test_start_does_not_clear_active_session(self):
        with patch('bot.main.api.upsert_user',new_callable=AsyncMock) as request:
            await start(self.message,self.state)
            request.assert_not_awaited()
        self.assertEqual((await self.state.get_data())['session_id'],9)
        self.assertIn('/cancel',self.message.answer.call_args.args[0])

    async def test_another_survey_is_blocked(self):
        with patch('bot.main.api.start_session',new_callable=AsyncMock) as request:
            await choose_survey(self.callback,self.state)
            request.assert_not_awaited()
        self.assertEqual((await self.state.get_data())['session_id'],9)

    async def test_old_language_button_is_blocked(self):
        self.callback.data='lang:en'
        with patch('bot.main.api.surveys',new_callable=AsyncMock) as request:
            await choose_language(self.callback,self.state)
            request.assert_not_awaited()
        self.assertEqual((await self.state.get_data())['lang'],'uk')

    async def test_cancel_updates_backend_before_clearing(self):
        with patch('bot.main.api.cancel',new_callable=AsyncMock) as request:
            await cancel(self.message,self.state)
            request.assert_awaited_once_with(9)
        self.assertEqual(await self.state.get_data(),{'lang':'uk'})

    async def test_help_is_explicit_and_localized(self):
        await help_command(self.message,self.state)
        self.assertIn('Як користуватися',self.message.answer.call_args.args[0])

    async def test_start_without_session_does_not_send_help(self):
        await self.state.clear()
        with patch('bot.main.api.upsert_user',new_callable=AsyncMock):
            await start(self.message,self.state)
        self.message.answer.assert_awaited_once()
        self.assertNotIn('Як користуватися',self.message.answer.call_args.args[0])

    async def test_localized_text(self):
        item={'text':'base','text_uk':'Так','text_en':'Yes'}
        self.assertEqual(localized(item,'text','uk'),'Так')
        self.assertEqual(localized(item,'text','en'),'Yes')

    async def test_scale_supports_zero(self):
        keyboard=scale_keyboard({'scale_min':0,'scale_max':5})
        self.assertEqual(keyboard.inline_keyboard[0][0].text,'0')


if __name__=='__main__':unittest.main(verbosity=2)
