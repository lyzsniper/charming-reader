"""merge alembic heads

Revision ID: 14_merge_heads
Revises: 10_add_model_params, 13_add_agent_skills_center
Create Date: 2026-01-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "14_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "10_add_model_params",
    "13_add_agent_skills_center",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This is a merge migration with no schema changes.
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Alembic will handle branch-specific downgrades.
    pass
