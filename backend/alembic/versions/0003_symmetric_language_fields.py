"""add symmetric english translation fields

Revision ID: 0003_symmetric_language_fields
Revises: 0002_multilingual_fields
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_symmetric_language_fields"
down_revision: Union[str, None] = "0002_multilingual_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("surveys", sa.Column("title_en", sa.String(length=255), nullable=True))
    op.add_column("surveys", sa.Column("description_en", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("text_en", sa.Text(), nullable=True))
    op.add_column("question_options", sa.Column("text_en", sa.String(length=500), nullable=True))
    op.execute("UPDATE surveys SET title_en = title WHERE title_en IS NULL")
    op.execute("UPDATE surveys SET description_en = description WHERE description_en IS NULL")
    op.execute("UPDATE questions SET text_en = text WHERE text_en IS NULL")
    op.execute("UPDATE question_options SET text_en = text WHERE text_en IS NULL")


def downgrade() -> None:
    op.drop_column("question_options", "text_en")
    op.drop_column("questions", "text_en")
    op.drop_column("surveys", "description_en")
    op.drop_column("surveys", "title_en")
