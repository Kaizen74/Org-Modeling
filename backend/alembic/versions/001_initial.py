"""Initial migration

Revision ID: 001_initial
Revises:
Create Date: 2024-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create grade_salaries table
    op.create_table(
        'grade_salaries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('grade', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('median_salary', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), default='SGD'),
        sa.Column('display_order', sa.Integer(), default=99),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # Create org_analyses table
    op.create_table(
        'org_analyses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('employee_count', sa.Integer()),
        sa.Column('raw_data', sa.JSON()),
        sa.Column('metrics', sa.JSON()),
        sa.Column('ai_analysis', sa.JSON()),
        sa.Column('strategy_context', sa.Text()),
        sa.Column('design_criteria', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # Create settings table
    op.create_table(
        'settings',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', sa.Text()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('settings')
    op.drop_table('org_analyses')
    op.drop_table('grade_salaries')
