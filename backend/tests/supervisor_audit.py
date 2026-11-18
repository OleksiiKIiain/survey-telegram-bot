"""Evidence for the controlled iteration; dedicated audit PostgreSQL only."""
import importlib.util
import io
import json
import platform
import time
import unittest
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import select
from app.api.v1.endpoints.translation import translate
from app.models.answer import Answer
from app.schemas.session import AnswerCreate, SessionCreate
from app.schemas.survey import QuestionUpdate
from app.schemas.translation import TranslationRequest
from app.core.config import settings
from app.services.analytics import build_analytics
from app.services.surveys import update_question
from app.api.v1.endpoints.public import save_answer, complete_session, start_session
from tests.test_integrity import IntegrityTests


class TranslationTests(unittest.TestCase):
    def setUp(self):
        provider = patch.object(settings, 'translation_provider', 'google')
        provider.start()
        self.addCleanup(provider.stop)

    def test_success_preserves_blank_lines(self):
        with patch('app.api.v1.endpoints.translation.GoogleTranslator') as service:
            service.return_value.translate.side_effect = ['Yes', 'No']
            result = translate(TranslationRequest(text='Так\n\nНі', source_lang='uk', target_lang='en'), None)
            self.assertEqual(result.translated_text, 'Yes\n\nNo')
            self.assertEqual(service.return_value.translate.call_count, 2)

    def test_upstream_failure_is_503(self):
        with patch('app.api.v1.endpoints.translation.GoogleTranslator') as service:
            service.return_value.translate.side_effect = RuntimeError('Controlled test outage')
            with self.assertRaises(HTTPException) as ctx:
                translate(TranslationRequest(text='Так', source_lang='uk', target_lang='en'), None)
            self.assertEqual(ctx.exception.status_code, 503)

    def test_unsupported_language_is_422(self):
        with self.assertRaises(HTTPException) as ctx:
            translate(TranslationRequest(text='Yes', source_lang='fr', target_lang='en'), None)
        self.assertEqual(ctx.exception.status_code, 422)


def controlled_edit():
    fixture = IntegrityTests()
    fixture.setUp()
    try:
        db, survey, qs = fixture.db, fixture.survey, fixture.questions
        # Five sessions from one synthetic respondent distinguish sessions from respondents.
        sessions = [fixture.session_id]
        for _ in range(4):
            sessions.append(start_session(SessionCreate(survey_id=survey.id, respondent_id=fixture.user.id), db).session.id)
        ratings = [5, 4, 5, 3, 4]
        singles = [0, 1, 0, 1, 0]
        multis = [[0, 1], [1], [0], [0, 1], [1]]
        for i, sid in enumerate(sessions):
            for q, value in zip(qs, [
                {'option_id': qs[0].options[singles[i]].id},
                {'option_ids': [qs[1].options[j].id for j in multis[i]]},
                {'text_value': 'Synthetic control answer'}, {'number_value': ratings[i]},
            ]):
                save_answer(sid, AnswerCreate(question_id=q.id, **value), db)
            complete_session(sid, db)

        def snapshot():
            stats = build_analytics(db, survey.id)
            answers = db.scalars(select(Answer).where(Answer.session_id.in_(sessions)).order_by(Answer.id)).all()
            return {
                'survey_id': survey.id, 'respondents': stats.total_respondents,
                'completed': stats.completed_sessions, 'answers': len(answers),
                'option_ids': [[o.id for o in q.options] for q in qs[:2]],
                'answer_links': [{'id': a.id, 'question_id': a.question_id, 'option_id': a.option_id, 'option_ids': a.option_ids} for a in answers],
                'frequencies': [[v['value'] for v in q.distribution] for q in stats.question_stats[:2]],
                'rating_average': stats.question_stats[3].average,
                'labels': [[v['name_en'] for v in q.distribution] for q in stats.question_stats[:2]],
            }
        before = snapshot()
        for q in qs[:2]:
            update_question(db, q, QuestionUpdate(text_en='Edited question', text_uk='Уточнене питання', options=[
                {'id': o.id, 'text': o.text, 'text_en': o.text + ' translated', 'text_uk': 'Уточнений варіант', 'position': i}
                for i, o in enumerate(q.options)]))
        db.commit()
        db.expire_all()
        after = snapshot()
        for key in ['option_ids', 'answer_links', 'frequencies', 'rating_average', 'completed', 'respondents', 'answers']:
            assert before[key] == after[key], key
        assert before['labels'] != after['labels']
        assert before['frequencies'] == [[3, 2], [3, 4]]
        assert before['rating_average'] == 4.2 and before['answers'] == 20
        return {'before': before, 'after': after, 'preserved': True,
                'boundary': 'Text/translation updates only; deletion and semantic changes are not versioned'}
    finally:
        fixture.tearDown()


def legacy_schema_failure():
    # This file is an unmodified snapshot of the schema at Git revision 7929c0c.
    source = Path('/tmp/legacy-survey-schema.py')
    spec = importlib.util.spec_from_file_location('legacy_survey_schema', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture = IntegrityTests()
    fixture.setUp()
    try:
        db, q = fixture.db, fixture.questions[0]
        old_ids = [o.id for o in q.options]
        save_answer(fixture.session_id, AnswerCreate(question_id=q.id, option_id=old_ids[0]), db)
        old_payload = module.QuestionUpdate(options=[{'id': o.id, 'text': o.text, 'text_en': 'Translated'} for o in q.options])
        normalized = old_payload.model_dump(exclude_unset=True)
        assert all('id' not in o for o in normalized['options'])
        update_question(db, q, QuestionUpdate(**normalized))
        db.commit()
        db.expire_all()
        answer = db.scalar(select(Answer).where(Answer.session_id == fixture.session_id))
        result = {'schema_revision': '7929c0c', 'old_ids': old_ids, 'new_ids': [o.id for o in q.options],
                  'id_lost_in_schema': True, 'answer_option_id_after': answer.option_id,
                  'counted_choices_after': sum(v['value'] for v in build_analytics(db, fixture.survey.id).question_stats[0].distribution)}
        assert result['answer_option_id_after'] is None and result['counted_choices_after'] == 0
        return result
    finally:
        fixture.tearDown()


def main():
    started = time.perf_counter()
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in [IntegrityTests, TranslationTests]])
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    print(log.getvalue())
    if not result.wasSuccessful():
        raise SystemExit(1)
    evidence = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Dedicated PostgreSQL integration tests plus mocked translation unit tests; no Telegram messages',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'python': platform.python_version(),
        'versions': {name: version(name) for name in ['fastapi', 'SQLAlchemy', 'pydantic', 'alembic', 'deep-translator', 'openpyxl']},
        'legacy_failure': legacy_schema_failure(), 'controlled_edit': controlled_edit(),
        'translation_success': 'mocked provider response, not an external translation quality test',
        'duration_seconds': round(time.perf_counter() - started, 3),
    }
    Path('/tmp/supervisor-audit.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(evidence, ensure_ascii=False))


if __name__ == '__main__':
    main()
