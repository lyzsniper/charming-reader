"""add adk session tables

Revision ID: 5
Revises: 30f0fd93085d
Create Date: 2026-01-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5'
down_revision = '30f0fd93085d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 adk_sessions 表
    op.create_table(
        'adk_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('app_name', sa.String(), nullable=False, server_default='paper_agent'),
        sa.Column('state', postgresql.JSON(), nullable=True),
        sa.Column('custom_metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'))
    )
    
    # 创建索引
    op.create_index('ix_adk_sessions_id', 'adk_sessions', ['id'])
    op.create_index('ix_adk_sessions_session_id', 'adk_sessions', ['session_id'])
    op.create_index('ix_adk_sessions_user_id', 'adk_sessions', ['user_id'])
    op.create_index('ix_adk_sessions_app_name', 'adk_sessions', ['app_name'])
    
    # 创建 adk_session_messages 表
    op.create_table(
        'adk_session_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('adk_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', postgresql.JSON(), nullable=False),
        sa.Column('custom_metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # 创建索引
    op.create_index('ix_adk_session_messages_id', 'adk_session_messages', ['id'])
    op.create_index('ix_adk_session_messages_session_id', 'adk_session_messages', ['session_id'])


def downgrade() -> None:
    # 删除表（按相反顺序）
    op.drop_index('ix_adk_session_messages_session_id', table_name='adk_session_messages')
    op.drop_index('ix_adk_session_messages_id', table_name='adk_session_messages')
    op.drop_table('adk_session_messages')
    
    op.drop_index('ix_adk_sessions_app_name', table_name='adk_sessions')
    op.drop_index('ix_adk_sessions_user_id', table_name='adk_sessions')
    op.drop_index('ix_adk_sessions_session_id', table_name='adk_sessions')
    op.drop_index('ix_adk_sessions_id', table_name='adk_sessions')
    op.drop_table('adk_sessions')

