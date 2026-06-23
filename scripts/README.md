# Scripts

Seed data можна повторно запустити командою:

```bash
docker compose exec backend python -m app.seed
```

Seed є ідемпотентним для демонстраційної бази: якщо опитування вже існують, він не дублює дані.
