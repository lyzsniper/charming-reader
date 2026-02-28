"""add agent skills center tables

Revision ID: 13_add_agent_skills_center
Revises: 12_add_chat_attachments
Create Date: 2026-01-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '13_add_agent_skills_center'
down_revision: Union[str, None] = '12_add_chat_attachments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # 1. 创建 skill 表（技能定义）
    op.create_table(
        'skill',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),  # 'file' | 'database' | 'builtin'
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('triggers', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('author', sa.String(100), nullable=True),
        sa.Column('download_count', sa.Integer(), server_default='0'),
        sa.Column('activation_count', sa.Integer(), server_default='0'),
        sa.Column('rating', sa.DECIMAL(3, 2), nullable=True),
        sa.Column('skill_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # skill 表索引
    op.create_index('ix_skill_id', 'skill', ['id'])
    op.create_index('ix_skill_name', 'skill', ['name'])
    op.create_index('ix_skill_category', 'skill', ['category'])
    op.create_index('ix_skill_status', 'skill', ['status'])
    op.create_index('ix_skill_triggers', 'skill', ['triggers'], postgresql_using='gin')
    
    # 2. 创建 skill_resource 表（技能资源文件）
    op.create_table(
        'skill_resource',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skill.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('file_name', sa.String(200), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('storage_object_name', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_index('ix_skill_resource_id', 'skill_resource', ['id'])
    op.create_index('ix_skill_resource_skill_id', 'skill_resource', ['skill_id'])
    
    # 3. 创建 agent_template 表（Agent模板）
    op.create_table(
        'agent_template',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('base_instruction', sa.Text(), nullable=False),
        sa.Column('is_builtin', sa.Boolean(), server_default='false'),
        sa.Column('is_public', sa.Boolean(), server_default='false'),
        sa.Column('author', sa.String(100), nullable=True),
        sa.Column('usage_count', sa.Integer(), server_default='0'),
        sa.Column('rating', sa.DECIMAL(3, 2), nullable=True),
        sa.Column('template_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_index('ix_agent_template_id', 'agent_template', ['id'])
    op.create_index('ix_agent_template_name', 'agent_template', ['name'])
    
    # 4. 创建 agent_config 表（Agent实例配置）
    op.create_table(
        'agent_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_template.id', ondelete='SET NULL'), nullable=True),
        sa.Column('instruction', sa.Text(), nullable=False),
        sa.Column('model_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_configurations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('agent_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_index('ix_agent_config_id', 'agent_config', ['id'])
    op.create_index('ix_agent_config_name', 'agent_config', ['name'])
    op.create_index('ix_agent_config_user_id', 'agent_config', ['user_id'])
    
    # 5. 创建 agent_skill 表（Agent-Skill关联）
    op.create_table(
        'agent_skill',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_config.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skill.id', ondelete='CASCADE'), nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('is_required', sa.Boolean(), server_default='false'),
        sa.Column('auto_activate', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('agent_config_id', 'skill_id', name='uix_agent_skill')
    )
    
    op.create_index('ix_agent_skill_id', 'agent_skill', ['id'])
    op.create_index('ix_agent_skill_agent_config_id', 'agent_skill', ['agent_config_id'])
    op.create_index('ix_agent_skill_skill_id', 'agent_skill', ['skill_id'])
    
    # 6. 创建 tool 表（工具定义）
    op.create_table(
        'tool',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tool_type', sa.String(50), nullable=False),  # 'mcp' | 'python' | 'api'
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('source_config', postgresql.JSONB(), nullable=True),
        sa.Column('schema_config', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('usage_count', sa.Integer(), server_default='0'),
        sa.Column('tool_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_index('ix_tool_id', 'tool', ['id'])
    op.create_index('ix_tool_name', 'tool', ['name'])
    op.create_index('ix_tool_tool_type', 'tool', ['tool_type'])
    
    # 7. 创建 agent_tool 表（Agent-Tool关联）
    op.create_table(
        'agent_tool',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_config.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tool.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default='false'),
        sa.Column('configuration', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('agent_config_id', 'tool_id', name='uix_agent_tool')
    )
    
    op.create_index('ix_agent_tool_id', 'agent_tool', ['id'])
    op.create_index('ix_agent_tool_agent_config_id', 'agent_tool', ['agent_config_id'])
    op.create_index('ix_agent_tool_tool_id', 'agent_tool', ['tool_id'])
    
    # 8. 创建 skill_activation_log 表（技能激活日志）
    op.create_table(
        'skill_activation_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skill.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_config.id', ondelete='SET NULL'), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('activation_reason', sa.Text(), nullable=True),
        sa.Column('query_text', sa.Text(), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    op.create_index('ix_skill_activation_log_id', 'skill_activation_log', ['id'])
    op.create_index('ix_skill_activation_log_skill_id', 'skill_activation_log', ['skill_id'])
    op.create_index('ix_skill_activation_log_session_id', 'skill_activation_log', ['session_id'])
    
    # 9. 创建 agent_execution_log 表（Agent执行日志）
    op.create_table(
        'agent_execution_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_config.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('input_text', sa.Text(), nullable=True),
        sa.Column('output_text', sa.Text(), nullable=True),
        sa.Column('tool_calls', postgresql.JSONB(), nullable=True),
        sa.Column('activated_skills', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_index('ix_agent_execution_log_id', 'agent_execution_log', ['id'])
    op.create_index('ix_agent_execution_log_agent_config_id', 'agent_execution_log', ['agent_config_id'])
    op.create_index('ix_agent_execution_log_session_id', 'agent_execution_log', ['session_id'])


def downgrade() -> None:
    """Downgrade schema."""
    
    # 删除表（逆序）
    op.drop_table('agent_execution_log')
    op.drop_table('skill_activation_log')
    op.drop_table('agent_tool')
    op.drop_table('tool')
    op.drop_table('agent_skill')
    op.drop_table('agent_config')
    op.drop_table('agent_template')
    op.drop_table('skill_resource')
    op.drop_table('skill')
