"""add chat attachments table

Revision ID: 12_add_chat_attachments
Revises: 11a67ea94371
Create Date: 2026-01-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '12_add_chat_attachments'
down_revision: Union[str, None] = '11a67ea94371'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 创建 chat_attachments 表
    op.create_table(
        'chat_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('attachment_type', sa.String(), nullable=False),  # 'upload', 'generated', 'summary' 等
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),  # MIME type 或扩展名
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('storage_object_name', sa.String(), nullable=True),  # MinIO 对象名
        sa.Column('download_url', sa.String(), nullable=True),  # 下载链接
        sa.Column('preview_url', sa.String(), nullable=True),  # 预览链接
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('attachment_metadata', postgresql.JSON(), nullable=True),  # 额外元数据
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # 创建 chat_attachments 表的索引
    op.create_index('ix_chat_attachments_id', 'chat_attachments', ['id'])
    op.create_index('ix_chat_attachments_session_id', 'chat_attachments', ['session_id'])
    op.create_index('ix_chat_attachments_message_id', 'chat_attachments', ['message_id'])
    op.create_index('ix_chat_attachments_attachment_type', 'chat_attachments', ['attachment_type'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 chat_attachments 表的索引和表
    op.drop_index('ix_chat_attachments_attachment_type', table_name='chat_attachments')
    op.drop_index('ix_chat_attachments_message_id', table_name='chat_attachments')
    op.drop_index('ix_chat_attachments_session_id', table_name='chat_attachments')
    op.drop_index('ix_chat_attachments_id', table_name='chat_attachments')
    op.drop_table('chat_attachments')
