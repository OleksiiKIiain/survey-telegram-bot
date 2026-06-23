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
            for index, answer in enumerate(answers):
                if question.type == "single_choice" and options:
                    replacement = options[index % len(options)]
                    if not answer.option_id or not any(option.id == answer.option_id for option in options):
                        answer.option_id = replacement.id
                        repaired += 1
                if question.type == "multiple_choice" and answer.option_ids:
                    valid_ids = {option.id for option in options}
                    if any(option_id not in valid_ids for option_id in answer.option_ids):
                        answer.option_ids = [option.id for option in options[: len(answer.option_ids)]]
                        repaired += 1
                elif question.type == "multiple_choice" and not answer.option_ids and options:
                    replacement_count = min(2, len(options))
                    answer.option_ids = [option.id for option in options[:replacement_count]]
                    repaired += 1
        db.commit()
        print(f"Repaired answer option links: {repaired}")
    finally:
        db.close()


if __name__ == "__main__":
    repair_answer_options()
