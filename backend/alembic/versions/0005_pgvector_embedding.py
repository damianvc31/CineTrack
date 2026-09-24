"""Add pgvector extension and embedding column to titulos

Revision ID: 0005_pgvector_embedding
Revises: 0004_composite_tmdb_id_tipo
Create Date: 2026-09-23 16:10:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    from sqlalchemy import JSON as Vector

# revision identifiers, used by Alembic.
revision: str = '0005_pgvector_embedding'
down_revision: Union[str, None] = '0004_composite_tmdb_id_tipo'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    with op.batch_alter_table('titulos') as batch_op:
        batch_op.add_column(sa.Column('embedding', Vector(768), nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX IF NOT EXISTS ix_titulos_embedding_hnsw ON titulos USING hnsw (embedding vector_cosine_ops);")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_titulos_embedding_hnsw;")

    with op.batch_alter_table('titulos') as batch_op:
        batch_op.drop_column('embedding')
