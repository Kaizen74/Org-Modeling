"""Add comparisons table

Revision ID: 003_comparisons
Revises: 002_scenarios
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_comparisons'
down_revision: Union[str, None] = '002_scenarios'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comparisons',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('analysis_id', sa.String(36), sa.ForeignKey('org_analyses.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('criteria', sa.JSON()),
        sa.Column('judgments', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('comparisons')
