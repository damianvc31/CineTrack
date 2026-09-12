from datetime import date, datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.actor import Actor
from app.models.episodio import Episodio
from app.models.episodio_visto import EpisodioVisto
from app.models.estado import EstadoUsuarioTitulo
from app.models.genero import Genero
from app.models.resena import Resena
from app.models.temporada import Temporada
from app.models.titulo import Titulo
from app.models.usuario import Usuario


@pytest.mark.asyncio
async def test_crear_usuario_y_unicidad(db_session: AsyncSession):
    """Verifica creación de usuario y constraint de nombre_usuario único."""
    user1 = Usuario(
        nombre_usuario="damian",
        password_hash="hashed_secret_123",
        pais="Argentina",
        ciudad="Buenos Aires"
    )
    db_session.add(user1)
    await db_session.commit()

    assert user1.id is not None
    assert user1.nombre_usuario == "damian"
    assert user1.fecha_registro is not None

    # Intentar crear duplicado con el mismo nombre_usuario debe lanzar IntegrityError
    user_dup = Usuario(
        nombre_usuario="damian",
        password_hash="another_hash"
    )
    db_session.add(user_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_crear_pelicula_y_serie_con_temporadas(db_session: AsyncSession):
    """Verifica creación de película (con duración) y serie con jerarquía de temporadas y episodios."""
    # Película
    pelicula = Titulo(
        tmdb_id=101,
        tipo="movie",
        nombre="Inception",
        sinopsis="Un ladrón que roba secretos corporativos a través de sueños.",
        anio_estreno=2010,
        duracion=148,
        director="Christopher Nolan",
        popularidad=85.5,
        popularidad_percentil=98.0,
        vote_average_tmdb=8.4,
        vote_count_tmdb=35000
    )
    db_session.add(pelicula)

    # Serie con Temporada y Episodios
    serie = Titulo(
        tmdb_id=201,
        tipo="tv",
        nombre="Breaking Bad",
        sinopsis="Un profesor de química se convierte en narcotraficante.",
        anio_estreno=2008,
        anio_fin=2013,
        status_tmdb="Ended",
        popularidad=95.0,
        popularidad_percentil=99.5,
        vote_average_tmdb=8.9,
        vote_count_tmdb=14000
    )
    temp1 = Temporada(
        titulo=serie,
        numero=1,
        sinopsis="Primera temporada",
        fecha_estreno=date(2008, 1, 20)
    )
    ep1 = Episodio(
        temporada=temp1,
        numero=1,
        nombre="Pilot",
        duracion=58,
        fecha_estreno=date(2008, 1, 20)
    )
    ep2 = Episodio(
        temporada=temp1,
        numero=2,
        nombre="Cat's in the Bag...",
        duracion=48,
        fecha_estreno=date(2008, 1, 27)
    )

    db_session.add(serie)
    await db_session.commit()

    # Consultar serie con temporadas y episodios cargados
    query = (
        select(Titulo)
        .where(Titulo.tmdb_id == 201)
        .options(selectinload(Titulo.temporadas).selectinload(Temporada.episodios))
    )
    res = await db_session.execute(query)
    serie_db = res.scalar_one()

    assert serie_db.tipo == "tv"
    assert len(serie_db.temporadas) == 1
    assert serie_db.temporadas[0].numero == 1
    assert len(serie_db.temporadas[0].episodios) == 2
    assert serie_db.temporadas[0].episodios[0].nombre == "Pilot"


@pytest.mark.asyncio
async def test_relaciones_muchos_a_muchos(db_session: AsyncSession):
    """Verifica asociaciones N:M entre Títulos, Géneros y Actores."""
    titulo = Titulo(
        tmdb_id=301,
        tipo="movie",
        nombre="Interstellar",
        anio_estreno=2014
    )
    genero_scifi = Genero(tmdb_id=878, nombre="Science Fiction")
    genero_drama = Genero(tmdb_id=18, nombre="Drama")
    actor_mcconaughey = Actor(tmdb_id=10297, nombre="Matthew McConaughey")

    titulo.generos.extend([genero_scifi, genero_drama])
    titulo.actores.append(actor_mcconaughey)

    db_session.add(titulo)
    await db_session.commit()

    # Verificar desde Título
    query = (
        select(Titulo)
        .where(Titulo.id == titulo.id)
        .options(selectinload(Titulo.generos), selectinload(Titulo.actores))
    )
    res = await db_session.execute(query)
    titulo_db = res.scalar_one()

    assert len(titulo_db.generos) == 2
    assert len(titulo_db.actores) == 1
    assert titulo_db.actores[0].nombre == "Matthew McConaughey"

    # Verificar relación inversa desde Género
    query_gen = select(Genero).where(Genero.nombre == "Science Fiction").options(selectinload(Genero.titulos))
    res_gen = await db_session.execute(query_gen)
    gen_db = res_gen.scalar_one()
    assert len(gen_db.titulos) == 1
    assert gen_db.titulos[0].nombre == "Interstellar"


@pytest.mark.asyncio
async def test_estados_usuario_titulo_y_unicidad(db_session: AsyncSession):
    """Verifica la máquina de estados granular y la unicidad de relación (usuario, titulo)."""
    usuario = Usuario(nombre_usuario="cinefilo", password_hash="hash")
    titulo = Titulo(tmdb_id=401, tipo="movie", nombre="The Matrix")
    db_session.add_all([usuario, titulo])
    await db_session.commit()

    # Usuario marca favorito y watchlist
    ahora = datetime.now(timezone.utc)
    estado = EstadoUsuarioTitulo(
        usuario=usuario,
        titulo=titulo,
        favorito=True,
        fecha_favorito=ahora,
        estado="watchlist",
        fecha_estado=ahora
    )
    db_session.add(estado)
    await db_session.commit()

    assert estado.id is not None
    assert estado.favorito is True
    assert estado.estado == "watchlist"

    # Transición de estado a 'vista'
    estado.estado = "vista"
    estado.fecha_estado = datetime.now(timezone.utc)
    await db_session.commit()

    # Intentar insertar un segundo registro para la misma dupla (usuario, titulo) debe fallar
    dup_estado = EstadoUsuarioTitulo(
        usuario_id=usuario.id,
        titulo_id=titulo.id,
        favorito=False,
        estado="siguiendo"
    )
    db_session.add(dup_estado)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_episodio_visto_historial(db_session: AsyncSession):
    """Verifica registro granular de episodios vistos y unicidad (usuario, episodio)."""
    usuario = Usuario(nombre_usuario="seriefilo", password_hash="hash")
    serie = Titulo(tmdb_id=501, tipo="tv", nombre="Dark")
    temp = Temporada(titulo=serie, numero=1)
    ep = Episodio(temporada=temp, numero=1, nombre="Secrets")

    db_session.add_all([usuario, serie, temp, ep])
    await db_session.commit()

    visto = EpisodioVisto(usuario=usuario, episodio=ep)
    db_session.add(visto)
    await db_session.commit()

    assert visto.id is not None
    assert visto.fecha_visto is not None

    # Intentar registrar el mismo episodio como visto dos veces para el mismo usuario falla
    dup_visto = EpisodioVisto(usuario_id=usuario.id, episodio_id=ep.id)
    db_session.add(dup_visto)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_resenas_polimorficas(db_session: AsyncSession):
    """Verifica soporte de reseñas propias de usuarios y de TMDB con autor polimórfico."""
    usuario = Usuario(nombre_usuario="critico", password_hash="hash")
    titulo = Titulo(tmdb_id=601, tipo="movie", nombre="Pulp Fiction")
    db_session.add_all([usuario, titulo])
    await db_session.commit()

    # Reseña de usuario propio con puntaje
    resena_usuario = Resena(
        titulo=titulo,
        usuario=usuario,
        puntaje=9.5,
        texto="Una obra maestra del cine independiente."
    )
    # Reseña importada de TMDB con autor texto y sin usuario_id
    resena_tmdb = Resena(
        titulo=titulo,
        autor_tmdb="tmdb_critic_42",
        puntaje=8.0,
        texto="Iconic non-linear storytelling.",
        tmdb_review_id="tmdb_rev_9999"
    )
    db_session.add_all([resena_usuario, resena_tmdb])
    await db_session.commit()

    assert resena_usuario.id is not None
    assert resena_usuario.autor_tmdb is None
    assert resena_usuario.usuario_id == usuario.id

    assert resena_tmdb.id is not None
    assert resena_tmdb.usuario_id is None
    assert resena_tmdb.autor_tmdb == "tmdb_critic_42"

    # Deduplicación de reseñas TMDB: reintentar con el mismo tmdb_review_id debe fallar
    resena_dup = Resena(
        titulo=titulo,
        autor_tmdb="another_author",
        texto="Another review",
        tmdb_review_id="tmdb_rev_9999"
    )
    db_session.add(resena_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_pelicula_y_serie_mismo_tmdb_id(db_session: AsyncSession):
    """Verifica que una película y una serie puedan coexistir con el mismo tmdb_id, pero no dos del mismo tipo."""
    m = Titulo(
        tmdb_id=121,
        tipo="movie",
        nombre="The Lord of the Rings",
        popularidad=100.0
    )
    s = Titulo(
        tmdb_id=121,
        tipo="tv",
        nombre="Doctor Who",
        popularidad=80.0
    )
    db_session.add_all([m, s])
    await db_session.commit()

    assert m.id is not None
    assert s.id is not None
    assert m.id != s.id
    assert m.tmdb_id == s.tmdb_id == 121

    # Intentar agregar otra película con el mismo tmdb_id=121 debe fallar por duplicado
    m_dup = Titulo(
        tmdb_id=121,
        tipo="movie",
        nombre="Another LOTR",
        popularidad=50.0
    )
    db_session.add(m_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

