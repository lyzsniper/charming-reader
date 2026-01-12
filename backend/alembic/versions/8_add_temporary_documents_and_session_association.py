"""add temporary documents and session association

Revision ID: 8_add_temp_docs
Revises: 7
Create Date: 2026-01-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8_add_temp_docs'
down_revision: Union[str, None] = '7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加 is_temporary 字段到 documents 表
    op.add_column('documents', sa.Column('is_temporary', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_documents_is_temporary', 'documents', ['is_temporary'])
    
    # 创建 document_sessions 关联表
    op.create_table(
        'document_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # 创建索引
    op.create_index('ix_document_sessions_id', 'document_sessions', ['id'])
    op.create_index('ix_document_sessions_document_id', 'document_sessions', ['document_id'])
    op.create_index('ix_document_sessions_session_id', 'document_sessions', ['session_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除索引和表
    op.drop_index('ix_document_sessions_session_id', table_name='document_sessions')
    op.drop_index('ix_document_sessions_document_id', table_name='document_sessions')
    op.drop_index('ix_document_sessions_id', table_name='document_sessions')
    op.drop_table('document_sessions')
    
    # 删除 is_temporary 字段
    op.drop_index('ix_documents_is_temporary', table_name='documents')
    op.drop_column('documents', 'is_temporary')
