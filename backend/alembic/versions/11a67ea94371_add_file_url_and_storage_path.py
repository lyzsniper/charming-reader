"""add_file_url_and_storage_path

Revision ID: 11a67ea94371
Revises: 4_add_minio_storage
Create Date: 2026-01-07 19:32:51.098863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11a67ea94371'
down_revision: Union[str, Sequence[str], None] = '4_add_minio_storage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add file_download_url column to store the presigned or public URL
    op.add_column('documents', sa.Column('file_download_url', sa.String(), nullable=True))
    
    # Add storage_bucket_name to explicitly store bucket info if needed separately, 
    # though storage_object_name might be enough. 
    # Let's add storage_path just in case structure changes.
    op.add_column('documents', sa.Column('storage_path', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'storage_path')
    op.drop_column('documents', 'file_download_url')
