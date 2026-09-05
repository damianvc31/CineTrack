"""Initial schema: usuarios, titulos, temporadas, episodios, estados, resenas

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-05 12:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Usuarios
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre_usuario', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('pais', sa.String(length=100), nullable=True),
        sa.Column('ciudad', sa.String(length=100), nullable=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('avatar_binario', sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usuarios_id'), 'usuarios', ['id'], unique=False)
    op.create_index(op.f('ix_usuarios_nombre_usuario'), 'usuarios', ['nombre_usuario'], unique=True)

    # 2. Titulos (tabla unificada)
    op.create_table(
        'titulos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=10), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('sinopsis', sa.Text(), nullable=True),
        sa.Column('portada_url', sa.String(length=500), nullable=True),
        sa.Column('anio_estreno', sa.Integer(), nullable=True),
        sa.Column('anio_fin', sa.Integer(), nullable=True),
        sa.Column('duracion', sa.Integer(), nullable=True),
        sa.Column('director', sa.String(length=150), nullable=True),
        sa.Column('guionista', sa.String(length=150), nullable=True),
        sa.Column('pais', sa.String(length=100), nullable=True),
        sa.Column('idioma_original', sa.String(length=20), nullable=True),
        sa.Column('popularidad', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('popularidad_percentil', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('vote_average_tmdb', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('vote_count_tmdb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status_tmdb', sa.String(length=50), nullable=True),
        sa.Column('proximo_episodio_fecha', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_titulos_id'), 'titulos', ['id'], unique=False)
    op.create_index(op.f('ix_titulos_tmdb_id'), 'titulos', ['tmdb_id'], unique=True)
    op.create_index(op.f('ix_titulos_tipo'), 'titulos', ['tipo'], unique=False)
    op.create_index(op.f('ix_titulos_nombre'), 'titulos', ['nombre'], unique=False)
    op.create_index(op.f('ix_titulos_anio_estreno'), 'titulos', ['anio_estreno'], unique=False)
    op.create_index(op.f('ix_titulos_director'), 'titulos', ['director'], unique=False)
    op.create_index(op.f('ix_titulos_guionista'), 'titulos', ['guionista'], unique=False)
    op.create_index(op.f('ix_titulos_popularidad'), 'titulos', ['popularidad'], unique=False)
    op.create_index(op.f('ix_titulos_popularidad_percentil'), 'titulos', ['popularidad_percentil'], unique=False)

    # 3. Generos
    op.create_table(
        'generos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('nombre', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generos_id'), 'generos', ['id'], unique=False)
    op.create_index(op.f('ix_generos_tmdb_id'), 'generos', ['tmdb_id'], unique=True)
    op.create_index(op.f('ix_generos_nombre'), 'generos', ['nombre'], unique=True)

    # 4. Titulos <-> Generos (M:N)
    op.create_table(
        'titulos_generos',
        sa.Column('titulo_id', sa.Integer(), nullable=False),
        sa.Column('genero_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['genero_id'], ['generos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['titulo_id'], ['titulos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('titulo_id', 'genero_id')
    )

    # 5. Actores
    op.create_table(
        'actores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_actores_id'), 'actores', ['id'], unique=False)
    op.create_index(op.f('ix_actores_tmdb_id'), 'actores', ['tmdb_id'], unique=True)
    op.create_index(op.f('ix_actores_nombre'), 'actores', ['nombre'], unique=False)

    # 6. Titulos <-> Elenco (M:N)
    op.create_table(
        'titulos_elenco',
        sa.Column('titulo_id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['actores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['titulo_id'], ['titulos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('titulo_id', 'actor_id')
    )

    # 7. Temporadas
    op.create_table(
        'temporadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titulo_id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('sinopsis', sa.Text(), nullable=True),
        sa.Column('fecha_estreno', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['titulo_id'], ['titulos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('titulo_id', 'numero', name='uq_temporada_titulo_numero')
    )
    op.create_index(op.f('ix_temporadas_id'), 'temporadas', ['id'], unique=False)
    op.create_index(op.f('ix_temporadas_titulo_id'), 'temporadas', ['titulo_id'], unique=False)

    # 8. Episodios
    op.create_table(
        'episodios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('temporada_id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('fecha_estreno', sa.Date(), nullable=True),
        sa.Column('duracion', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['temporada_id'], ['temporadas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('temporada_id', 'numero', name='uq_episodio_temporada_numero')
    )
    op.create_index(op.f('ix_episodios_id'), 'episodios', ['id'], unique=False)
    op.create_index(op.f('ix_episodios_temporada_id'), 'episodios', ['temporada_id'], unique=False)

    # 9. Estados de Usuario sobre Titulos
    op.create_table(
        'estados_usuario_titulos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('titulo_id', sa.Integer(), nullable=False),
        sa.Column('favorito', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fecha_favorito', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=True),
        sa.Column('fecha_estado', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['titulo_id'], ['titulos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('usuario_id', 'titulo_id', name='uq_usuario_titulo_estado')
    )
    op.create_index(op.f('ix_estados_usuario_titulos_id'), 'estados_usuario_titulos', ['id'], unique=False)
    op.create_index(op.f('ix_estados_usuario_titulos_usuario_id'), 'estados_usuario_titulos', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_estados_usuario_titulos_titulo_id'), 'estados_usuario_titulos', ['titulo_id'], unique=False)
    op.create_index(op.f('ix_estados_usuario_titulos_estado'), 'estados_usuario_titulos', ['estado'], unique=False)

    # 10. Episodios Vistos
    op.create_table(
        'episodios_vistos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('episodio_id', sa.Integer(), nullable=False),
        sa.Column('fecha_visto', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['episodio_id'], ['episodios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('usuario_id', 'episodio_id', name='uq_usuario_episodio_visto')
    )
    op.create_index(op.f('ix_episodios_vistos_id'), 'episodios_vistos', ['id'], unique=False)
    op.create_index(op.f('ix_episodios_vistos_usuario_id'), 'episodios_vistos', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_episodios_vistos_episodio_id'), 'episodios_vistos', ['episodio_id'], unique=False)

    # 11. Resenas
    op.create_table(
        'resenas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titulo_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('autor_tmdb', sa.String(length=100), nullable=True),
        sa.Column('puntaje', sa.Float(), nullable=True),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('tmdb_review_id', sa.String(length=100), nullable=True),
        sa.CheckConstraint('(usuario_id IS NOT NULL) OR (autor_tmdb IS NOT NULL)', name='chk_resena_autor_presente'),
        sa.ForeignKeyConstraint(['titulo_id'], ['titulos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resenas_id'), 'resenas', ['id'], unique=False)
    op.create_index(op.f('ix_resenas_titulo_id'), 'resenas', ['titulo_id'], unique=False)
    op.create_index(op.f('ix_resenas_usuario_id'), 'resenas', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_resenas_tmdb_review_id'), 'resenas', ['tmdb_review_id'], unique=True)


def downgrade() -> None:
    op.drop_table('resenas')
    op.drop_table('episodios_vistos')
    op.drop_table('estados_usuario_titulos')
    op.drop_table('episodios')
    op.drop_table('temporadas')
    op.drop_table('titulos_elenco')
    op.drop_table('actores')
    op.drop_table('titulos_generos')
    op.drop_table('generos')
    op.drop_table('titulos')
    op.drop_table('usuarios')
