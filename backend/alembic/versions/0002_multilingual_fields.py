"""add multilingual survey fields

Revision ID: 0002_multilingual_fields
Revises: 0001_initial
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_multilingual_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("surveys", sa.Column("title_uk", sa.String(length=255), nullable=True))
    op.add_column("surveys", sa.Column("description_uk", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("text_uk", sa.Text(), nullable=True))
    op.add_column("question_options", sa.Column("text_uk", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("question_options", "text_uk")
    op.drop_column("questions", "text_uk")
    op.drop_column("surveys", "description_uk")
    op.drop_column("surveys", "title_uk")
