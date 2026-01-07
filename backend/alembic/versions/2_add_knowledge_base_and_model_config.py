"""add knowledge base and model config tables

Revision ID: 2_add_kb_model
Revises: 1a6c6664a3cc
Create Date: 2026-01-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2_add_kb_model'
down_revision: Union[str, None] = '1a6c6664a3cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建知识库表
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_bases_id'), 'knowledge_bases', ['id'], unique=False)
    op.create_index(op.f('ix_knowledge_bases_name'), 'knowledge_bases', ['name'], unique=True)
    
    # 创建文档知识库关联表
    op.create_table(
        'document_knowledge_base',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('knowledge_base_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_knowledge_base_id'), 'document_knowledge_base', ['id'], unique=False)
    
    # 创建模型配置表
    op.create_table(
        'model_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('base_url', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_configurations_id'), 'model_configurations', ['id'], unique=False)
    op.create_index(op.f('ix_model_configurations_name'), 'model_configurations', ['name'], unique=True)


def downgrade() -> None:
    # 删除模型配置表
    op.drop_index(op.f('ix_model_configurations_name'), table_name='model_configurations')
    op.drop_index(op.f('ix_model_configurations_id'), table_name='model_configurations')
    op.drop_table('model_configurations')
    
    # 删除文档知识库关联表
    op.drop_index(op.f('ix_document_knowledge_base_id'), table_name='document_knowledge_base')
    op.drop_table('document_knowledge_base')
    
    # 删除知识库表
    op.drop_index(op.f('ix_knowledge_bases_name'), table_name='knowledge_bases')
    op.drop_index(op.f('ix_knowledge_bases_id'), table_name='knowledge_bases')
    op.drop_table('knowledge_bases')

