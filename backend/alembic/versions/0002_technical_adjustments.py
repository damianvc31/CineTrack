"""Technical adjustments: rating_unificado, es_admin, and enriched titulos_elenco (personaje, orden)

Revision ID: 0002_technical_adjustments
Revises: 0001_initial_schema
Create Date: 2026-09-11 14:30:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002_technical_adjustments'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Columna es_admin en usuarios
    op.add_column('usuarios', sa.Column('es_admin', sa.Boolean(), nullable=False, server_default=sa.false()))

    # 2. Columna rating_unificado en titulos e indice
    op.add_column('titulos', sa.Column('rating_unificado', sa.Float(), nullable=False, server_default='0.0'))
    op.create_index(op.f('ix_titulos_rating_unificado'), 'titulos', ['rating_unificado'], unique=False)

    # 3. Columnas personaje y orden en titulos_elenco
    op.add_column('titulos_elenco', sa.Column('personaje', sa.String(length=150), nullable=True))
    op.add_column('titulos_elenco', sa.Column('orden', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('titulos_elenco', 'orden')
    op.drop_column('titulos_elenco', 'personaje')
    op.drop_index(op.f('ix_titulos_rating_unificado'), table_name='titulos')
    op.drop_column('titulos', 'rating_unificado')
    op.drop_column('usuarios', 'es_admin')
