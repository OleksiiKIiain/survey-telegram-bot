"""Build the thesis and evidence reports from versioned Ukrainian sources."""
from __future__ import annotations

import ast
import hashlib
import html
import json
import re
import textwrap
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image as PILImage, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'docs' / 'thesis'
OUT = ROOT / 'output' / 'thesis'
FIG = SRC / 'figures'
FONTS = Path('C:/Windows/Fonts')
TITLE = 'Управління проєктом розробки системи автоматизованого опитування та аналізу даних засобами Telegram Bot та веб-технологій'
WIDTH = 170 * mm


def diagrams():
    FIG.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(FONTS / 'arial.ttf'), 30)
    small = ImageFont.truetype(str(FONTS / 'arial.ttf'), 26)
    def canvas():
        im = PILImage.new('RGB', (1800, 1100), 'white')
        return im, ImageDraw.Draw(im)
    def box(d, xy, title, details='', ellipse=False):
        (d.ellipse if ellipse else d.rectangle)(xy, outline='#222222', width=3)
        lines = [title] + details.split('\n') if details else [title]
        y = (xy[1]+xy[3])/2 - len(lines)*22
        for line in lines:
            d.text(((xy[0]+xy[2])/2, y), line, fill='black', font=font, anchor='mt')
            y += 45
    def arrow(d, a, b, label=''):
        import math
        d.line([a,b],fill='#333333',width=3)
        angle = math.atan2(b[1]-a[1], b[0]-a[0])
        pts = [b, (b[0]-18*math.cos(angle-0.45), b[1]-18*math.sin(angle-0.45)), (b[0]-18*math.cos(angle+0.45), b[1]-18*math.sin(angle+0.45))]
        d.polygon(pts, fill='#333333')
        if label:
            d.text(((a[0]+b[0])/2, (a[1]+b[1])/2-14), label, fill='black',font=small,anchor='mm',stroke_width=4,stroke_fill='white')
    im,d = canvas()
    box(d,(600,40,1200,190),'Система Survey Bot')
    for i,(title,details) in enumerate([('Підготувати анкету','Структура та дві мови'),('Провести опитування','Діалог і валідація'),('Зберегти відповіді','Сесії та цілісність'),('Проаналізувати','Частоти та шкали'),('Передати результати','CSV та XLSX')]):
        y=300+i*145
        box(d,(180,y,750,y+100),title,details)
        arrow(d,(900,190),(900,y+50))
        arrow(d,(900,y+50),(750,y+50))
    box(d,(1080,390,1720,660),'Керувальні умови','Статуси та права доступу\nПравила питань\nКритерії приймання')
    im.save(FIG/'functional.png')
    im,d=canvas()
    nodes=[((80,50,570,230),'admins','PK id; UNIQUE email'),((680,50,1170,230),'surveys','PK id; FK created_by_id'),((1280,50,1770,230),'questions','PK id; FK survey_id'),((1280,400,1770,580),'question_options','PK id; FK question_id'),((80,740,570,940),'telegram_users','PK id; UNIQUE telegram_id'),((680,740,1170,940),'survey_sessions','PK id; FK survey_id\nFK respondent_id'),((1280,740,1770,940),'answers','FK session_id, question_id\nFK option_id; JSONB option_ids'),((80,400,570,580),'audit_logs','FK admin_id; entity_id')]
    for xy,title,detail in nodes: box(d,xy,title,detail)
    for a,b,label in [((570,140),(680,140),'1:N'),((1170,140),(1280,140),'1:N'),((1520,230),(1520,400),'1:N'),((325,230),(325,400),'1:N'),((570,840),(680,840),'1:N'),((1170,840),(1280,840),'1:N'),((920,230),(920,740),'1:N'),((1770,230),(1770,740),'1:N'),((1520,580),(1520,740),'1:N')]: arrow(d,a,b,label)
    d.text((900,1030),'JSONB option_ids перевіряється API, не окремим FOREIGN KEY',font=small,fill='black',anchor='mm')
    im.save(FIG/'er.png')
    im,d=canvas()
    for xy,title,details in [((80,100,560,300),'Адміністратор','React у браузері'),((1240,100,1720,300),'Респондент','Telegram-клієнт'),((1240,450,1720,650),'Telegram Bot','aiogram; FSM; polling'),((620,450,1100,650),'Backend','FastAPI; JWT; валідація'),((620,850,1100,1040),'PostgreSQL','8 доменних таблиць'),((80,850,560,1040),'Зовнішній переклад','Мережевий сервіс')]: box(d,xy,title,details)
    for a,b,label in [((560,250),(620,450),'HTTP + JWT'),((1480,300),(1480,450),'Telegram API'),((1240,550),(1100,550),'HTTP + X-Bot-Key'),((860,650),(860,850),'SQLAlchemy'),((620,650),(560,850),'Текст анкети')]: arrow(d,a,b,label)
    im.save(FIG/'architecture.png')
    im,d=canvas()
    for i,title in enumerate(['draft','active','closed']): box(d,(100+i*580,100,500+i*580,280),title,ellipse=True)
    arrow(d,(500,190),(680,190),'публікація');arrow(d,(1080,190),(1260,190),'закриття')
    for xy,title in [((100,600,550,800),'in_progress'),((1150,430,1650,630),'completed'),((1150,820,1650,1020),'cancelled')]: box(d,xy,title,ellipse=True)
    arrow(d,(550,650),(1150,530),'усі обов’язкові відповіді');arrow(d,(550,750),(1150,920),'/cancel')
    d.text((900,370),'Стан анкети не тотожний стану сесії',font=font,fill='black',anchor='mm')
    im.save(FIG/'states.png')
    im,d=canvas()
    columns=[('Респондент',180),('Telegram Bot',650),('FastAPI',1110),('PostgreSQL',1570)]
    for title,x in columns:
        box(d,(x-150,30,x+150,140),title)
        d.line((x,140,x,1020),fill='gray',width=2)
    for y,a,b,label in [(230,180,650,'Вибір / текст'),(350,650,1110,'POST answer'),(470,1110,1570,'Перевірка і запис'),(590,1570,1110,'COMMIT'),(710,1110,650,'201 saved'),(830,650,180,'Наступне питання')]: arrow(d,(a,y),(b,y),label)
    d.text((900,990),'Перехід індексу лише після успішного запису',font=font,fill='black',anchor='mm')
    im.save(FIG/'sequence.png')
    im,d=canvas()
    for xy,title,detail in [((100,80,700,250),'Респондент','Почати; відповісти; скасувати'),((1100,80,1700,250),'Адміністратор','Створити; аналізувати; експортувати')]:box(d,xy,title,detail)
    for xy,title in [((100,450,700,650),'Пройти активну анкету'),((1100,450,1700,650),'Керувати анкетами'),((100,850,700,1030),'Перевірити відповіді'),((1100,850,1700,1030),'Переглянути аналітику')]:box(d,xy,title,ellipse=True)
    for a,b in [((400,250),(400,450)),((1400,250),(1400,450)),((700,550),(1100,940)),((400,650),(400,850)),((1400,650),(1400,850))]:arrow(d,a,b)
    im.save(FIG/'usecases.png')


