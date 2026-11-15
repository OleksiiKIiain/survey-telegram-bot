"""Negative controls ensure metadata checks detect artifact regressions."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.shared import Mm, Pt

spec = importlib.util.spec_from_file_location('artifact_checks', Path(__file__).with_name('check_artifacts.py'))
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class ArtifactChecksTest(unittest.TestCase):
    def test_citation_order_detects_inverted_first_occurrence(self):
        text = 'First [2], second [1].\n# СПИСОК ВИКОРИСТАНИХ ДЖЕРЕЛ\n1. A\n2. B\n# ДОДАТОК А'
        sources = [{'key': 'a', 'url': 'https://example.com/a'}, {'key': 'b', 'url': 'https://example.com/b'}]
        self.assertFalse(checks.validate_citations(text, sources)['citations_follow_first_occurrence'])

    def test_citation_order_accepts_repeated_references(self):
        text = 'First [1], repeat [1], second [2].\n# СПИСОК ВИКОРИСТАНИХ ДЖЕРЕЛ\n1. A\n2. B\n# ДОДАТОК А'
        sources = [{'key': 'a', 'url': 'https://example.com/a'}, {'key': 'b', 'url': 'https://example.com/b'}]
        self.assertTrue(checks.validate_citations(text, sources)['citations_follow_first_occurrence'])

    def test_docx_detects_wrong_margins_and_font(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.docx'
            doc = Document()
            doc.sections[0].left_margin = Mm(10)
            doc.styles['Normal'].font.name = 'Arial'
            doc.styles['Normal'].font.size = Pt(11)
            doc.save(path)
            report = checks.validate_docx(path)
            self.assertFalse(report['all_sections_required_margins'])
            self.assertFalse(report['normal_style_matches_requirements'])
            self.assertFalse(report['official_placeholders_present'])

    def test_bibliography_gap_is_detected(self):
        report = checks.validate_citations('Use [1].\n# СПИСОК ВИКОРИСТАНИХ ДЖЕРЕЛ\n1. A\n3. C', [])
        self.assertFalse(report['bibliography_consecutive'])


if __name__ == '__main__':
    unittest.main()
