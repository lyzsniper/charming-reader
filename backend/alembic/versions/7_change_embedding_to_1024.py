"""change embedding to 1024

Revision ID: 7
Revises: 6
Create Date: 2026-01-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '7'
down_revision = '6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # text-embedding-v4 默认 1024 维
    # 1. 删除所有现有的 chunks（因为维度不兼容）
    op.execute("TRUNCATE TABLE document_chunks CASCADE")
    
    # 2. 修改列类型为 1024 维
    op.alter_column(
        'document_chunks',
        'embedding',
        type_=Vector(1024),
        existing_type=Vector(1536),
        existing_nullable=True
    )
    
    print("✓ 向量维度已更新为 1024（text-embedding-v4 默认维度）")
    print("⚠️  所有旧的 chunks 已删除，需要重新索引文档")


def downgrade() -> None:
    # 回滚到 1536 维
    op.execute("TRUNCATE TABLE document_chunks CASCADE")
    
    op.alter_column(
        'document_chunks',
        'embedding',
        type_=Vector(1536),
        existing_type=Vector(1024),
        existing_nullable=True
    )

