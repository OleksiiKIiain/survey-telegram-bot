"""Render every PDF page and record structural checks without claiming DOCX QA."""
import json
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/thesis'
QA=OUT/'qa'
QA.mkdir(exist_ok=True)
reports=[]
for filename in ['survey_bot_thesis.pdf','technical_report.pdf','compliance_report.pdf']:
    path=OUT/filename
    pdf=pdfium.PdfDocument(path)
    reader=PdfReader(path)
    directory=QA/path.stem
    directory.mkdir(exist_ok=True)
    pages=[]
    for index in range(len(pdf)):
        image=pdf[index].render(scale=1.35).to_pil().convert('RGB')
        image.save(directory/f'page-{index+1:03}.png')
        text=reader.pages[index].extract_text() or ''
        pages.append({'page':index+1,'characters':len(text),'has_replacement_glyph':'\ufffd' in text,'size_points':list(pdf[index].get_size())})
    for start in range(0,len(pdf),6):
        sheet=Image.new('RGB',(1200,1800),'#cfcfcf');draw=ImageDraw.Draw(sheet)
        for slot,index in enumerate(range(start,min(start+6,len(pdf)))):
            with Image.open(directory/f'page-{index+1:03}.png') as image:
                image.thumbnail((580,560));x=(slot%2)*600+(600-image.width)//2;y=(slot//2)*600+28
                sheet.paste(image,(x,y));draw.text(((slot%2)*600+10,(slot//2)*600+8),f'Page {index+1}',fill='black')
        sheet.save(directory/f'contact-{start//6+1:02}.png')
    reports.append({'file':filename,'page_count':len(pdf),'pages':pages})
    pdf.close()
(QA/'pdf_structure.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'file':r['file'],'pages':r['page_count'],'very_short_pages':[p['page'] for p in r['pages'] if p['characters']<180]} for r in reports],indent=2))
