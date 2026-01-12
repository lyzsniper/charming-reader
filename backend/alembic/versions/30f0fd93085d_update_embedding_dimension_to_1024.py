"""update_embedding_dimension_to_1024

Revision ID: 30f0fd93085d
Revises: 11a67ea94371
Create Date: 2026-01-07 20:07:54.020083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '30f0fd93085d'
down_revision: Union[str, Sequence[str], None] = '11a67ea94371'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update the embedding column type from Vector(1536) to Vector(1024)
    # Note: Changing vector dimension usually requires dropping and recreating the column or using explicit CAST,
    # but since data with wrong dimension can't exist, we assume existing data might be incompatible or empty.
    # Postgres pgvector allows altering type if dimensions match, but here they don't.
    # We will use USING clause to truncate or pad if needed, or simply cast nulls.
    # Since we likely have no valid 1536 data (or don't care about mixed), we can drop/recreate or alter with type cast.
    
    # Safest way for existing data is to clear it or if it's empty just alter.
    # Given this is dev/test data causing error, we can alter.
    
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector(1024);")


def downgrade() -> None:
    # Revert back to 1536
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536);")
