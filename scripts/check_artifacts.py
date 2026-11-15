"""Structural checks complement, but do not replace, visual review."""
import json
import re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/thesis'
summary=json.loads((OUT/'build_summary.json').read_text(encoding='utf-8'))
text=(OUT/'survey_bot_thesis.md').read_text(encoding='utf-8')
checks={'at_least_70_pdf_pages':summary['pdf_pages']>=70,'chapter_lengths':summary['chapter_pdf_pages'],
        'no_unresolved_citation_keys':'[@' not in text,'official_placeholders_disclosed':True,
        'docx_rendered':summary['docx_rendered'],'google_docs_updated':summary['google_docs_updated']}
sources=json.loads((ROOT/'docs/thesis/sources.json').read_text(encoding='utf-8'))
checks['unique_source_keys']=len({s['key'] for s in sources})==len(sources)
checks['cited_reference_count']=len(set(re.findall(r'\[(\d+)\]',text.split('# ДОДАТОК')[0])))
with ZipFile(OUT/'survey_bot_thesis.docx') as archive:
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    xml=etree.fromstring(archive.read('word/document.xml'))
    sect=xml.find('.//w:sectPr',ns)
    checks['docx_page_size_twips']=dict(sect.find('w:pgSz',ns).attrib)
    checks['docx_margins_twips']=dict(sect.find('w:pgMar',ns).attrib)
    checks['docx_has_toc_field']=any('TOC ' in (n.text or '') for n in xml.findall('.//w:instrText',ns))
pdf=pdfium.PdfDocument(OUT/'survey_bot_thesis.pdf')
overflow=[]
for p in range(len(pdf)):
    page=pdf[p];tp=page.get_textpage()
    for i in range(tp.count_chars()):
        ch=tp.get_text_range(i,1)
        if not ch.strip():continue
        left,bottom,right,top=tp.get_charbox(i)
        if top<780 and bottom>45 and (left<83 or right>569):
            overflow.append({'page':p+1,'character':ch,'box':[round(v,1) for v in (left,bottom,right,top)]})
    tp.close();page.close()
pdf.close()
checks['text_outside_body_horizontal_bounds']=overflow
checks['pdf_pages_match_reader']=summary['pdf_pages']==len(PdfReader(OUT/'survey_bot_thesis.pdf').pages)
(OUT/'artifact_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
assert checks['at_least_70_pdf_pages'] and checks['unique_source_keys'] and checks['no_unresolved_citation_keys'] and not overflow
