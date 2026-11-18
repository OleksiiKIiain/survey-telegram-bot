import unittest
from unittest.mock import Mock, patch

import requests
from fastapi import HTTPException

from app.api.v1.endpoints.translation import translate, utf8_segments
from app.core.config import settings
from app.schemas.translation import TranslationRequest


class ProviderTests(unittest.TestCase):
    def setUp(self):
        provider = patch.object(settings, 'translation_provider', 'mymemory')
        provider.start()
        self.addCleanup(provider.stop)

    def payload(self, text='Yes\n\nNo'):
        return TranslationRequest(text=text, source_lang='en', target_lang='uk')

    def response(self, text, status=200):
        return Mock(json=Mock(return_value={'responseStatus': status, 'responseData': {'translatedText': text}}))

    def test_success_and_blank_lines(self):
        with patch('app.api.v1.endpoints.translation.requests.get', side_effect=[self.response('Так'), self.response('Ні')]) as get:
            self.assertEqual(translate(self.payload(), None).translated_text, 'Так\n\nНі')
            self.assertEqual(get.call_count, 2)
            self.assertEqual(get.call_args.kwargs['params']['langpair'], 'en|uk')
            self.assertEqual(get.call_args.kwargs['timeout'], (4, 12))

    def test_utf8_segments_keep_all_text_within_limit(self):
        text = 'Опитування та відповіді. ' * 90
        chunks = utf8_segments(text)
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(all(0 < len(c.encode('utf-8')) <= 500 for c in chunks))

    def test_quota_is_503(self):
        with patch('app.api.v1.endpoints.translation.requests.get', return_value=self.response('Quota exceeded', 429)):
            with self.assertRaises(HTTPException) as error:
                translate(self.payload('Yes'), None)
            self.assertEqual(error.exception.status_code, 503)

    def test_timeout_is_503(self):
        with patch('app.api.v1.endpoints.translation.requests.get', side_effect=requests.Timeout):
            with self.assertRaises(HTTPException) as error:
                translate(self.payload('Yes'), None)
            self.assertEqual(error.exception.status_code, 503)

    def test_empty_result_is_503(self):
        with patch('app.api.v1.endpoints.translation.requests.get', return_value=self.response('')):
            with self.assertRaises(HTTPException) as error:
                translate(self.payload('Yes'), None)
            self.assertEqual(error.exception.status_code, 503)

    def test_html_entities_are_decoded(self):
        with patch('app.api.v1.endpoints.translation.requests.get', return_value=self.response('Так &amp; ні')):
            self.assertEqual(translate(self.payload('Yes and no'), None).translated_text, 'Так & ні')

    def test_same_language_does_not_call_provider(self):
        with patch('app.api.v1.endpoints.translation.requests.get') as get:
            result = translate(TranslationRequest(text='Так', source_lang='uk', target_lang='uk'), None)
            self.assertEqual(result.translated_text, 'Так')
            get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
