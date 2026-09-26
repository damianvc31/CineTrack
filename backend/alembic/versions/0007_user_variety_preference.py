"""Add user variety preference for AI recommendations

Revision ID: 0007_user_variety_preference
Revises: 0006_nullable_review_text
Create Date: 2026-09-26 05:20:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '0007_user_variety_preference'
down_revision: Union[str, None] = '0006_nullable_review_text'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.add_column(sa.Column('preferencia_variedad_ia', sa.String(length=20), server_default='MEDIUM', nullable=False))
        batch_op.create_check_constraint(
            'chk_usuario_preferencia_variedad_ia',
            "preferencia_variedad_ia IN ('VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')"
        )


def downgrade() -> None:
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.drop_constraint('chk_usuario_preferencia_variedad_ia', type_='check')
        batch_op.drop_column('preferencia_variedad_ia')
