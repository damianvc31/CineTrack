"""Change tmdb_id uniqueness to composite (tmdb_id, tipo)

Revision ID: 0004_composite_tmdb_id_tipo
Revises: 0003_dates_and_home_specs
Create Date: 2026-09-12 03:30:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004_composite_tmdb_id_tipo'
down_revision: Union[str, None] = '0003_dates_and_home_specs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('titulos') as batch_op:
        try:
            batch_op.drop_index('ix_titulos_tmdb_id')
        except Exception:
            pass
        batch_op.create_index('ix_titulos_tmdb_id', ['tmdb_id'], unique=False)
        batch_op.create_unique_constraint('uq_titulos_tmdb_id_tipo', ['tmdb_id', 'tipo'])


def downgrade() -> None:
    with op.batch_alter_table('titulos') as batch_op:
        try:
            batch_op.drop_constraint('uq_titulos_tmdb_id_tipo', type_='unique')
        except Exception:
            pass
        try:
            batch_op.drop_index('ix_titulos_tmdb_id')
        except Exception:
            pass
        batch_op.create_index('ix_titulos_tmdb_id', ['tmdb_id'], unique=True)
