import csv
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.answer import Answer
from app.models.question import Question
from app.models.survey import Survey
from app.models.survey_session import SurveySession

router = APIRouter()


def safe_cell(value: str) -> str:
    # Spreadsheet applications may interpret untrusted text as formulas.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\uff1d", "\uff0b", "\uff0d", "\uff20")) or value.startswith(("\t", "\r", "\n")) else value


def answer_value(answer: Answer) -> str:
    if answer.text_value:
        return answer.text_value
    if answer.number_value is not None:
        return str(answer.number_value)
    if answer.option:
        return answer.option.text
    if answer.option_ids:
        option_map = {option.id: option.text for option in answer.question.options}
        return ", ".join(option_map.get(item, str(item)) for item in answer.option_ids)
    return ""


def export_rows(db: Session, survey_id: int) -> list[list[str]]:
    if not db.get(Survey, survey_id):
        raise HTTPException(status_code=404, detail="Survey not found")
    answers = db.scalars(
        select(Answer)
        .join(SurveySession)
        .where(SurveySession.survey_id == survey_id)
        .options(
            joinedload(Answer.option),
            joinedload(Answer.question).selectinload(Question.options),
            joinedload(Answer.session).joinedload(SurveySession.respondent),
        )
        .order_by(Answer.session_id, Answer.question_id)
    ).all()
    rows = [["session_id", "respondent", "question", "answer", "created_at"]]
    for answer in answers:
        user = answer.session.respondent
        respondent = user.username or f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user.telegram_id)
        rows.append([str(answer.session_id), respondent, answer.question.text, answer_value(answer), answer.created_at.isoformat()])
    return [[safe_cell(cell) for cell in row] for row in rows]


@router.get("/surveys/{survey_id}.csv")
def export_csv(survey_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)) -> Response:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerows(export_rows(db, survey_id))
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=survey-{survey_id}.csv"})


@router.get("/surveys/{survey_id}.xlsx")
def export_xlsx(survey_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)) -> StreamingResponse:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Responses"
    for row in export_rows(db, survey_id):
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=survey-{survey_id}.xlsx"},
    )
