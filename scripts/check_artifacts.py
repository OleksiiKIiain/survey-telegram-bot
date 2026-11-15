"""Verify structural evidence without implying a successful DOCX render."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pypdfium2 as pdfium
from docx import Document
from lxml import etree
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/thesis'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'


def validate_docx(path: Path) -> dict:
    doc = Document(path)
    with ZipFile(path) as archive:
        xml = etree.fromstring(archive.read('word/document.xml'))
    dimensions = []
    for section in xml.findall('.//w:sectPr', NS):
        size = section.find('w:pgSz', NS)
        margin = section.find('w:pgMar', NS)
        dimensions.append({
            'page': {key: int(size.get(W + key)) for key in ('w', 'h')},
            'margins': {key: int(margin.get(W + key)) for key in ('left', 'right', 'top', 'bottom')},
        })
    normal = doc.styles['Normal']
    font_size = normal.font.size.pt if normal.font.size else None
    content = '\n'.join(p.text for p in doc.paragraphs)
    return {
        'sections': dimensions,
        'all_sections_a4': all(abs(s['page']['w'] - 11906) <= 1 and abs(s['page']['h'] - 16838) <= 1 for s in dimensions),
        'all_sections_required_margins': all(s['margins'] == {'left': 1701, 'right': 567, 'top': 1134, 'bottom': 1134} for s in dimensions),
        'normal_font': normal.font.name,
        'normal_font_size_pt': font_size,
        'normal_line_spacing': normal.paragraph_format.line_spacing,
        'normal_style_matches_requirements': normal.font.name == 'Times New Roman' and font_size == 14 and normal.paragraph_format.line_spacing == 1.5,
        'has_toc_field': any('TOC ' in (node.text or '') for node in xml.findall('.//w:instrText', NS)),
        'has_page_field': any('PAGE' in part.blob.decode('utf-8', errors='ignore') for part in doc.part.package.parts if '/header' in str(part.partname)),
        'heading_one_starts_new_page': doc.styles['Heading 1'].paragraph_format.page_break_before is True,
        'official_placeholders_present': all(value in content for value in ('[ПІБ', '[Кафедра]', '[номер, дата]', '[дата]')),
        'table_count': len(doc.tables),
        'numbered_table_caption_count': sum(p.text.startswith('Таблиця ') for p in doc.paragraphs),
        'image_count': len(doc.inline_shapes),
        'numbered_figure_caption_count': sum(p.text.startswith('Рисунок ') for p in doc.paragraphs),
    }


def validate_citations(text: str, sources: list[dict]) -> dict:
    body, bibliography = text.split('# СПИСОК ВИКОРИСТАНИХ ДЖЕРЕЛ', 1)
    bibliography = bibliography.split('# ДОДАТОК', 1)[0]
    first_occurrences = list(dict.fromkeys(int(n) for n in re.findall(r'\[(\d+)\]', body)))
    entries = [int(n) for n in re.findall(r'(?m)^(\d+)\. ', bibliography)]
    expected = list(range(1, len(entries) + 1))
    return {
        'no_unresolved_citation_keys': '[@' not in text,
        'unique_source_keys': len({source['key'] for source in sources}) == len(sources),
        'unique_source_urls': len({source['url'] for source in sources}) == len(sources),
        'bibliography_count': len(entries),
        'citation_first_occurrence_order': first_occurrences,
        'citations_follow_first_occurrence': first_occurrences == expected,
        'bibliography_consecutive': entries == expected,
        'all_registered_sources_cited': len(entries) == len(sources),
    }


def main() -> None:
    summary = json.loads((OUT / 'build_summary.json').read_text(encoding='utf-8'))
    text = (OUT / 'survey_bot_thesis.md').read_text(encoding='utf-8')
    sources = json.loads((ROOT / 'docs/thesis/sources.json').read_text(encoding='utf-8'))
    docx = validate_docx(OUT / 'survey_bot_thesis.docx')
    citations = validate_citations(text, sources)
    reader = PdfReader(OUT / 'survey_bot_thesis.pdf')
    blank_pages = [i + 1 for i, page in enumerate(reader.pages) if len((page.extract_text() or '').strip()) < 20]
    missing_headings = [item for item in summary['headings'] if item['heading'] not in (reader.pages[item['page'] - 1].extract_text() or '').replace('\n', ' ')]
    missing_images = [filename for filename in re.findall(r'!\[.*?\]\((.*?)\)', text) if not (ROOT / 'docs/thesis' / filename).is_file()]
    overflow = []
    pdf = pdfium.PdfDocument(OUT / 'survey_bot_thesis.pdf')
    for p in range(len(pdf)):
        page = pdf[p]
        text_page = page.get_textpage()
        for i in range(text_page.count_chars()):
            if not text_page.get_text_range(i, 1).strip():
                continue
            left, bottom, right, top = text_page.get_charbox(i)
            if top < 780 and bottom > 45 and (left < 83 or right > 569):
                overflow.append({'page': p + 1, 'box': [round(v, 1) for v in (left, bottom, right, top)]})
        text_page.close()
        page.close()
    pdf.close()
    checks = {
        'at_least_70_pdf_pages_including_appendices': len(reader.pages) >= 70,
        'chapter_lengths': summary['chapter_pdf_pages'],
        'chapter_lengths_in_requested_ranges': all(low <= length <= 20 for low, length in zip((15, 15, 17), summary['chapter_pdf_pages'])),
        'pdf_pages_match_summary': len(reader.pages) == summary['pdf_pages'],
        'blank_pdf_pages': blank_pages,
        'heading_page_mismatches': missing_headings,
        'missing_source_images': missing_images,
        'text_outside_body_horizontal_bounds': overflow,
        'docx': docx,
        'citations': citations,
        'docx_rendered': summary['docx_rendered'],
        'google_docs_updated': summary['google_docs_updated'],
        'scope': 'Structural checks only. Not visual DOCX QA, university approval or plagiarism screening.',
        'table_caption_exception': 'The abbreviation glossary is a tabular list without a numbered table caption.',
    }
    required = [checks['at_least_70_pdf_pages_including_appendices'], checks['chapter_lengths_in_requested_ranges'], checks['pdf_pages_match_summary'],
                not blank_pages, not missing_headings, not missing_images, not overflow,
                docx['all_sections_a4'], docx['all_sections_required_margins'], docx['normal_style_matches_requirements'],
                docx['has_toc_field'], docx['has_page_field'], docx['heading_one_starts_new_page'], docx['official_placeholders_present'],
                docx['image_count'] == docx['numbered_figure_caption_count'],
                *[value for value in citations.values() if isinstance(value, bool)]]
    checks['structural_checks_passed'] = all(required)
    (OUT / 'artifact_checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    deliverables = ['survey_bot_thesis.docx', 'survey_bot_thesis.pdf', 'technical_report.docx', 'technical_report.pdf',
                    'compliance_report.docx', 'compliance_report.pdf', 'completion_report.md', 'build_summary.json', 'artifact_checks.json']
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'files': [{'path': name, 'bytes': (OUT / name).stat().st_size, 'sha256': hashlib.sha256((OUT / name).read_bytes()).hexdigest()} for name in deliverables],
        'limitations': summary['limitations'],
        'structural_checks_passed': checks['structural_checks_passed'],
    }
    (OUT / 'delivery_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if not checks['structural_checks_passed']:
        raise SystemExit('Artifact structural validation failed; see artifact_checks.json')


if __name__ == '__main__':
    main()
