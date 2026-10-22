"""Add ai_dispositions table

Revision ID: 004_ai_dispositions
Revises: 003_comparisons
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_ai_dispositions'
down_revision: Union[str, None] = '003_comparisons'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_dispositions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('analysis_id', sa.String(36), sa.ForeignKey('org_analyses.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('enabled', sa.Integer(), default=1),
        sa.Column('roles', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('ai_dispositions')
