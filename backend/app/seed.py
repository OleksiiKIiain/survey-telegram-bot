from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.models.answer import Answer
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.respondent import TelegramUser
from app.models.survey import Survey
from app.models.survey_session import SurveySession


def seed() -> None:
    db = SessionLocal()
    try:
        admin = db.scalar(select(Admin).where(Admin.email == "admin@example.com"))
        if not admin:
            admin = Admin(email="admin@example.com", full_name="Demo Administrator", hashed_password=get_password_hash("admin12345"))
            db.add(admin)
            db.flush()

        if db.scalar(select(Survey).limit(1)):
            db.commit()
            return

        survey1 = Survey(
            title="Customer Service Satisfaction",
            title_en="Customer Service Satisfaction",
            title_uk="Задоволеність клієнтів сервісом",
            description="Demo survey for service quality analysis.",
            description_en="Demo survey for service quality analysis.",
            description_uk="Демонстраційне опитування для аналізу якості сервісу.",
            status="active",
            created_by_id=admin.id,
        )
        survey2 = Survey(
            title="Student Learning Feedback",
            title_en="Student Learning Feedback",
            title_uk="Відгук студента про навчання",
            description="Course feedback survey with ratings and text answers.",
            description_en="Course feedback survey with ratings and text answers.",
            description_uk="Опитування про курс з оцінками та текстовими відповідями.",
            status="active",
            created_by_id=admin.id,
        )
        survey3 = Survey(
            title="Internal HR Pulse",
            title_en="Internal HR Pulse",
            title_uk="Внутрішній HR-пульс",
            description="Draft survey for employees.",
            description_en="Draft survey for employees.",
            description_uk="Чернетка опитування для співробітників.",
            status="draft",
            created_by_id=admin.id,
        )
        db.add_all([survey1, survey2, survey3])
        db.flush()

        def question(
            survey: Survey,
            text: str,
            text_uk: str,
            qtype: str,
            position: int,
            options: list[tuple[str, str]] | None = None,
            scale_min: int | None = None,
            scale_max: int | None = None,
        ) -> Question:
            item = Question(survey_id=survey.id, text=text, text_en=text, text_uk=text_uk, type=qtype, position=position, scale_min=scale_min, scale_max=scale_max)
            db.add(item)
            db.flush()
            for index, option_pair in enumerate(options or []):
                db.add(QuestionOption(question_id=item.id, text=option_pair[0], text_en=option_pair[0], text_uk=option_pair[1], position=index))
            db.flush()
            return item

        q1 = question(survey1, "How satisfied are you with the service?", "Наскільки ви задоволені сервісом?", "scale", 0, scale_min=1, scale_max=5)
        q2 = question(survey1, "Which channel did you use?", "Яким каналом ви користувалися?", "single_choice", 1, [("Telegram", "Telegram"), ("Website", "Сайт"), ("Phone", "Телефон"), ("Office", "Офіс")])
        q3 = question(survey1, "What should we improve?", "Що нам варто покращити?", "multiple_choice", 2, [("Speed", "Швидкість"), ("Price", "Ціну"), ("Support", "Підтримку"), ("Documentation", "Документацію")])
        q4 = question(survey1, "Leave a short comment", "Залиште короткий коментар", "free_text", 3)

        question(survey2, "Rate course materials", "Оцініть навчальні матеріали", "scale", 0, scale_min=1, scale_max=10)
        question(survey2, "Preferred learning format", "Бажаний формат навчання", "single_choice", 1, [("Online", "Онлайн"), ("Offline", "Офлайн"), ("Hybrid", "Змішаний")])
        question(survey2, "Which topics were useful?", "Які теми були корисними?", "multiple_choice", 2, [("API", "API"), ("Databases", "Бази даних"), ("Frontend", "Frontend"), ("Project management", "Управління проєктом")])
        question(survey2, "Your suggestion", "Ваша пропозиція", "free_text", 3)

        user1 = TelegramUser(telegram_id=100001, username="demo_student", first_name="Ivan", last_name="Student", language_code="uk")
        user2 = TelegramUser(telegram_id=100002, username="olena_demo", first_name="Olena", last_name="Tester", language_code="uk")
        db.add_all([user1, user2])
        db.flush()

        session1 = SurveySession(survey_id=survey1.id, respondent_id=user1.id, status="completed", completed_at=datetime.now(timezone.utc))
        session2 = SurveySession(survey_id=survey1.id, respondent_id=user2.id, status="completed", completed_at=datetime.now(timezone.utc))
        db.add_all([session1, session2])
        db.flush()

        channel_options = sorted(q2.options, key=lambda item: item.position)
        improve_options = sorted(q3.options, key=lambda item: item.position)
        db.add_all([
            Answer(session_id=session1.id, question_id=q1.id, number_value=5),
            Answer(session_id=session1.id, question_id=q2.id, option_id=channel_options[0].id),
            Answer(session_id=session1.id, question_id=q3.id, option_ids=[improve_options[0].id, improve_options[2].id]),
            Answer(session_id=session1.id, question_id=q4.id, text_value="Everything worked well."),
            Answer(session_id=session2.id, question_id=q1.id, number_value=4),
            Answer(session_id=session2.id, question_id=q2.id, option_id=channel_options[1].id),
            Answer(session_id=session2.id, question_id=q3.id, option_ids=[improve_options[1].id]),
            Answer(session_id=session2.id, question_id=q4.id, text_value="Add faster response times."),
        ])
        db.commit()
        print("Seed data created")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
