"""Migrate anio_estreno and anio_fin to fecha_estreno and fecha_fin

Revision ID: 0003_dates_and_home_specs
Revises: 0002_technical_adjustments
Create Date: 2026-09-12 02:30:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0003_dates_and_home_specs'
down_revision: Union[str, None] = '0002_technical_adjustments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('titulos') as batch_op:
        # Dropear indices y columnas viejas
        try:
            batch_op.drop_index('ix_titulos_anio_estreno')
        except Exception:
            pass
        batch_op.drop_column('anio_estreno')
        batch_op.drop_column('anio_fin')

        # Agregar columnas nuevas
        batch_op.add_column(sa.Column('fecha_estreno', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('fecha_fin', sa.Date(), nullable=True))
        batch_op.create_index('ix_titulos_fecha_estreno', ['fecha_estreno'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('titulos') as batch_op:
        try:
            batch_op.drop_index('ix_titulos_fecha_estreno')
        except Exception:
            pass
        batch_op.drop_column('fecha_estreno')
        batch_op.drop_column('fecha_fin')

        batch_op.add_column(sa.Column('anio_estreno', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('anio_fin', sa.Integer(), nullable=True))
        batch_op.create_index('ix_titulos_anio_estreno', ['anio_estreno'], unique=False)
