"""Structure inputs per upload: manager types set on screen and role families

Revision ID: 007_structure_inputs
Revises: 006_engagement_per_country
Create Date: 2026-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_structure_inputs'
down_revision: Union[str, None] = '006_engagement_per_country'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The app also creates this table at start-up; skip it if it is already there
    if "structure_inputs" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'structure_inputs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('analysis_id', sa.String(36), sa.ForeignKey('org_analyses.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('manager_types', sa.JSON()),
        sa.Column('families', sa.JSON()),
        sa.Column('family_seq', sa.Integer(), default=0),
        sa.Column('family_reasons', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('structure_inputs')
