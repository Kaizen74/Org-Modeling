"""Add engagements table (Compass hand-off, hypotheses, shared grades)

Revision ID: 005_engagements
Revises: 004_ai_dispositions
Create Date: 2026-11-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_engagements'
down_revision: Union[str, None] = '004_ai_dispositions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'engagements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('analysis_id', sa.String(36), sa.ForeignKey('org_analyses.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('key', sa.String(100)),
        sa.Column('packet', sa.JSON()),
        sa.Column('imported_at', sa.DateTime()),
        sa.Column('strategy_draft', sa.Text()),
        sa.Column('hypotheses', sa.JSON()),
        sa.Column('hypothesis_seq', sa.Integer(), default=0),
        sa.Column('grades', sa.JSON()),
        sa.Column('relates', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('engagements')