def dynamic_appendix():
    parts=['# ДОДАТОК А ФУНКЦІОНАЛЬНІ ТА ІНФОРМАЦІЙНІ МОДЕЛІ',
           'Діаграми узгоджено з поточною структурою коду. Вони не описують неіснуючі мікросервіси або автоматичне масштабування.',
           '![Рисунок А.1 - Основні варіанти використання](figures/usecases.png)',
           '# ДОДАТОК Б СЛОВНИК ДАНИХ']
    descriptions={'admins':'Облікові записи адміністраторів. Пароль зберігається лише як хеш; email має унікальний індекс.',
                  'telegram_users':'Профіль респондента. Telegram ID є ідентифікатором платформи, а не доказом анонімності.',
                  'surveys':'Структурна одиниця анкети. Мовні поля є представленнями тієї самої сутності.',
                  'questions':'Питання анкети. position визначає порядок; тип керує допустимим полем відповіді.',
                  'question_options':'Варіант відповіді зі стабільним ключем. Редагування тексту не повинно замінювати ID.',
                  'survey_sessions':'Сесія проходження конкретним респондентом. started_at є основою часового відбору.',
                  'answers':'Первинні відповіді. JSONB-список множинного вибору перевіряє прикладний код.',
                  'audit_logs':'Записи адміністративних дій. Журнал не є повним event sourcing і не дозволяє автоматично відновлювати всі первинні значення.'}
    for source in sorted((ROOT/'backend/app/models').glob('*.py')):
        tree=ast.parse(source.read_text(encoding='utf-8'))
        for cls in [node for node in tree.body if isinstance(node,ast.ClassDef)]:
            table=next((n.value.value for n in cls.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__tablename__' for t in n.targets)),None)
            if not table: continue
            parts += [f'## Б.{len([p for p in parts if p.startswith("## Б.")])+1} Таблиця {table}', descriptions[table],f'Джерело визначення: backend/app/models/{source.name}. Наведені обмеження відтворюють ORM-модель; додаткові правила API описано в основному тексті.', '| Поле | Визначення та обмеження |','|---|---|']
            for node in cls.body:
                if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name):
                    value=ast.unparse(node.value).replace('mapped_column(', '').rstrip(')')
                    parts.append(f'| {node.target.id} | {value} |')
    parts += ['# ДОДАТОК В КОНТРАКТИ REST API',
              'Наведено інвентар маршрутів, отриманий зі схеми OpenAPI фактично запущеного сервера. Службові маршрути потребують X-Bot-Key, адміністративні - Bearer JWT. Наявність контракту не означає окремий E2E-тест кожної операції.']
    spec_path=SRC/'evidence/openapi.json'
    if spec_path.exists():
        spec=json.loads(spec_path.read_text(encoding='utf-8'))
        for url,methods in spec['paths'].items():
            for method,operation in methods.items():
                if method not in {'get','post','patch','delete','put'}: continue
                parts += [f'## {method.upper()} {url}',operation.get('summary','Операція API'), '| Властивість | Контракт |','|---|---|',f'| Операція | {operation.get("operationId","")} |', f'| Відповіді | {", ".join(operation.get("responses",{}))} |']
                parameters=operation.get('parameters',[])
                for p in parameters:
                    parts.append(f'| {p["name"]} | {p["in"]}; {"обов’язковий" if p.get("required") else "необов’язковий"}; {p.get("schema",{}).get("type","схема")} |')
                if 'requestBody' in operation:
                    schema=operation['requestBody'].get('content',{}).get('application/json',{}).get('schema',{})
                    ref=schema.get('$ref','').rsplit('/',1)[-1]
                    if ref:
                        model=spec.get('components',{}).get('schemas',{}).get(ref,{})
                        required=set(model.get('required',[]))
                        parts += [f'Тіло запиту відповідає схемі {ref}.', '| Поле запиту | Обов’язковість і тип |','|---|---|']
                        for key,value in model.get('properties',{}).items():
                            kind=value.get('type') or value.get('$ref','').rsplit('/',1)[-1] or 'nullable / складений тип'
                            parts.append(f'| {key} | {"Так" if key in required else "Ні"}; {kind} |')
    parts += ['# ДОДАТОК Г ПРОТОКОЛИ ПЕРЕВІРКИ',
              'Тести виконано в окремій PostgreSQL БД. Контрольні сутності не належать до реальних відповідей респондентів.',
              '## Г.1 HTTP-перевірки', '| Сценарій | Очікуваний результат | Фактичний результат |','|---|---|---|']
    report_path=SRC/'http_audit.json'
    if report_path.exists():
        report=json.loads(report_path.read_text(encoding='utf-8'))
        for row in report['results']:
            parts.append(f'| {row["test"]} | {row["expected"]} | {row["actual"]} |')
        parts += ['## Г.2 Короткий навантажувальний запуск', '| Показник | Виміряне значення |','|---|---|']
        for key,value in report['load'].items():parts.append(f'| {key} | {value} |')
        parts += ['Параметри цього запуску не є SLA. Для зіставлення версій потрібні повторення на однаковому наборі даних і контроль стану хоста.']
    parts += ['# ДОДАТОК Д ІНТЕРФЕЙС ТЕСТОВОГО СЕРЕДОВИЩА',
              'Зображення отримано з ізольованого frontend на порту 5174 та окремої тестової БД. Демонстраційні профілі не є результатом нового опитування людей.']
    for i,(filename,caption) in enumerate([('dashboard-uk.png','Панель українською мовою'),('dashboard-en.png','Панель англійською мовою'),('surveys-uk.png','Перелік анкет'),('responses-uk.png','Локалізовані питання та відповіді'),('analytics-uk.png','Діаграми контрольних відповідей'),('editor-saved.png','Підтвердження збереження у редакторі'),('analytics-mobile.png','Адаптивне представлення аналітики')],1):
        if (SRC/'evidence'/filename).exists(): parts += [f'![Рисунок Д.{i} - {caption}](evidence/{filename})']
    parts += ['# ДОДАТОК Е ФРАГМЕНТИ ПРОГРАМНОЇ РЕАЛІЗАЦІЇ',
              'Фрагменти відтворено з перевірюваної робочої копії. Вони ілюструють критичні контракти, а не замінюють повний репозиторій.']
    snippets=[('backend/app/api/deps.py','Е.1 Перевірка адміністративного та службового доступу',None),('backend/app/api/v1/endpoints/public.py','Е.2 Збереження відповіді','def save_answer'),('backend/app/services/surveys.py','Е.3 Оновлення варіантів зі збереженням ID','def update_question'),('backend/app/api/v1/endpoints/export.py','Е.4 Захист експортованих комірок','def safe_cell'),('backend/tests/test_integrity.py','Е.5 Регресія ідентичності після перекладу','    def test_translation_edit_preserves_option_identity')]
    for filename,heading,start in snippets:
        code=(ROOT/filename).read_text(encoding='utf-8')
        lines=code.splitlines()
        if start:
            begin=next(i for i,line in enumerate(lines) if line.startswith(start))
            function_name=start.strip().split()[1]
            function=next(node for node in ast.walk(ast.parse(code)) if isinstance(node,ast.FunctionDef) and node.name==function_name)
            end=function.end_lineno
            lines=lines[begin:end]
        parts += ['## '+heading,'Джерело: '+filename,'```python','\n'.join(lines),'```']
    text='\n\n'.join(parts)
    (SRC/'06-appendices.generated.md').write_text(text,encoding='utf-8')
    return text


def parse(text):
    lines=text.splitlines(); i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('```'):
            block=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
            yield 'code','\n'.join(block);i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines):
                if not lines[i].strip() and i+1<len(lines) and lines[i+1].strip().startswith('|'):
                    i+=1
                    continue
                if not lines[i].strip().startswith('|'):
                    break
                cells=[cell.strip() for cell in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',cell) for cell in cells): rows.append(cells)
                i+=1
            if rows:yield 'table',rows
            continue
        match=re.match(r'!\[(.*?)\]\((.*?)\)',line)
        if match:yield 'image',match.groups();i+=1;continue
        if line.startswith('#'):
            n=len(line)-len(line.lstrip('#'));yield 'h'+str(n),line[n:].strip();i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','![')):
            paragraph.append(lines[i].strip());i+=1
        yield 'p',' '.join(paragraph)


def field(paragraph,instruction,text=''):
    begin=OxmlElement('w:fldChar');begin.set(qn('w:fldCharType'),'begin')
    code=OxmlElement('w:instrText');code.set(qn('xml:space'),'preserve');code.text=instruction
    separate=OxmlElement('w:fldChar');separate.set(qn('w:fldCharType'),'separate')
    end=OxmlElement('w:fldChar');end.set(qn('w:fldCharType'),'end')
    for item in [begin,code,separate]:paragraph.add_run()._r.append(item)
    if text:paragraph.add_run(text)
    paragraph.add_run()._r.append(end)


def make_docx(tokens,target,cover=False):
    doc=Document();section=doc.sections[0]
    section.page_width=Mm(210);section.page_height=Mm(297)
    section.left_margin=Mm(30);section.right_margin=Mm(10);section.top_margin=Mm(20);section.bottom_margin=Mm(20)
    section.header_distance=Mm(10);section.footer_distance=Mm(10)
    for name in ['Normal','Title','Heading 1','Heading 2','Heading 3','Caption']:
        style=doc.styles[name];style.font.name='Times New Roman';style.font.size=Pt(14);style.font.color.rgb=RGBColor(0,0,0)
        style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Times New Roman')
        style.paragraph_format.line_spacing=1.5;style.paragraph_format.space_after=Pt(0)
    normal=doc.styles['Normal'].paragraph_format
    normal.first_line_indent=Mm(12.5);normal.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    for name in ['Heading 1','Heading 2','Heading 3']:
        pf=doc.styles[name].paragraph_format;pf.first_line_indent=Mm(0);pf.space_before=Pt(12);pf.space_after=Pt(8);pf.keep_with_next=True
    doc.styles['Heading 1'].paragraph_format.page_break_before=True
    doc.styles['Heading 1'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    section.different_first_page_header_footer=True
    p=section.header.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;p.paragraph_format.first_line_indent=Mm(0);field(p,'PAGE')
    update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');doc.settings.element.append(update)
    if cover:
        for text in ['МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ','НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ «ОСТРОЗЬКА АКАДЕМІЯ»','[Інститут / факультет]','[Кафедра]','', 'КВАЛІФІКАЦІЙНА РОБОТА','на здобуття освітнього ступеня магістра',TITLE,'','Спеціальність F3 «Комп’ютерні науки»','ОПП «Управління ІТ-проєктами»','','Здобувач: [ПІБ, група]','Керівник: [ПІБ, ступінь, звання]','Рецензент: [ПІБ, ступінь, звання]','','Острог 2026']:
            p=doc.add_paragraph(text,style='Title' if text==TITLE else 'Normal');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Mm(0)
        doc.add_paragraph('ЗАВДАННЯ НА КВАЛІФІКАЦІЙНУ РОБОТУ',style='Heading 1')
        for text in ['Здобувач: [ПІБ]. Спеціальність F3 «Комп’ютерні науки». ОПП «Управління ІТ-проєктами».', 'Тема: '+TITLE+'.','Керівник: [ПІБ]. Наказ про затвердження: [номер, дата]. Строк подання: [дата].','Вихідні дані: репозиторій Survey Bot, вимоги до системи, результати аудиту та експериментального тестування.','Зміст завдання: аналіз предметної області; моделювання; планування; дослідження реалізації; виправлення дефектів; перевірки; оформлення результатів.','Графічні матеріали: функціональна схема, ER-модель, діаграми станів, компонентів і послідовності, зображення інтерфейсу.','Календарний план і офіційні реквізити підлягають погодженню з кафедрою.','Підпис здобувача: ______________. Підпис керівника: ______________.']:
            doc.add_paragraph(text)
        doc.add_paragraph('ЗМІСТ',style='Heading 1');field(doc.add_paragraph(),'TOC \\o "1-3" \\h \\z \\u','[Автоматичне поле змісту]')
    first=True
    for kind,value in tokens:
        if kind.startswith('h'):
            p=doc.add_paragraph(value,style='Heading '+kind[1:]);
            if first and not cover:p.paragraph_format.page_break_before=False
        elif kind=='p':
            p=doc.add_paragraph(value)
            if value.startswith('Таблиця '):p.paragraph_format.keep_with_next=True
        elif kind=='code':
            for line in value.splitlines():
                for wrapped in textwrap.wrap(line,90,replace_whitespace=False,drop_whitespace=False) or ['']:
                    p=doc.add_paragraph();p.paragraph_format.first_line_indent=Mm(0);p.paragraph_format.line_spacing=1
                    r=p.add_run(wrapped);r.font.name='Courier New';r.font.size=Pt(9)
        elif kind=='table':
            t=doc.add_table(rows=1,cols=len(value[0]));t.style='Table Grid';t.autofit=False
            for i,row in enumerate(value):
                cells=t.rows[0].cells if i==0 else t.add_row().cells
                for j,cell in enumerate(cells):
                    cell.text=row[j] if j<len(row) else ''
                    for p in cell.paragraphs:
                        p.paragraph_format.first_line_indent=Mm(0);p.paragraph_format.line_spacing=1.0
                        for run in p.runs:run.font.size=Pt(12);run.bold=i==0
                    if i==0:
                        shading=OxmlElement('w:shd');shading.set(qn('w:fill'),'E8E8E8');cell._tc.get_or_add_tcPr().append(shading)
                if i==0:
                    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
            doc.add_paragraph()
        elif kind=='image':
            caption,filename=value;image=SRC/filename
            if image.exists():
                with PILImage.open(image) as im:w,h=im.size
                scale=min(170/w,210/h)
                p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Mm(0);p.paragraph_format.keep_with_next=True
                p.add_run().add_picture(str(image),width=Mm(w*scale))
                p=doc.add_paragraph(caption,style='Caption');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        first=False
    doc.core_properties.title=TITLE if cover else target.stem;doc.core_properties.language='uk-UA'
    for style in doc.styles:
        for border in style.element.findall('.//'+qn('w:pBdr')):
            border.getparent().remove(border)
    doc.save(target)


class ThesisPDF(BaseDocTemplate):
    def __init__(self,filename):
        super().__init__(str(filename),pagesize=(210*mm,297*mm),leftMargin=30*mm,rightMargin=10*mm,topMargin=20*mm,bottomMargin=20*mm,title=TITLE,author='')
        self.addPageTemplates(PageTemplate(id='main',frames=Frame(30*mm,20*mm,WIDTH,257*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),onPage=self.page_header))
        self.heading_pages=[]
    def page_header(self,c,doc):
        if doc.page>1:
            c.saveState();c.setFont('TNR',12);c.drawRightString(200*mm,282*mm,str(doc.page));c.restoreState()
    def beforeDocument(self):self.heading_pages=[]
    def afterFlowable(self,flow):
        if isinstance(flow,Paragraph) and flow.style.name in ('h1','h2'):
            text=flow.getPlainText();level=0 if flow.style.name=='h1' else 1
            if text in (TITLE,'ЗМІСТ'):
                return
            key='heading-'+hashlib.sha1(text.encode()).hexdigest()[:12]
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(text,key,level=level,closed=False)
            self.notify('TOCEntry',(level,text,self.page,key));self.heading_pages.append({'heading':text,'page':self.page})


def make_pdf(tokens,target,cover=False):
    styles={
        'p':ParagraphStyle('p',fontName='TNR',fontSize=14,leading=21,alignment=TA_JUSTIFY,firstLineIndent=12.5*mm,spaceAfter=0,splitLongWords=True),
        'h1':ParagraphStyle('h1',fontName='TNR-Bold',fontSize=14,leading=21,alignment=TA_CENTER,spaceAfter=14,keepWithNext=True),
        'h2':ParagraphStyle('h2',fontName='TNR-Bold',fontSize=14,leading=21,spaceBefore=12,spaceAfter=8,keepWithNext=True),
        'h3':ParagraphStyle('h3',fontName='TNR-Bold',fontSize=14,leading=21,spaceBefore=10,spaceAfter=6,keepWithNext=True),
        'cell':ParagraphStyle('cell',fontName='TNR',fontSize=12,leading=15,alignment=TA_LEFT,wordWrap='LTR'),
        'caption':ParagraphStyle('caption',fontName='TNR',fontSize=12,leading=16,alignment=TA_CENTER,spaceAfter=10),
        'cover':ParagraphStyle('cover',fontName='TNR',fontSize=14,leading=22,alignment=TA_CENTER,spaceAfter=8),
        'code':ParagraphStyle('code',fontName='Code',fontSize=8,leading=10,spaceAfter=0),
        'table_caption':ParagraphStyle('table_caption',fontName='TNR',fontSize=14,leading=21,spaceBefore=8,spaceAfter=4),
    }
    story=[]
    def para(text,style='p'):return Paragraph(html.escape(text),styles[style])
    if cover:
        for text in ['МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ','НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ «ОСТРОЗЬКА АКАДЕМІЯ»','[Інститут / факультет]','[Кафедра]']:
            story.append(para(text,'cover'))
        story.append(Spacer(1,25*mm));story.append(para('КВАЛІФІКАЦІЙНА РОБОТА','cover'));story.append(para('на здобуття освітнього ступеня магістра','cover'));story.append(para(TITLE,'h1'))
        for text in ['Спеціальність F3 «Комп’ютерні науки»','ОПП «Управління ІТ-проєктами»','Здобувач: [ПІБ, група]','Керівник: [ПІБ, ступінь, звання]','Рецензент: [ПІБ, ступінь, звання]','Острог 2026']:story.append(para(text,'cover'))
        story.append(PageBreak());story.append(para('ЗАВДАННЯ НА КВАЛІФІКАЦІЙНУ РОБОТУ','h1'))
        for text in ['Здобувач: [ПІБ]. Спеціальність F3 «Комп’ютерні науки». ОПП «Управління ІТ-проєктами».','Тема: '+TITLE+'.','Керівник: [ПІБ]. Наказ: [номер, дата]. Строк подання: [дата].','Вихідні дані: репозиторій Survey Bot, вимоги до системи та результати перевірок.','Завдання: аналіз предметної області, моделювання, планування, дослідження коду, виправлення дефектів і тестування.','Графічні матеріали: функціональна, ER та UML-моделі, архітектура, зображення інтерфейсу.','Календарний план і офіційні реквізити підлягають погодженню.','Підпис здобувача: ______________. Підпис керівника: ______________.']:story.append(para(text))
        story.append(PageBreak());story.append(para('ЗМІСТ','h1'))
        toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC0',fontName='TNR',fontSize=12,leading=16,spaceBefore=4),ParagraphStyle('TOC1',fontName='TNR',fontSize=12,leading=16,leftIndent=12)]
        story.append(toc)
    first=True
    pending_caption=None
    for kind,value in tokens:
        if kind.startswith('h'):
            if kind=='h1' and (not first or cover):story.append(PageBreak())
            story.append(para(value,kind))
        elif kind=='p':
            if value.startswith('Таблиця '):pending_caption=value
            else:story.append(para(value))
        elif kind=='table':
            cols=len(value[0]);widths=[WIDTH/cols]*cols
            if cols==2:widths=[WIDTH*0.3,WIDTH*0.7]
            rows=[[para(cell,'cell') for cell in row] for row in value]
            t=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#D9D9D9')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8E8E8')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]))
            if pending_caption:
                caption=para(pending_caption,'table_caption')
                first_rows=Table(rows[:2],colWidths=widths)
                first_rows.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
                minimum=caption.wrap(WIDTH,10000)[1]+first_rows.wrap(WIDTH,10000)[1]+20
                story.extend([CondPageBreak(minimum),caption])
                pending_caption=None
            story.extend([t,Spacer(1,10)])
        elif kind=='image':
            caption,filename=value;image=SRC/filename
            if image.exists():
                with PILImage.open(image) as im:w,h=im.size
                scale=min(WIDTH/w,200*mm/h)
                story.append(KeepTogether([Image(str(image),width=w*scale,height=h*scale),para(caption,'caption')]))
        elif kind=='code':
            wrapped_lines=[]
            for line in value.splitlines():
                wrapped_lines.extend(textwrap.wrap(line,100,replace_whitespace=False,drop_whitespace=False) or [''])
            block=Preformatted('\n'.join(wrapped_lines),styles['code'])
            story.append(KeepTogether([block]) if len(wrapped_lines)<=55 else block)
        first=False
    pdf=ThesisPDF(target);pdf.multiBuild(story,maxPasses=5)
    return pdf.heading_pages


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('TNR',str(FONTS/'times.ttf')))
    pdfmetrics.registerFont(TTFont('TNR-Bold',str(FONTS/'timesbd.ttf')))
    pdfmetrics.registerFont(TTFont('Code',str(FONTS/'consola.ttf')))
    diagrams();dynamic_appendix()
    sources=json.loads((SRC/'sources.json').read_text(encoding='utf-8'));by_key={s['key']:s for s in sources};order=[]
    def cite(match):
        key=match.group(1)
        if key not in order:order.append(key)
        if key not in by_key:raise ValueError(key)
        return '['+str(order.index(key)+1)+']'
    main_parts=[]
    for name in ['01-introduction.md','02-chapter-one.md','03-chapter-two.md','04-chapter-three.md','05-conclusions.md']:
        main_parts.append(re.sub(r'\[@([a-z]+)\]',cite,(SRC/name).read_text(encoding='utf-8')))
    refs=['# СПИСОК ВИКОРИСТАНИХ ДЖЕРЕЛ']
    for i,key in enumerate(order,1):
        s=by_key[key];refs.append(f'{i}. {s["author"]}. {s["title"]}. {s["year"]}. URL: {s["url"]} (дата звернення: 15.11.2026).')
    text='\n\n'.join(main_parts+['\n\n'.join(refs),(SRC/'06-appendices.generated.md').read_text(encoding='utf-8')])
    (OUT/'survey_bot_thesis.md').write_text(text,encoding='utf-8')
    tokens=list(parse(text))
    numbered=[];appendix=None;table_index=0;last_paragraph=''
    for kind,value in tokens:
        if kind=='h1':
            match=re.match(r'ДОДАТОК ([А-ЯІЇЄ]) ',value)
            appendix=match.group(1) if match else None
            table_index=0
        if kind=='table' and appendix and not last_paragraph.startswith('Таблиця '):
            table_index+=1
            numbered.append(('p',f'Таблиця {appendix}.{table_index} - Довідкові дані поточного підрозділу'))
        numbered.append((kind,value))
        last_paragraph=value if kind=='p' else ''
    tokens=numbered
    make_docx(tokens,OUT/'survey_bot_thesis.docx',cover=True)
    pages=make_pdf(tokens,OUT/'survey_bot_thesis.pdf',cover=True)
    starts=[next(item['page'] for item in pages if item['heading'].startswith('РОЗДІЛ '+str(i))) for i in (1,2,3)]
    conclusion=next(item['page'] for item in pages if item['heading']=='ВИСНОВКИ')
    chapter_lengths=[starts[1]-starts[0],starts[2]-starts[1],conclusion-starts[2]]
    reports={}
    for source,stem in [('technical-report.md','technical_report'),('compliance-report.md','compliance_report')]:
        if (SRC/source).exists():
            report_text=(SRC/source).read_text(encoding='utf-8').replace('{{TOTAL_PAGES}}',str(len(PdfReader(OUT/'survey_bot_thesis.pdf').pages)))
            for i,length in enumerate(chapter_lengths,1):report_text=report_text.replace('{{CH'+str(i)+'}}',str(length))
            report_tokens=list(parse(report_text))
            make_docx(report_tokens,OUT/(stem+'.docx'));make_pdf(report_tokens,OUT/(stem+'.pdf'))
            reports[stem]=len(PdfReader(OUT/(stem+'.pdf')).pages)
    summary={'pdf_pages':len(PdfReader(OUT/'survey_bot_thesis.pdf').pages),'chapter_pdf_pages':chapter_lengths,'headings':pages,'reports':reports,'words':len(re.findall(r'\S+',text)),
             'docx_rendered':False,'pdf_generation':'ReportLab from the same structured source; not a DOCX conversion','google_docs_updated':False,
             'limitations':['Official methodology and Appendix E inaccessible','Official personal details unconfirmed','DOCX rendering and automatic TOC refresh require a compatible renderer','No completed real Telegram client E2E','External translation returned 503']}
    (OUT/'build_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    if (SRC/'completion-report.md').exists():
        completion=(SRC/'completion-report.md').read_text(encoding='utf-8').replace('{{TOTAL_PAGES}}',str(summary['pdf_pages']))
        for i,length in enumerate(chapter_lengths,1):completion=completion.replace('{{CH'+str(i)+'}}',str(length))
        (OUT/'completion_report.md').write_text(completion,encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='headings'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
