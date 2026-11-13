"""One Compass link per (upload, country); Compass-role matches and reasons

Revision ID: 006_engagement_per_country
Revises: 005_engagements
Create Date: 2026-11-13

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '006_engagement_per_country'
down_revision: Union[str, None] = '005_engagements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Same code the app runs at start-up; does nothing if already upgraded
    from app.models.upgrades import upgrade_engagements
    upgrade_engagements(op.get_bind())


def downgrade() -> None:
    raise NotImplementedError("Going back would lose the per-country links; restore a backup instead.")
