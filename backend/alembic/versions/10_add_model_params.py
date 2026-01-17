"""add model parameters to model_configurations

Revision ID: 10_add_model_params
Revises: 9_add_chat_tables
Create Date: 2026-01-17 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10_add_model_params'
down_revision: Union[str, None] = '9_add_chat_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加模型参数字段到model_configurations表"""
    # 添加provider字段
    op.add_column('model_configurations', sa.Column('provider', sa.String(), nullable=True))
    
    # 添加模型参数字段
    op.add_column('model_configurations', sa.Column('temperature', sa.Float(), nullable=True))
    op.add_column('model_configurations', sa.Column('max_tokens', sa.Integer(), nullable=True))
    op.add_column('model_configurations', sa.Column('top_p', sa.Float(), nullable=True))
    op.add_column('model_configurations', sa.Column('frequency_penalty', sa.Float(), nullable=True))
    op.add_column('model_configurations', sa.Column('presence_penalty', sa.Float(), nullable=True))


def downgrade() -> None:
    """移除模型参数字段"""
    op.drop_column('model_configurations', 'presence_penalty')
    op.drop_column('model_configurations', 'frequency_penalty')
    op.drop_column('model_configurations', 'top_p')
    op.drop_column('model_configurations', 'max_tokens')
    op.drop_column('model_configurations', 'temperature')
    op.drop_column('model_configurations', 'provider')
