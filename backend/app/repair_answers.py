from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.answer import Answer
from app.models.question import Question


def repair_answer_options() -> None:
    db = SessionLocal()
    try:
        questions = db.scalars(select(Question).where(Question.type.in_(["single_choice", "multiple_choice"]))).all()
        repaired = 0
        for question in questions:
            options = sorted(question.options, key=lambda option: option.position)
            answers = db.scalars(select(Answer).where(Answer.question_id == question.id)).all()
            for answer in answers:
                valid_ids = {option.id for option in options}
                choices = [answer.option_id] if question.type == "single_choice" else (answer.option_ids or [])
                if not choices or any(item not in valid_ids for item in choices):
                    repaired += 1
        print(f"Invalid answer links: {repaired}. Modified rows: 0. Restore only from a verified backup.")
    finally:
        db.close()


if __name__ == "__main__":
    repair_answer_options()
