"""add chat tables

Revision ID: 9_add_chat_tables
Revises: 8_add_temp_docs
Create Date: 2026-01-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9_add_chat_tables'
down_revision: Union[str, None] = '8_add_temp_docs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 创建 chat_sessions 表
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('session_title', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('custom_metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )
    
    # 创建 chat_sessions 表的索引
    op.create_index('ix_chat_sessions_id', 'chat_sessions', ['id'])
    op.create_index('ix_chat_sessions_session_id', 'chat_sessions', ['session_id'], unique=True)
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'])
    
    # 创建 chat_messages 表
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('message_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_metadata', postgresql.JSON(), nullable=True),
        sa.Column('parent_message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # 创建 chat_messages 表的索引
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'])
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_parent_message_id', 'chat_messages', ['parent_message_id'])
    op.create_index('ix_chat_messages_role_message_type', 'chat_messages', ['role', 'message_type'])
    
    # 创建 chat_histories 表
    op.create_table(
        'chat_histories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('user_message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assistant_message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # 创建 chat_histories 表的索引
    op.create_index('ix_chat_histories_id', 'chat_histories', ['id'])
    op.create_index('ix_chat_histories_session_id', 'chat_histories', ['session_id'])
    op.create_index('ix_chat_histories_user_message_id', 'chat_histories', ['user_message_id'])
    op.create_index('ix_chat_histories_assistant_message_id', 'chat_histories', ['assistant_message_id'])
    # 创建复合唯一约束：同一session内turn_index唯一
    op.create_unique_constraint('uix_chat_histories_session_turn', 'chat_histories', ['session_id', 'turn_index'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 chat_histories 表的索引和表
    op.drop_constraint('uix_chat_histories_session_turn', 'chat_histories', type_='unique')
    op.drop_index('ix_chat_histories_assistant_message_id', table_name='chat_histories')
    op.drop_index('ix_chat_histories_user_message_id', table_name='chat_histories')
    op.drop_index('ix_chat_histories_session_id', table_name='chat_histories')
    op.drop_index('ix_chat_histories_id', table_name='chat_histories')
    op.drop_table('chat_histories')
    
    # 删除 chat_messages 表的索引和表
    op.drop_index('ix_chat_messages_role_message_type', table_name='chat_messages')
    op.drop_index('ix_chat_messages_parent_message_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_session_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_id', table_name='chat_messages')
    op.drop_table('chat_messages')
    
    # 删除 chat_sessions 表的索引和表
    op.drop_index('ix_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_session_id', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_id', table_name='chat_sessions')
    op.drop_table('chat_sessions')
