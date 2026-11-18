"""Integration tests against a dedicated, migrated PostgreSQL audit database."""
import unittest
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.models.answer import Answer
from app.models.respondent import TelegramUser
from app.schemas.survey import QuestionCreate, QuestionUpdate, SurveyCreate
from app.schemas.session import AnswerCreate, SessionCreate
from app.services.surveys import create_survey, update_question
from app.services.analytics import build_analytics
from app.api.deps import get_current_admin
from app.api.v1.endpoints.public import start_session, save_answer, complete_session
from app.api.v1.endpoints.export import export_rows, safe_cell


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        if not settings.database_url.rsplit('/', 1)[-1].startswith('survey_audit_'):
            raise RuntimeError('Tests require a dedicated survey_audit_* PostgreSQL database')
        self.db = SessionLocal()
        self.admin = self.db.scalar(select(Admin).limit(1))
        if not self.admin:
            self.admin = Admin(email='audit@example.com', full_name='Audit', hashed_password=get_password_hash('audit-test-password'))
            self.db.add(self.admin)
            self.db.flush()
        self.survey = create_survey(self.db, SurveyCreate(title='Audit', status='active', questions=[
            QuestionCreate(text='Choice', text_en='Choice', text_uk='Вибір', type='single_choice', options=[{'text': 'A'}, {'text': 'B'}]),
            QuestionCreate(text='Many', type='multiple_choice', options=[{'text': 'C'}, {'text': 'D'}]),
            QuestionCreate(text='Text', type='free_text'),
            QuestionCreate(text='Rating', type='scale', scale_min=0, scale_max=5),
        ]), self.admin.id)
        self.user = TelegramUser(telegram_id=900000000000 + self.survey.id, first_name='Audit')
        self.db.add(self.user)
        self.db.commit()
        self.payload = start_session(SessionCreate(survey_id=self.survey.id, respondent_id=self.user.id), self.db)
        self.session_id = self.payload.session.id
        self.questions = list(self.survey.questions)

    def tearDown(self):
        self.db.rollback()
        self.db.delete(self.survey)
        self.db.flush()
        self.db.delete(self.user)
        self.db.commit()
        self.db.close()

    def answer_all(self):
        q = self.questions
        values = [{'option_id': q[0].options[0].id}, {'option_ids': [q[1].options[0].id]}, {'text_value': '=1+1'}, {'number_value': 0}]
        for question, value in zip(q, values):
            save_answer(self.session_id, AnswerCreate(question_id=question.id, **value), self.db)

    def test_complete_requires_answers(self):
        with self.assertRaises(HTTPException) as ctx:
            complete_session(self.session_id, self.db)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_all_four_types_and_analytics(self):
        self.answer_all()
        result = complete_session(self.session_id, self.db)
        self.assertEqual(result.status, 'completed')
        stats = build_analytics(self.db, self.survey.id)
        self.assertEqual(stats.completed_sessions, 1)
        self.assertEqual(stats.total_respondents, 1)
        self.assertEqual(stats.question_stats[3].average, 0)
        self.assertEqual(stats.question_stats[0].distribution[0]['value'], 1)

    def test_translation_edit_preserves_option_identity(self):
        question = self.questions[0]
        original = question.options[0].id
        save_answer(self.session_id, AnswerCreate(question_id=question.id, option_id=original), self.db)
        payload = QuestionUpdate(text_en='Updated', text_uk='Оновлено', options=[
            {'id': item.id, 'text': item.text, 'text_en': item.text + ' EN', 'text_uk': 'Варіант'} for item in question.options])
        update_question(self.db, question, payload)
        self.db.commit()
        self.db.expire_all()
        answer = self.db.scalar(select(Answer).where(Answer.session_id == self.session_id))
        self.assertEqual(answer.option_id, original)
        self.assertEqual(self.db.get(type(question), question.id).text_en, 'Updated')

    def test_invalid_options_and_blank_text(self):
        for question, value in [(self.questions[0], {'option_id': -1}), (self.questions[1], {'option_ids': [-1]}),
                                (self.questions[2], {'text_value': '   '}), (self.questions[3], {'number_value': 6})]:
            with self.assertRaises(HTTPException):
                save_answer(self.session_id, AnswerCreate(question_id=question.id, **value), self.db)

    def test_duplicate_answer_is_replaced(self):
        q = self.questions[3]
        for number in [1, 2]:
            save_answer(self.session_id, AnswerCreate(question_id=q.id, number_value=number), self.db)
        answers = self.db.scalars(select(Answer).where(Answer.session_id == self.session_id, Answer.question_id == q.id)).all()
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0].number_value, 2)

    def test_export_formula_is_text(self):
        self.answer_all()
        rows = export_rows(self.db, self.survey.id)
        self.assertTrue(any(row[3] == "'=1+1" for row in rows[1:]))
        self.assertEqual(safe_cell('normal'), 'normal')

    def test_invalid_jwt_subject_returns_401(self):
        for token in [create_access_token('not-an-id'), create_access_token(self.admin.id, timedelta(seconds=-10))]:
            with self.assertRaises(HTTPException) as ctx:
                get_current_admin(self.db, token)
            self.assertEqual(ctx.exception.status_code, 401)

    def test_multiple_translation_and_reorder_preserve_counts(self):
        q = self.questions[1]
        ids = [option.id for option in q.options]
        save_answer(self.session_id, AnswerCreate(question_id=q.id, option_ids=ids), self.db)
        before = build_analytics(self.db, self.survey.id).question_stats[1]
        update_question(self.db, q, QuestionUpdate(options=[
            {'id': oid, 'text': 'Edited', 'text_uk': 'Переклад', 'text_en': 'Translation', 'position': i}
            for i, oid in enumerate(reversed(ids))]))
        self.db.commit()
        self.db.expire_all()
        after = build_analytics(self.db, self.survey.id).question_stats[1]
        answer = self.db.scalar(select(Answer).where(Answer.session_id == self.session_id))
        self.assertEqual(answer.option_ids, ids)
        self.assertEqual(before.total_answers, after.total_answers)
        self.assertEqual([v['value'] for v in after.distribution], [1, 1])
        self.assertEqual(set(option.id for option in self.db.get(type(q), q.id).options), set(ids))

    def test_empty_and_whitespace_text_are_rejected(self):
        for value in ['', ' ', '\n\t', None]:
            with self.subTest(value=value), self.assertRaises(HTTPException) as ctx:
                save_answer(self.session_id, AnswerCreate(question_id=self.questions[2].id, text_value=value), self.db)
            self.assertEqual(ctx.exception.status_code, 422)

    def test_empty_multiple_is_rejected(self):
        for value in [[], None]:
            with self.subTest(value=value), self.assertRaises(HTTPException) as ctx:
                save_answer(self.session_id, AnswerCreate(question_id=self.questions[1].id, option_ids=value), self.db)
            self.assertEqual(ctx.exception.status_code, 422)

    def test_scale_boundaries(self):
        q = self.questions[3]
        for value in [-1, 6, None]:
            with self.subTest(value=value), self.assertRaises(HTTPException) as ctx:
                save_answer(self.session_id, AnswerCreate(question_id=q.id, number_value=value), self.db)
            self.assertEqual(ctx.exception.status_code, 422)
        for value in [0, 5]:
            save_answer(self.session_id, AnswerCreate(question_id=q.id, number_value=value), self.db)
            self.assertEqual(build_analytics(self.db, self.survey.id).question_stats[3].average, value)

    def test_multiple_duplicates_are_normalized(self):
        q = self.questions[1]
        oid = q.options[0].id
        save_answer(self.session_id, AnswerCreate(question_id=q.id, option_ids=[oid, oid]), self.db)
        answer = self.db.scalar(select(Answer).where(Answer.session_id == self.session_id))
        self.assertEqual(answer.option_ids, [oid])
        self.assertEqual(build_analytics(self.db, self.survey.id).question_stats[1].distribution[0]['value'], 1)

    def test_completion_is_idempotent(self):
        self.answer_all()
        first = complete_session(self.session_id, self.db).completed_at
        second = complete_session(self.session_id, self.db).completed_at
        self.assertEqual(first, second)
        self.assertEqual(build_analytics(self.db, self.survey.id).completed_sessions, 1)

    def test_completed_answer_is_immutable(self):
        self.answer_all()
        complete_session(self.session_id, self.db)
        with self.assertRaises(HTTPException) as ctx:
            save_answer(self.session_id, AnswerCreate(question_id=self.questions[3].id, number_value=3), self.db)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_optional_unanswered_can_complete(self):
        for q in self.questions:
            q.is_required = False
        self.db.commit()
        self.assertEqual(complete_session(self.session_id, self.db).status, 'completed')

    def test_date_and_survey_filters(self):
        from datetime import datetime, timezone
        self.answer_all()
        stats = build_analytics(self.db, self.survey.id)
        self.assertEqual(stats.total_respondents, 1)
        future = build_analytics(self.db, self.survey.id, date_from=datetime.now(timezone.utc) + timedelta(days=1))
        self.assertEqual(future.total_sessions, 0)
        self.assertEqual(future.total_respondents, 0)
        self.assertTrue(all(q.total_answers == 0 for q in future.question_stats))


if __name__ == '__main__':
    unittest.main(verbosity=2)
