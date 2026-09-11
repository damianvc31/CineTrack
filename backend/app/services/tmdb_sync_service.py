import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import (
    Actor,
    Episodio,
    Genero,
    Resena,
    Temporada,
    Titulo,
    titulos_elenco,
    titulos_generos,
    EstadoUsuarioTitulo,
)
from app.schemas.import_export import TituloManualImportSchema
from app.services.tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


class TMDBSyncService:
    def __init__(self, db: AsyncSession, client: Optional[TMDBClient] = None):
        self.db = db
        self.client = client or TMDBClient()

    # -------------------------------------------------------------------------
    # GÉNEROS
    # -------------------------------------------------------------------------
    async def sync_genres(self) -> int:
        """Sincroniza el catálogo de géneros de TMDB (películas y series)."""
        logger.info("Sincronizando géneros desde TMDB...")
        movie_genres = await self.client.get_genres("movie")
        tv_genres = await self.client.get_genres("tv")

        all_genres: Dict[int, str] = {}
        for g in movie_genres + tv_genres:
            all_genres[g["id"]] = g["name"]

        count = 0
        for gid, name in all_genres.items():
            result = await self.db.execute(select(Genero).where(Genero.id == gid))
            existing = result.scalar_one_or_none()
            if not existing:
                genero = Genero(id=gid, nombre=name)
                self.db.add(genero)
                count += 1
            else:
                existing.nombre = name

        await self.db.commit()
        logger.info(f"Géneros sincronizados. {count} géneros nuevos agregados.")
        return count

    # -------------------------------------------------------------------------
    # PARSING DE CRÉDITOS Y CAST
    # -------------------------------------------------------------------------
    def _parse_credits(self, credits_data: Dict[str, Any]) -> tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
        crew = credits_data.get("crew", [])
        cast = credits_data.get("cast", [])

        # Director
        directores = [c["name"] for c in crew if c.get("job") == "Director"]
        director = ", ".join(directores[:2]) if directores else None

        # Guionistas (hasta TMDB_CREW_WRITERS_LIMIT)
        guionistas_set = []
        for c in crew:
            if c.get("job") in ("Screenplay", "Writer", "Story"):
                name = c.get("name")
                if name and name not in guionistas_set:
                    guionistas_set.append(name)
        guionista = ", ".join(guionistas_set[:settings.TMDB_CREW_WRITERS_LIMIT]) if guionistas_set else None

        # Elenco (hasta TMDB_CAST_LIMIT)
        cast_sorted = sorted(cast, key=lambda x: x.get("order", 999))
        elenco_list = []
        for member in cast_sorted[:settings.TMDB_CAST_LIMIT]:
            if member.get("name"):
                elenco_list.append({
                    "tmdb_id": member.get("id"),
                    "nombre": member["name"],
                    "personaje": member.get("character"),
                    "orden": member.get("order", 0)
                })

        return director, guionista, elenco_list

    async def _attach_genres(self, titulo: Titulo, genre_ids: List[int]):
        """Asocia géneros existentes por ID al título operando directo en la tabla intermedia."""
        if not genre_ids:
            return
        await self.db.execute(titulos_generos.delete().where(titulos_generos.c.titulo_id == titulo.id))
        for gid in genre_ids:
            res = await self.db.execute(select(Genero.id).where(Genero.id == gid))
            if res.scalar_one_or_none():
                await self.db.execute(
                    titulos_generos.insert().values(titulo_id=titulo.id, genero_id=gid)
                )

    async def _attach_cast(self, titulo: Titulo, elenco_list: List[Dict[str, Any]]):
        """Asocia actores al título en titulos_elenco con personaje y orden."""
        # Limpiar elenco previo si ya existía
        await self.db.execute(titulos_elenco.delete().where(titulos_elenco.c.titulo_id == titulo.id))

        for actor_dict in elenco_list:
            nombre = actor_dict["nombre"]
            tmdb_id = actor_dict.get("tmdb_id")
            personaje = actor_dict.get("personaje")
            orden = actor_dict.get("orden", 0)

            # Buscar o crear actor
            if tmdb_id:
                result = await self.db.execute(select(Actor).where(Actor.tmdb_id == tmdb_id))
            else:
                result = await self.db.execute(select(Actor).where(Actor.nombre == nombre))
            actor = result.scalar_one_or_none()

            if not actor:
                actor = Actor(
                    nombre=nombre,
                    tmdb_id=tmdb_id,
                )
                self.db.add(actor)
                await self.db.flush()

            await self.db.execute(
                titulos_elenco.insert().values(
                    titulo_id=titulo.id,
                    actor_id=actor.id,
                    personaje=personaje,
                    orden=orden,
                )
            )

    # -------------------------------------------------------------------------
    # RESEÑAS DE TMDB
    # -------------------------------------------------------------------------
    async def sync_reviews_for_title(self, titulo: Titulo, limit: Optional[int] = None) -> int:
        """Sincroniza reseñas de TMDB para un título hasta alcanzar el límite configurado (máximo 20)."""
        max_limit = limit or settings.TMDB_REVIEWS_PER_TITLE_LIMIT
        if not titulo.tmdb_id:
            return 0

        # Contar cuántas reseñas de TMDB ya existen para este título
        res_count = await self.db.execute(
            select(func.count(Resena.id)).where(
                Resena.titulo_id == titulo.id,
                Resena.tmdb_review_id.isnot(None)
            )
        )
        current_count = res_count.scalar() or 0
        if current_count >= max_limit:
            return 0

        needed = max_limit - current_count
        try:
            reviews_data = await self.client.get_reviews(titulo.tipo, titulo.tmdb_id)
            results = reviews_data.get("results", [])
        except Exception as e:
            logger.warning(f"No se pudieron obtener reseñas de TMDB para {titulo.nombre}: {e}")
            return 0

        added = 0
        for r in results:
            if added >= needed:
                break
            r_id = r.get("id")
            if not r_id:
                continue

            existing = await self.db.execute(
                select(Resena.id).where(Resena.tmdb_review_id == r_id)
            )
            if existing.scalar_one_or_none():
                continue

            author = r.get("author") or "Usuario TMDB"
            author_details = r.get("author_details", {})
            rating = author_details.get("rating")
            content = r.get("content", "")
            if not content.strip():
                continue

            created_at = None
            if r.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                except Exception:
                    created_at = datetime.now()

            resena = Resena(
                titulo_id=titulo.id,
                usuario_id=None,
                autor_tmdb=author,
                puntaje=float(rating) if rating is not None else None,
                texto=content,
                fecha=created_at or datetime.now(),
                tmdb_review_id=r_id,
            )
            self.db.add(resena)
            added += 1

        return added

    async def sync_all_missing_reviews(
        self,
        limit_per_title: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """Recorre todos los títulos de la base de datos y absorbe reseñas de TMDB hasta completar el tope."""
        effective_limit = limit_per_title if limit_per_title is not None else limit
        logger.info("Iniciando sincronización masiva de reseñas para todos los títulos...")
        res = await self.db.execute(select(Titulo).where(Titulo.tmdb_id.isnot(None)))
        titulos = res.scalars().all()
        
        total_added = 0
        titles_updated = 0
        for titulo in titulos:
            added = await self.sync_reviews_for_title(titulo, limit=effective_limit)
            if added > 0:
                total_added += added
                titles_updated += 1
                await self.db.commit()

        logger.info(f"Sincronización de reseñas completada: {total_added} reseñas agregadas en {titles_updated} títulos.")
        return {"total_reviews_added": total_added, "titles_updated": titles_updated}

    # -------------------------------------------------------------------------
    # UPSERT DE PELÍCULA
    # -------------------------------------------------------------------------
    async def upsert_movie(self, tmdb_id: int, details: Optional[Dict[str, Any]] = None) -> Optional[Titulo]:
        if not details:
            try:
                details = await self.client.get_details("movie", tmdb_id)
            except Exception as e:
                logger.error(f"Error al obtener detalle de película {tmdb_id}: {e}")
                return None

        # Parsear año de estreno
        anio_estreno = None
        rd_str = details.get("release_date")
        if rd_str:
            try:
                anio_estreno = datetime.strptime(rd_str, "%Y-%m-%d").year
            except ValueError:
                pass

        director, guionista, elenco_list = self._parse_credits(details.get("credits", {}))

        # Buscar título existente
        result = await self.db.execute(select(Titulo).where(Titulo.tmdb_id == tmdb_id, Titulo.tipo == "movie"))
        titulo = result.scalar_one_or_none()

        portada = f"https://image.tmdb.org/t/p/w500{details['poster_path']}" if details.get("poster_path") else None
        pais = details.get("origin_country", [""])[0] if details.get("origin_country") else None
        vote_avg = details.get("vote_average", 0.0)
        vote_cnt = details.get("vote_count", 0)
        rating_unif = vote_avg if vote_cnt > 0 else 0.0

        if not titulo:
            titulo = Titulo(
                tmdb_id=tmdb_id,
                tipo="movie",
                nombre=details.get("title", ""),
                sinopsis=details.get("overview"),
                portada_url=portada,
                anio_estreno=anio_estreno,
                duracion=details.get("runtime"),
                director=director,
                guionista=guionista,
                pais=pais,
                idioma_original=details.get("original_language"),
                popularidad=details.get("popularity", 0.0),
                vote_average_tmdb=vote_avg,
                vote_count_tmdb=vote_cnt,
                rating_unificado=rating_unif,
                status_tmdb=details.get("status"),
            )
            self.db.add(titulo)
            await self.db.flush()
        else:
            titulo.nombre = details.get("title", titulo.nombre)
            titulo.sinopsis = details.get("overview", titulo.sinopsis)
            titulo.portada_url = portada or titulo.portada_url
            titulo.anio_estreno = anio_estreno or titulo.anio_estreno
            titulo.duracion = details.get("runtime", titulo.duracion)
            titulo.director = director or titulo.director
            titulo.guionista = guionista or titulo.guionista
            titulo.pais = pais or titulo.pais
            titulo.idioma_original = details.get("original_language", titulo.idioma_original)
            titulo.popularidad = details.get("popularity", titulo.popularidad)
            titulo.vote_average_tmdb = vote_avg
            titulo.vote_count_tmdb = vote_cnt
            titulo.rating_unificado = rating_unif
            titulo.status_tmdb = details.get("status", titulo.status_tmdb)

        # Géneros
        genre_ids = [g["id"] for g in details.get("genres", []) if "id" in g]
        await self._attach_genres(titulo, genre_ids)

        # Elenco
        await self._attach_cast(titulo, elenco_list)

        # Reseñas de TMDB (hasta 20)
        await self.sync_reviews_for_title(titulo)

        return titulo

    # -------------------------------------------------------------------------
    # UPSERT DE SERIE
    # -------------------------------------------------------------------------
    async def upsert_series(self, tmdb_id: int, details: Optional[Dict[str, Any]] = None, fetch_episodes: bool = True) -> Optional[Titulo]:
        if not details:
            try:
                details = await self.client.get_details("tv", tmdb_id)
            except Exception as e:
                logger.error(f"Error al obtener detalle de serie {tmdb_id}: {e}")
                return None

        # Parsear año de estreno y año de fin
        anio_estreno = None
        fad_str = details.get("first_air_date")
        if fad_str:
            try:
                anio_estreno = datetime.strptime(fad_str, "%Y-%m-%d").year
            except ValueError:
                pass

        anio_fin = None
        status = details.get("status")
        lad_str = details.get("last_air_date")
        if status in ("Ended", "Canceled") and lad_str:
            try:
                anio_fin = datetime.strptime(lad_str, "%Y-%m-%d").year
            except ValueError:
                pass

        # Próximo episodio
        next_ep = details.get("next_episode_to_air")
        fecha_prox_ep = None
        if next_ep and next_ep.get("air_date"):
            try:
                fecha_prox_ep = datetime.strptime(next_ep["air_date"], "%Y-%m-%d").date()
            except ValueError:
                pass

        director, guionista, elenco_list = self._parse_credits(details.get("credits", {}))
        if not director and details.get("created_by"):
            creators = [c["name"] for c in details["created_by"] if "name" in c]
            director = ", ".join(creators[:2])

        result = await self.db.execute(select(Titulo).where(Titulo.tmdb_id == tmdb_id, Titulo.tipo == "tv"))
        titulo = result.scalar_one_or_none()

        portada = f"https://image.tmdb.org/t/p/w500{details['poster_path']}" if details.get("poster_path") else None
        pais = details.get("origin_country", [""])[0] if details.get("origin_country") else None
        vote_avg = details.get("vote_average", 0.0)
        vote_cnt = details.get("vote_count", 0)
        rating_unif = vote_avg if vote_cnt > 0 else 0.0

        if not titulo:
            titulo = Titulo(
                tmdb_id=tmdb_id,
                tipo="tv",
                nombre=details.get("name", ""),
                sinopsis=details.get("overview"),
                portada_url=portada,
                anio_estreno=anio_estreno,
                anio_fin=anio_fin,
                duracion=details.get("episode_run_time", [None])[0] if details.get("episode_run_time") else None,
                director=director,
                guionista=guionista,
                pais=pais,
                idioma_original=details.get("original_language"),
                popularidad=details.get("popularity", 0.0),
                vote_average_tmdb=vote_avg,
                vote_count_tmdb=vote_cnt,
                rating_unificado=rating_unif,
                status_tmdb=status,
                proximo_episodio_fecha=fecha_prox_ep,
            )
            self.db.add(titulo)
            await self.db.flush()
        else:
            titulo.nombre = details.get("name", titulo.nombre)
            titulo.sinopsis = details.get("overview", titulo.sinopsis)
            titulo.portada_url = portada or titulo.portada_url
            titulo.anio_estreno = anio_estreno or titulo.anio_estreno
            titulo.anio_fin = anio_fin
            titulo.director = director or titulo.director
            titulo.guionista = guionista or titulo.guionista
            titulo.pais = pais or titulo.pais
            titulo.idioma_original = details.get("original_language", titulo.idioma_original)
            titulo.popularidad = details.get("popularity", titulo.popularidad)
            titulo.vote_average_tmdb = vote_avg
            titulo.vote_count_tmdb = vote_cnt
            titulo.rating_unificado = rating_unif
            titulo.status_tmdb = details.get("status", titulo.status_tmdb)
            titulo.proximo_episodio_fecha = fecha_prox_ep

        # Géneros
        genre_ids = [g["id"] for g in details.get("genres", []) if "id" in g]
        await self._attach_genres(titulo, genre_ids)

        # Elenco
        await self._attach_cast(titulo, elenco_list)

        # Temporadas y Episodios
        if fetch_episodes:
            seasons_info = details.get("seasons", [])
            for s_info in seasons_info:
                s_num = s_info.get("season_number")
                if s_num is None or s_num < 1:  # Ignorar especiales (temporada 0)
                    continue

                try:
                    s_details = await self.client.get_season_details(tmdb_id, s_num)
                except Exception as e:
                    logger.warning(f"No se pudo obtener temporada {s_num} de serie {tmdb_id}: {e}")
                    continue

                res_temp = await self.db.execute(
                    select(Temporada).where(
                        Temporada.titulo_id == titulo.id,
                        Temporada.numero == s_num
                    )
                )
                temporada = res_temp.scalar_one_or_none()
                if not temporada:
                    temporada = Temporada(
                        titulo_id=titulo.id,
                        numero=s_num,
                        sinopsis=s_details.get("overview"),
                    )
                    self.db.add(temporada)
                    await self.db.flush()
                else:
                    temporada.sinopsis = s_details.get("overview", temporada.sinopsis)

                # Episodios de la temporada
                for ep_data in s_details.get("episodes", []):
                    ep_num = ep_data.get("episode_number")
                    if ep_num is None:
                        continue

                    ep_air_date = None
                    ep_ad_str = ep_data.get("air_date")
                    if ep_ad_str:
                        try:
                            ep_air_date = datetime.strptime(ep_ad_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass

                    res_ep = await self.db.execute(
                        select(Episodio).where(
                            Episodio.temporada_id == temporada.id,
                            Episodio.numero == ep_num
                        )
                    )
                    episodio = res_ep.scalar_one_or_none()
                    if not episodio:
                        episodio = Episodio(
                            temporada_id=temporada.id,
                            numero=ep_num,
                            nombre=ep_data.get("name", f"Episodio {ep_num}"),
                            fecha_estreno=ep_air_date,
                            duracion=ep_data.get("runtime"),
                        )
                        self.db.add(episodio)
                    else:
                        episodio.nombre = ep_data.get("name", episodio.nombre)
                        episodio.fecha_estreno = ep_air_date or episodio.fecha_estreno
                        episodio.duracion = ep_data.get("runtime", episodio.duracion)

        # Reseñas de TMDB (hasta 20)
        await self.sync_reviews_for_title(titulo)

        return titulo

    # -------------------------------------------------------------------------
    # INGESTA INICIAL
    # -------------------------------------------------------------------------
    async def run_initial_ingest(
        self,
        priority: Optional[str] = None,
        movies_target: Optional[int] = None,
        series_target: Optional[int] = None
    ) -> Dict[str, int]:
        prio = priority or settings.TMDB_INGEST_PRIORITY
        logger.info(f"Iniciando Ingesta Inicial con prioridad: {prio}")

        # Sincronizar géneros primero
        await self.sync_genres()

        movie_target = movies_target or settings.TMDB_INGEST_MOVIES_TARGET
        series_target = series_target or settings.TMDB_INGEST_SERIES_TARGET
        min_votes = settings.TMDB_MIN_VOTE_COUNT

        movies_added = await self._ingest_media_pool("movie", movie_target, prio, min_votes)
        series_added = await self._ingest_media_pool("tv", series_target, prio, min_votes)

        await self.recalculate_percentiles()
        await self.recalculate_unified_ratings()
        logger.info(f"Ingesta inicial completada: {movies_added} películas, {series_added} series.")
        return {"movies_added": movies_added, "series_added": series_added}

    async def _ingest_media_pool(self, media_type: str, target_count: int, priority: str, min_votes: int) -> int:
        half_target = target_count // 2
        collected_ids: Set[int] = set()

        # Consulta IDs existentes en BD para no duplicar
        existing_res = await self.db.execute(select(Titulo.tmdb_id).where(Titulo.tipo == media_type))
        existing_ids = set(existing_res.scalars().all())
        collected_ids.update(existing_ids)

        initial_count = len(existing_ids)
        newly_added = 0

        async def harvest_ids(sort_by: str, limit: int, vote_count_gte: Optional[int] = None):
            nonlocal newly_added
            page = 1
            while len(collected_ids) - initial_count < limit and page <= 50:
                data = await self.client.discover(
                    media_type=media_type,
                    sort_by=sort_by,
                    page=page,
                    vote_count_gte=vote_count_gte,
                )
                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    tmdb_id = item["id"]
                    if tmdb_id not in collected_ids:
                        try:
                            if media_type == "movie":
                                await self.upsert_movie(tmdb_id)
                            else:
                                await self.upsert_series(tmdb_id, fetch_episodes=True)
                            collected_ids.add(tmdb_id)
                            newly_added += 1
                            await self.db.commit()
                        except Exception as e:
                            logger.error(f"Error importando {media_type} id {tmdb_id}: {e}")
                            await self.db.rollback()

                        if len(collected_ids) - initial_count >= limit:
                            break

                page += 1

        if priority == "popular_first":
            # 1. Populares hasta half_target
            await harvest_ids(sort_by="popularity.desc", limit=half_target)
            # 2. Top-rated hasta target_count
            await harvest_ids(sort_by="vote_average.desc", limit=target_count, vote_count_gte=min_votes)
        else:
            # 1. Top-rated hasta half_target
            await harvest_ids(sort_by="vote_average.desc", limit=half_target, vote_count_gte=min_votes)
            # 2. Populares hasta target_count
            await harvest_ids(sort_by="popularity.desc", limit=target_count)

        return newly_added

    # -------------------------------------------------------------------------
    # SINCRONIZACIÓN DIARIA (CON /CHANGES Y SEGUIMIENTO)
    # -------------------------------------------------------------------------
    async def run_daily_sync(self, hours_window: Optional[int] = None) -> Dict[str, int]:
        """
        Sincronización diaria:
        1. Consulta TMDB /tv/changes (últimas horas_window o config) y cruza con nuestra BD local para detectar
           series con nuevos episodios o cambio de estado, aun si nadie las sigue todavía.
        2. Garantiza la actualización de cualquier serie activamente seguida por usuarios (siguiendo).
        3. Consulta TMDB /movie/changes para actualizar ratings/metadatos de películas de nuestro catálogo.
        4. Ingesta estrenos recientes en cartelera (ventana de 15 días, popularidad >= 10.0).
        5. Recalcula percentiles de popularidad y ratings unificados.
        """
        logger.info("Iniciando Sincronización Diaria...")
        today = date.today()
        h_window = hours_window or settings.TMDB_CHANGES_HOURS_WINDOW
        days_back = max(1, (h_window + 23) // 24)
        yesterday = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_end = today.strftime("%Y-%m-%d")
        window_days = settings.TMDB_DAILY_SYNC_DAYS_WINDOW
        pop_threshold = settings.TMDB_DAILY_SYNC_POP_THRESHOLD
        date_start = (today - timedelta(days=window_days)).strftime("%Y-%m-%d")

        # 1. Obtener IDs cambiados en TMDB para TV
        changed_tv_ids: Set[int] = set()
        try:
            tv_changes = await self.client.get_changes("tv", start_date=yesterday, end_date=date_end)
            for item in tv_changes.get("results", []):
                changed_tv_ids.add(item["id"])
        except Exception as e:
            logger.warning(f"No se pudo consultar TMDB /tv/changes: {e}")

        # 2. Obtener series de nuestra BD que cambiaron en TMDB O que tienen usuarios en 'siguiendo'
        active_series_q = select(Titulo.tmdb_id).distinct().join(
            EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id
        ).where(
            Titulo.tipo == "tv",
            EstadoUsuarioTitulo.estado == "siguiendo"
        )
        res_active = await self.db.execute(active_series_q)
        tracked_tmdb_ids = set(res_active.scalars().all())

        # Si tenemos series locales que coinciden con los cambios de TMDB
        local_tv_q = select(Titulo.tmdb_id).where(Titulo.tipo == "tv")
        res_local_tv = await self.db.execute(local_tv_q)
        local_tv_ids = set(res_local_tv.scalars().all())

        # Unión: Series seguidas + Series locales que tuvieron cambios en TMDB
        tv_to_update = tracked_tmdb_ids.union(local_tv_ids.intersection(changed_tv_ids))

        updated_series_count = 0
        for tmdb_id in tv_to_update:
            if tmdb_id:
                try:
                    await self.upsert_series(tmdb_id, fetch_episodes=True)
                    updated_series_count += 1
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"Error actualizando serie id {tmdb_id}: {e}")
                    await self.db.rollback()

        # 3. Consultar /movie/changes y refrescar películas locales modificadas
        try:
            movie_changes = await self.client.get_changes("movie", start_date=yesterday, end_date=date_end)
            changed_movie_ids = {item["id"] for item in movie_changes.get("results", [])}
            local_movie_q = select(Titulo.tmdb_id).where(Titulo.tipo == "movie")
            res_local_movies = await self.db.execute(local_movie_q)
            local_movie_ids = set(res_local_movies.scalars().all())
            movies_to_update = local_movie_ids.intersection(changed_movie_ids)
            for m_id in movies_to_update:
                try:
                    await self.upsert_movie(m_id)
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"Error actualizando película cambiada id {m_id}: {e}")
                    await self.db.rollback()
        except Exception as e:
            logger.warning(f"No se pudo sincronizar /movie/changes: {e}")

        # 4. Ingestar nuevos estrenos calificados
        new_movies_count = 0
        page = 1
        while page <= 5:
            data = await self.client.discover(
                media_type="movie",
                sort_by="popularity.desc",
                page=page,
                release_date_gte=date_start,
                release_date_lte=date_end,
            )
            results = data.get("results", [])
            if not results:
                break
            for item in results:
                if item.get("popularity", 0) >= pop_threshold:
                    tmdb_id = item["id"]
                    res = await self.db.execute(select(Titulo.id).where(Titulo.tmdb_id == tmdb_id, Titulo.tipo == "movie"))
                    if not res.scalar_one_or_none():
                        try:
                            await self.upsert_movie(tmdb_id)
                            new_movies_count += 1
                            await self.db.commit()
                        except Exception as e:
                            logger.error(f"Error ingesting new movie {tmdb_id}: {e}")
                            await self.db.rollback()
            page += 1

        # 5. Recalcular percentiles y ratings unificados con los nuevos títulos
        await self.recalculate_percentiles()
        await self.recalculate_unified_ratings()

        logger.info(f"Sincronización diaria terminada: {updated_series_count} series actualizadas, {new_movies_count} nuevos estrenos.")
        return {"updated_series": updated_series_count, "new_movies": new_movies_count}

    # -------------------------------------------------------------------------
    # CARGA MANUAL POR JSON
    # -------------------------------------------------------------------------
    async def import_from_json_data(self, items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Importa títulos desde una lista de diccionarios con esquema TituloManualImportSchema."""
        imported_count = 0
        errors = []

        for idx, item_raw in enumerate(items_data):
            try:
                # Validar con Pydantic
                item = TituloManualImportSchema.model_validate(item_raw)
                tmdb_id = item.id_tmdb

                # Si no viene id_tmdb, buscar automáticamente en TMDB
                if not tmdb_id:
                    year = item.fecha_estreno.year if item.fecha_estreno else None
                    search_res = await self.client.search(item.tipo, item.titulo, year=year)
                    results = search_res.get("results", [])
                    if results:
                        tmdb_id = results[0]["id"]
                        logger.info(f"Coincidencia automática encontrada para '{item.titulo}' -> TMDB ID {tmdb_id}")

                if tmdb_id:
                    # Enriquecer directo desde TMDB
                    if item.tipo == "movie":
                        await self.upsert_movie(tmdb_id)
                    else:
                        await self.upsert_series(tmdb_id, fetch_episodes=True)
                    await self.db.commit()
                    imported_count += 1
                else:
                    # Regla estricta: No se permiten títulos huérfanos sin respaldo en TMDB
                    err_msg = f"No se encontró coincidencia en TMDB para '{item.titulo}' y no se proveyó id_tmdb. Registro omitido."
                    logger.warning(err_msg)
                    errors.append(err_msg)
            except Exception as e:
                await self.db.rollback()
                err_msg = f"Error en elemento {idx} ({item_raw.get('titulo', 'Sin título')}): {str(e)}"
                logger.error(err_msg)
                errors.append(err_msg)

        if imported_count > 0:
            await self.recalculate_percentiles()
            await self.recalculate_unified_ratings()
        return {"imported": imported_count, "errors": errors}

    # -------------------------------------------------------------------------
    # RECÁLCULO DE PERCENTILES
    # -------------------------------------------------------------------------
    async def recalculate_percentiles(self):
        """Calcula percentiles de popularidad (0.0 a 1.0) para todos los títulos."""
        logger.info("Recalculando percentiles de popularidad...")
        query = text("""
            WITH ranked AS (
                SELECT id, PERCENT_RANK() OVER (ORDER BY popularidad ASC) as pct
                FROM titulos
            )
            UPDATE titulos
            SET popularidad_percentil = (
                SELECT pct FROM ranked WHERE ranked.id = titulos.id
            )
        """)
        try:
            await self.db.execute(query)
            await self.db.commit()
            logger.info("Percentiles de popularidad recalculados con éxito.")
        except Exception as e:
            logger.warning(f"Error recalculando percentiles con SQL directo: {e}. Aplicando cálculo en memoria...")
            await self.db.rollback()
            res = await self.db.execute(select(Titulo.id, Titulo.popularidad).order_by(Titulo.popularidad.asc()))
            rows = res.all()
            n = len(rows)
            if n > 1:
                for rank, (tid, _) in enumerate(rows):
                    pct = rank / (n - 1)
                    await self.db.execute(update(Titulo).where(Titulo.id == tid).values(popularidad_percentil=pct))
                await self.db.commit()

    # -------------------------------------------------------------------------
    # RECÁLCULO DE RATING UNIFICADO
    # -------------------------------------------------------------------------
    async def recalculate_unified_ratings(self, titulo_id: Optional[int] = None) -> int:
        """
        Recalcula el Rating Unificado ponderado:
        [(vote_average_tmdb * vote_count_tmdb) + sum(puntajes_usuarios)] / [vote_count_tmdb + N]
        donde N es el total de reseñas locales de usuarios con puntaje.
        """
        logger.info("Recalculando rating unificado...")
        query = select(Titulo)
        if titulo_id:
            query = query.where(Titulo.id == titulo_id)
        res = await self.db.execute(query)
        titulos = res.scalars().all()

        for tit in titulos:
            q_res = select(
                func.coalesce(func.sum(Resena.puntaje), 0.0),
                func.count(Resena.id)
            ).where(
                Resena.titulo_id == tit.id,
                Resena.usuario_id.isnot(None),
                Resena.puntaje.isnot(None)
            )
            r = await self.db.execute(q_res)
            sum_users, count_users = r.one()
            total_votes = tit.vote_count_tmdb + count_users
            if total_votes > 0:
                tit.rating_unificado = round(((tit.vote_average_tmdb * tit.vote_count_tmdb) + float(sum_users)) / total_votes, 2)
            else:
                tit.rating_unificado = 0.0

        await self.db.commit()
        logger.info(f"Rating unificado recalculado para {len(titulos)} títulos.")
        return len(titulos)

