"""Allow nullable review text for score-only reviews

Revision ID: 0006_nullable_review_text
Revises: 0005_pgvector_embedding
Create Date: 2026-09-26 03:50:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '0006_nullable_review_text'
down_revision: Union[str, None] = '0005_pgvector_embedding'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('resenas') as batch_op:
        batch_op.alter_column('texto', existing_type=sa.Text(), nullable=True)
        batch_op.create_check_constraint(
            'chk_resena_puntaje_o_texto',
            '(puntaje IS NOT NULL) OR (texto IS NOT NULL)'
        )


def downgrade() -> None:
    with op.batch_alter_table('resenas') as batch_op:
        batch_op.drop_constraint('chk_resena_puntaje_o_texto', type_='check')
        batch_op.alter_column('texto', existing_type=sa.Text(), nullable=False)
