# Survey Bot: Telegram опитування + FastAPI + React

Навчальний full-stack проєкт для дипломної/курсової роботи на тему управління проєктом розробки системи автоматизованого опитування та аналізу даних засобами Telegram Bot та веб-технологій.

## Архітектура

- `backend/` - FastAPI REST API, SQLAlchemy, Alembic, JWT auth, аналітика, CSV/XLSX export.
- `bot/` - Telegram bot на aiogram 3 з FSM та polling.
- `frontend/` - React + Vite + TypeScript + Tailwind CSS + Recharts admin panel.
- `db` у Docker Compose - PostgreSQL 16.
- `docs/` - короткі нотатки для захисту.

Backend є центральною точкою логіки. Telegram bot і frontend працюють тільки через REST API.

## Повна структура

```text
survey-bot/
  backend/
    alembic/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      main.py
      seed.py
  bot/
    bot/
      api.py
      config.py
      keyboards.py
      main.py
  frontend/
    src/
      pages/
      ui/
      api.ts
      main.tsx
      types.ts
  docs/
  scripts/
  docker-compose.yml
  .env.example
```

## Швидкий запуск через Docker

1. Створіть `.env`:

```bash
cp .env.example .env
```

2. Для Telegram-бота вкажіть токен у `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:your-token-from-botfather
```

Якщо токен не заданий, backend і frontend працюватимуть, а bot container буде в idle-режимі.

3. Запустіть:

```bash
docker compose up --build
```

4. Відкрийте:

- Admin panel: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Тестовий логін

- Email: `admin@example.com`
- Password: `admin12345`

Seed створює адміністратора, 3 опитування, питання різних типів, варіанти відповідей, тестових респондентів і відповіді.

## Як перевірити адмін-панель

1. Відкрийте http://localhost:5173.
2. Увійдіть тестовим адміністратором.
3. Перейдіть у `Surveys`.
4. Створіть нове опитування або відкрийте seeded survey.
5. Додайте питання типів `single_choice`, `multiple_choice`, `free_text`, `scale`.
6. Перегляньте `Responses` та `Analytics`.
7. На сторінці survey details натисніть CSV або Excel export.

## Як перевірити Telegram-бота

1. Створіть бота через Telegram BotFather.
2. Додайте токен у `.env`.
3. Перезапустіть `docker compose up --build`.
4. У Telegram надішліть `/start`.
5. Оберіть активне опитування.
6. Пройдіть питання покроково.
7. Перевірте нові відповіді у веб-панелі.

## Основні API endpoints

- `POST /api/v1/auth/login` - JWT login.
- `GET /api/v1/auth/me` - поточний адміністратор.
- `GET /api/v1/surveys` - список опитувань.
- `POST /api/v1/surveys` - створити опитування.
- `PATCH /api/v1/surveys/{id}` - оновити опитування.
- `POST /api/v1/surveys/{id}/questions` - додати питання.
- `GET /api/v1/public/surveys` - активні опитування для бота.
- `POST /api/v1/public/respondents` - створити/оновити Telegram-респондента.
- `POST /api/v1/public/sessions` - старт проходження.
- `POST /api/v1/public/sessions/{id}/answers` - зберегти відповідь.
- `POST /api/v1/public/sessions/{id}/complete` - завершити проходження.
- `GET /api/v1/analytics/overview` - аналітика.
- `GET /api/v1/export/surveys/{id}.csv` - CSV export.
- `GET /api/v1/export/surveys/{id}.xlsx` - Excel export.

## Локальний запуск без Docker

Потрібен PostgreSQL і змінна `DATABASE_URL`.

Backend:

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Bot:

```bash
cd bot
pip install -r requirements.txt
python -m bot.main
```

## Аудит і матеріали магістерської

`docs/thesis/` містить український текст, перевірені посилання, схеми, протоколи та скриншоти ізольованого тестового середовища. `scripts/build_thesis.py` формує локальні DOCX/PDF у `output/thesis/`. Цей каталог виключений із Git. Офіційні реквізити та недоступні методичні матеріали не вигадуються; стан вимог наведено у `docs/thesis/compliance-report.md`.

Перевірки: `backend/tests/test_integrity.py` використовує тільки окрему PostgreSQL БД з назвою `survey_audit_*`; `backend/tests/http_audit.py` перевіряє реальний HTTP API; `scripts/ui_audit.cjs` працює з ізольованим frontend на порту 5174. Повне проходження через Telegram-клієнт обліковується окремо від цих тестів.

Маршрути `/api/v1/public/*` тепер потребують `X-Bot-Key`: SHA-256 від налаштованого `TELEGRAM_BOT_TOKEN`. Бот додає його автоматично. Без токена адмін-панель працює, службові маршрути повертають 503. Це секретний службовий реквізит, його не слід публікувати. Для зовнішнього розгортання потрібні HTTPS та окреме керування секретами.

БД не оприлюднюється портом хоста. Для локальних SQL-перевірок використовуйте `docker compose exec db psql -U survey_user -d survey_bot`. Звичайна зупинка: `docker compose down`, без `-v`. Скрипт `app.repair_answers` тепер лише виявляє пошкоджені зв'язки та ніколи не підставляє вигадані відповіді.
