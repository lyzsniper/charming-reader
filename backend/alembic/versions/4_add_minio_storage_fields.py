"""add minio storage fields

Revision ID: 4_add_minio_storage
Revises: 3_migrate_to_uuid
Create Date: 2026-01-07 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4_add_minio_storage'
down_revision = '3_migrate_to_uuid'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    升级数据库schema，添加 MinIO 存储相关字段
    """
    # 1. 重命名 filename 为 original_filename
    op.alter_column(
        'documents',
        'filename',
        new_column_name='original_filename',
        existing_type=sa.String(),
        existing_nullable=False
    )
    
    # 2. 添加新字段
    op.add_column('documents', sa.Column('storage_object_name', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('content_type', sa.String(), server_default='application/pdf', nullable=False))
    
    # 3. 为现有数据生成唯一的 UUID 作为 storage_object_name
    # 不能直接使用 original_filename，因为可能有重复
    op.execute("""
        UPDATE documents 
        SET storage_object_name = CONCAT(gen_random_uuid()::text, '.pdf')
        WHERE storage_object_name IS NULL
    """)
    
    # 4. 将 storage_object_name 设为 NOT NULL
    op.alter_column(
        'documents',
        'storage_object_name',
        nullable=False,
        existing_type=sa.String()
    )
    
    # 5. 创建唯一索引
    op.create_index(
        'ix_documents_storage_object_name',
        'documents',
        ['storage_object_name'],
        unique=True
    )


def downgrade() -> None:
    """
    降级数据库schema
    """
    # 1. 删除索引
    op.drop_index('ix_documents_storage_object_name', table_name='documents')
    
    # 2. 删除新字段
    op.drop_column('documents', 'content_type')
    op.drop_column('documents', 'file_size')
    op.drop_column('documents', 'storage_object_name')
    
    # 3. 重命名回 filename
    op.alter_column(
        'documents',
        'original_filename',
        new_column_name='filename',
        existing_type=sa.String(),
        existing_nullable=False
    )

