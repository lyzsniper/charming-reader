"""migrate all tables to use UUID

Revision ID: 3_migrate_to_uuid
Revises: 2_add_kb_model
Create Date: 2026-01-07 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid


# revision identifiers, used by Alembic.
revision: str = '3_migrate_to_uuid'
down_revision: Union[str, None] = '2_add_kb_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    将所有表的 ID 从 Integer 迁移到 UUID
    
    注意：这个迁移会删除所有现有数据！
    如果有重要数据，请先备份。
    """
    # 由于要改变主键类型，最简单的方式是重建表
    
    # 1. 删除所有旧表（按照依赖关系的逆序）
    op.drop_table('document_chunks')
    op.drop_table('document_knowledge_base')
    op.drop_table('documents')
    op.drop_table('knowledge_bases')
    op.drop_table('model_configurations')
    
    # 2. 创建使用 UUID 的新表
    
    # 知识库表
    op.create_table(
        'knowledge_bases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_knowledge_bases_id'), 'knowledge_bases', ['id'], unique=False)
    op.create_index(op.f('ix_knowledge_bases_name'), 'knowledge_bases', ['name'], unique=False)
    
    # 文档表
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('upload_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('content_markdown', sa.Text(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), default=False, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    
    # 文档知识库关联表
    op.create_table(
        'document_knowledge_base',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('knowledge_base_id', UUID(as_uuid=True), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_knowledge_base_id'), 'document_knowledge_base', ['id'], unique=False)
    
    # 文档分块表
    op.create_table(
        'document_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),  # pgvector 类型，1536维度
        sa.Column('chunk_index', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_chunks_id'), 'document_chunks', ['id'], unique=False)
    
    # 模型配置表
    op.create_table(
        'model_configurations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('base_url', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_model_configurations_id'), 'model_configurations', ['id'], unique=False)
    op.create_index(op.f('ix_model_configurations_name'), 'model_configurations', ['name'], unique=False)


def downgrade() -> None:
    """
    回滚：将 UUID 改回 Integer
    
    注意：这个回滚也会删除所有数据！
    """
    # 删除 UUID 版本的表
    op.drop_table('document_chunks')
    op.drop_table('document_knowledge_base')
    op.drop_table('documents')
    op.drop_table('knowledge_bases')
    op.drop_table('model_configurations')
    
    # 重新创建 Integer 版本的表（参考之前的迁移）
    # ... 这里省略，因为通常不会回滚这种类型的迁移

