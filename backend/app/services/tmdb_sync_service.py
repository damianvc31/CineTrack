import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import delete, func, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.text_utils import extract_tmdb_countries, is_latin_legible
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
                profile_path = member.get("profile_path")
                foto_url = f"https://image.tmdb.org/t/p/w185{profile_path}" if profile_path else None
                elenco_list.append({
                    "tmdb_id": member.get("id"),
                    "nombre": member["name"],
                    "personaje": member.get("character"),
                    "orden": member.get("order", 0),
                    "foto_url": foto_url
                })

        return director, guionista, elenco_list

    async def _attach_genres(self, titulo: Titulo, genre_ids: List[int]):
        """Asocia géneros existentes por ID al título operando directo en la tabla intermedia."""
        if not genre_ids:
            return
        await self.db.execute(titulos_generos.delete().where(titulos_generos.c.titulo_id == titulo.id))
        for gid in set(genre_ids):
            res = await self.db.execute(select(Genero.id).where(Genero.id == gid))
            if res.scalar_one_or_none():
                await self.db.execute(
                    titulos_generos.insert().values(titulo_id=titulo.id, genero_id=gid)
                )

    async def _attach_cast(self, titulo: Titulo, elenco_list: List[Dict[str, Any]]):
        """Asocia actores al título en titulos_elenco con personaje y orden, evitando duplicados."""
        # Limpiar elenco previo si ya existía
        await self.db.execute(titulos_elenco.delete().where(titulos_elenco.c.titulo_id == titulo.id))

        attached_actor_ids: set[int] = set()
        for actor_dict in elenco_list:
            nombre = actor_dict["nombre"]
            tmdb_id = actor_dict.get("tmdb_id")
            personaje = actor_dict.get("personaje")
            orden = actor_dict.get("orden", 0)
            foto_url = actor_dict.get("foto_url")

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
                    foto_url=foto_url,
                )
                self.db.add(actor)
                await self.db.flush()
            elif foto_url and not actor.foto_url:
                actor.foto_url = foto_url

            # Evitar insertar dos veces el mismo par (titulo_id, actor_id)
            if actor.id in attached_actor_ids:
                continue

            attached_actor_ids.add(actor.id)
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
    async def upsert_movie(
        self,
        tmdb_id: int,
        details: Optional[Dict[str, Any]] = None,
        allow_unreleased: Optional[bool] = None,
        fetch_reviews: bool = True,
    ) -> Optional[Titulo]:
        if not details:
            try:
                details = await self.client.get_details("movie", tmdb_id)
            except Exception as e:
                logger.error(f"Error al obtener detalle de película {tmdb_id}: {e}")
                return None

        # Parsear fecha de estreno
        fecha_estreno = None
        rd_str = details.get("release_date")
        if rd_str:
            try:
                fecha_estreno = datetime.strptime(rd_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        allow_unrel = settings.TMDB_ALLOW_UNRELEASED if allow_unreleased is None else allow_unreleased
        today = date.today()
        status = details.get("status")
        if not allow_unrel and (fecha_estreno is None or fecha_estreno > today or (status and status != "Released")):
            logger.info(f"Omitiendo película no estrenada (TMDB ID: {tmdb_id}, fecha_estreno: {fecha_estreno}, status: {status})")
            return None

        director, guionista, elenco_list = self._parse_credits(details.get("credits", {}))
        nombre = details.get("title", "")
        idioma = details.get("original_language")
        pais = extract_tmdb_countries(details)

        # Filtro de Calidad Mínima y Legibilidad
        if not is_latin_legible(nombre):
            logger.info(f"Omitiendo película no legible en alfabeto no latino (TMDB ID: {tmdb_id}, nombre: {nombre})")
            return None

        if not allow_unrel and (fecha_estreno is None or not idioma or not pais):
            logger.info(f"Omitiendo película con metadatos incompletos (TMDB ID: {tmdb_id}, fecha: {fecha_estreno}, idioma: {idioma}, pais: {pais})")
            return None

        # Buscar título existente
        result = await self.db.execute(select(Titulo).where(Titulo.tmdb_id == tmdb_id, Titulo.tipo == "movie"))
        titulo = result.scalar_one_or_none()

        portada = f"https://image.tmdb.org/t/p/w500{details['poster_path']}" if details.get("poster_path") else None
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
                fecha_estreno=fecha_estreno,
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
            titulo.fecha_estreno = fecha_estreno or titulo.fecha_estreno
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
        if fetch_reviews:
            await self.sync_reviews_for_title(titulo)

        return titulo

    # -------------------------------------------------------------------------
    # UPSERT DE SERIE
    # -------------------------------------------------------------------------
    async def upsert_series(
        self,
        tmdb_id: int,
        details: Optional[Dict[str, Any]] = None,
        fetch_episodes: bool = True,
        allow_unreleased: Optional[bool] = None,
        fetch_reviews: bool = True,
    ) -> Optional[Titulo]:
        if not details:
            try:
                details = await self.client.get_details("tv", tmdb_id)
            except Exception as e:
                logger.error(f"Error al obtener detalle de serie {tmdb_id}: {e}")
                return None

        # Parsear fecha de estreno y fecha de fin
        fecha_estreno = None
        fad_str = details.get("first_air_date")
        if fad_str:
            try:
                fecha_estreno = datetime.strptime(fad_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        allow_unrel = settings.TMDB_ALLOW_UNRELEASED if allow_unreleased is None else allow_unreleased
        today = date.today()
        has_aired_season = False
        if fecha_estreno and fecha_estreno <= today:
            has_aired_season = True
        else:
            for s_info in details.get("seasons", []):
                s_num = s_info.get("season_number")
                s_ad = s_info.get("air_date")
                if s_num is not None and s_num >= 1 and s_ad:
                    try:
                        if datetime.strptime(s_ad, "%Y-%m-%d").date() <= today:
                            has_aired_season = True
                            break
                    except ValueError:
                        pass

        if not allow_unrel and (fecha_estreno is None or fecha_estreno > today or not has_aired_season):
            logger.info(f"Omitiendo serie no estrenada (TMDB ID: {tmdb_id}, fecha_estreno: {fecha_estreno})")
            return None

        fecha_fin = None
        status = details.get("status")
        lad_str = details.get("last_air_date")
        if status in ("Ended", "Canceled") and lad_str:
            try:
                fecha_fin = datetime.strptime(lad_str, "%Y-%m-%d").date()
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

        nombre = details.get("name", "")
        idioma = details.get("original_language")
        pais = extract_tmdb_countries(details)

        # Filtro de Calidad Mínima y Legibilidad
        if not is_latin_legible(nombre):
            logger.info(f"Omitiendo serie no legible en alfabeto no latino (TMDB ID: {tmdb_id}, nombre: {nombre})")
            return None

        if not allow_unrel and (fecha_estreno is None or not idioma or not pais):
            logger.info(f"Omitiendo serie con metadatos incompletos (TMDB ID: {tmdb_id}, fecha: {fecha_estreno}, idioma: {idioma}, pais: {pais})")
            return None

        result = await self.db.execute(select(Titulo).where(Titulo.tmdb_id == tmdb_id, Titulo.tipo == "tv"))
        titulo = result.scalar_one_or_none()

        portada = f"https://image.tmdb.org/t/p/w500{details['poster_path']}" if details.get("poster_path") else None
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
                fecha_estreno=fecha_estreno,
                fecha_fin=fecha_fin,
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
            titulo.fecha_estreno = fecha_estreno or titulo.fecha_estreno
            titulo.fecha_fin = fecha_fin
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
            valid_seasons = [s for s in seasons_info if s.get("season_number") is not None and s.get("season_number") >= 1]
            max_s_num = max([s["season_number"] for s in valid_seasons], default=0)

            # Cargar temporadas existentes y conteo de episodios locales en una sola query
            existing_seasons = {}
            if titulo.id:
                stmt = (
                    select(
                        Temporada.id,
                        Temporada.numero,
                        Temporada.fecha_estreno,
                        func.count(Episodio.id).label("ep_count"),
                    )
                    .outerjoin(Episodio, Episodio.temporada_id == Temporada.id)
                    .where(Temporada.titulo_id == titulo.id)
                    .group_by(Temporada.id, Temporada.numero, Temporada.fecha_estreno)
                )
                res_seasons = await self.db.execute(stmt)
                existing_seasons = {row.numero: row for row in res_seasons.all()}

            for s_info in valid_seasons:
                s_num = s_info.get("season_number")
                tmdb_ep_count = s_info.get("episode_count", 0)
                local_season = existing_seasons.get(s_num)

                # Criterio de omisión (skip): evitar llamadas HTTP y loops de episodios para temporadas pasadas ya completas
                should_skip = False
                if local_season and local_season.ep_count == tmdb_ep_count and tmdb_ep_count > 0:
                    # 1. Si la serie finalizó o fue cancelada, sus temporadas pasadas no cambian
                    if status in ("Ended", "Canceled"):
                        should_skip = True
                    # 2. Si es una temporada anterior a la última en una serie activa
                    elif s_num < max_s_num:
                        should_skip = True
                    # 3. Si es la última temporada pero ya terminó de emitirse hace más de 30 días
                    elif s_num == max_s_num and not fecha_prox_ep and lad_str:
                        try:
                            lad_date = datetime.strptime(lad_str, "%Y-%m-%d").date()
                            if (today - lad_date).days > 30:
                                should_skip = True
                        except ValueError:
                            pass

                if should_skip:
                    continue

                s_details = {}
                try:
                    s_details = await self.client.get_season_details(tmdb_id, s_num)
                except Exception as e:
                    logger.debug(f"Temporada {s_num} de serie {tmdb_id} sin detalles extendidos en TMDB: {e}")

                s_air_date = None
                s_ad_str = s_details.get("air_date") or s_info.get("air_date")
                if s_ad_str:
                    try:
                        s_air_date = datetime.strptime(s_ad_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                if not s_air_date:
                    for ep_item in s_details.get("episodes", []):
                        ep_item_ad = ep_item.get("air_date")
                        if ep_item_ad:
                            try:
                                s_air_date = datetime.strptime(ep_item_ad, "%Y-%m-%d").date()
                                break
                            except ValueError:
                                pass

                overview_text = s_details.get("overview") or s_info.get("overview")
                if not local_season:
                    temporada = Temporada(
                        titulo_id=titulo.id,
                        numero=s_num,
                        sinopsis=overview_text,
                        fecha_estreno=s_air_date,
                    )
                    self.db.add(temporada)
                    await self.db.flush()
                else:
                    res_t = await self.db.execute(select(Temporada).where(Temporada.id == local_season.id))
                    temporada = res_t.scalar_one()
                    if overview_text:
                        temporada.sinopsis = overview_text
                    if s_air_date:
                        temporada.fecha_estreno = s_air_date

                # Episodios de la temporada: cargar existentes en 1 query para evitar N+1
                episodes_data = s_details.get("episodes", [])
                if episodes_data:
                    res_eps = await self.db.execute(
                        select(Episodio).where(Episodio.temporada_id == temporada.id)
                    )
                    existing_eps = {ep.numero: ep for ep in res_eps.scalars().all()}

                    for ep_data in episodes_data:
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

                        episodio = existing_eps.get(ep_num)
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
        if fetch_reviews:
            await self.sync_reviews_for_title(titulo)

        return titulo

    # -------------------------------------------------------------------------
    # INGESTA INICIAL
    # -------------------------------------------------------------------------
    async def run_initial_ingest(
        self,
        priority: Optional[str] = None,
        movies_target: Optional[int] = None,
        series_target: Optional[int] = None,
        allow_unreleased: Optional[bool] = None,
    ) -> Dict[str, int]:
        prio = priority or settings.TMDB_INGEST_PRIORITY
        logger.info(f"Iniciando Ingesta Inicial con prioridad: {prio}")

        # Sincronizar géneros primero
        await self.sync_genres()

        movie_target = movies_target or settings.TMDB_INGEST_MOVIES_TARGET
        series_target = series_target or settings.TMDB_INGEST_SERIES_TARGET
        min_votes = settings.TMDB_MIN_VOTE_COUNT

        movies_added = await self._ingest_media_pool("movie", movie_target, prio, min_votes, allow_unreleased=allow_unreleased)
        series_added = await self._ingest_media_pool("tv", series_target, prio, min_votes, allow_unreleased=allow_unreleased)

        await self.recalculate_percentiles()
        await self.recalculate_unified_ratings()
        logger.info(f"Ingesta inicial completada: {movies_added} películas, {series_added} series.")
        return {"movies_added": movies_added, "series_added": series_added}

    async def _ingest_media_pool(
        self,
        media_type: str,
        target_count: int,
        priority: str,
        min_votes: int,
        allow_unreleased: Optional[bool] = None,
    ) -> int:
        allow_unrel = settings.TMDB_ALLOW_UNRELEASED if allow_unreleased is None else allow_unreleased
        release_date_lte = None if allow_unrel else date.today().strftime("%Y-%m-%d")
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
                    release_date_lte=release_date_lte,
                )
                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    if len(collected_ids) - initial_count >= limit:
                        break

                    tmdb_id = item["id"]
                    if tmdb_id not in collected_ids:
                        try:
                            if media_type == "movie":
                                t = await self.upsert_movie(tmdb_id, allow_unreleased=allow_unrel)
                            else:
                                t = await self.upsert_series(tmdb_id, fetch_episodes=True, allow_unreleased=allow_unrel)
                            collected_ids.add(tmdb_id)
                            if t is not None:
                                newly_added += 1
                                await self.db.commit()
                                title_name = t.nombre if t else str(tmdb_id)
                                logger.info(f"[{media_type.upper()}] Importado #{newly_added}/{limit}: '{title_name}' (TMDB ID: {tmdb_id})")
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
    async def run_daily_sync(
        self,
        changes_hours_window: Optional[int] = None,
        releases_days_window: Optional[int] = None,
        hours_window: Optional[int] = None,
        allow_unreleased: Optional[bool] = None,
    ) -> Dict[str, int]:
        """
        Sincronización diaria:
        1. Consulta TMDB /tv/changes y /movie/changes con ventana de cambios (changes_hours_window, default 48h / 2 días)
           y actualiza series y películas locales que cambiaron.
        2. Ingesta estrenos recientes en cartelera con ventana de estrenos (releases_days_window, default 15 días, popularidad >= 10.0).
        3. Recalcula percentiles de popularidad y ratings unificados.
        """
        logger.info("Iniciando Sincronización Diaria...")
        today = date.today()
        allow_unrel = settings.TMDB_ALLOW_UNRELEASED if allow_unreleased is None else allow_unreleased

        # 1. Ventana para /changes (horas convertidas a días hacia atrás para la API de TMDB)
        if changes_hours_window is not None:
            h_changes = changes_hours_window
        elif hours_window is not None:
            h_changes = hours_window
        else:
            h_changes = settings.TMDB_CHANGES_HOURS_WINDOW

        # 2. Ventana para /discover estrenos recientes en cartelera
        d_releases = releases_days_window or settings.TMDB_DAILY_SYNC_DAYS_WINDOW
        releases_start_date = (today - timedelta(days=d_releases)).strftime("%Y-%m-%d")
        releases_end_date = today.strftime("%Y-%m-%d")
        pop_threshold = settings.TMDB_DAILY_SYNC_POP_THRESHOLD

        logger.info(
            f"Configuración de sync diaria -> Cambios (/changes): {h_changes} hs | "
            f"Estrenos recientes: {d_releases} días ({releases_start_date} a {releases_end_date}) | "
            f"Permitir no estrenados: {allow_unrel}"
        )

        updated_series_count = 0
        updated_movies_count = 0
        if h_changes > 0:
            changes_days_back = max(1, (h_changes + 23) // 24)
            changes_start_date = (today - timedelta(days=changes_days_back)).strftime("%Y-%m-%d")
            changes_end_date = today.strftime("%Y-%m-%d")

            async def get_all_changes(media_type: str) -> Set[int]:
                """Recorre exhaustivamente todas las páginas de /changes en TMDB."""
                ids: Set[int] = set()
                page = 1
                while True:
                    data = await self.client.get_changes(
                        media_type,
                        start_date=changes_start_date,
                        end_date=changes_end_date,
                        page=page
                    )
                    results = data.get("results", [])
                    if not results:
                        break
                    for item in results:
                        if "id" in item:
                            ids.add(item["id"])
                    total_pages = data.get("total_pages", 1)
                    if page >= total_pages or page >= 1000:
                        break
                    page += 1
                return ids

            # 1. Obtener IDs cambiados en TMDB para TV
            changed_tv_ids: Set[int] = set()
            try:
                changed_tv_ids = await get_all_changes("tv")
                logger.info(f"TMDB /tv/changes devolvió {len(changed_tv_ids)} series con modificaciones en la ventana.")
            except Exception as e:
                logger.warning(f"No se pudo consultar TMDB /tv/changes: {e}")

            # 2. Obtener series de nuestra BD local
            local_tv_q = select(Titulo.tmdb_id).where(Titulo.tipo == "tv")
            res_local_tv = await self.db.execute(local_tv_q)
            local_tv_ids = set(res_local_tv.scalars().all())

            # Series locales que tuvieron cambios en TMDB durante la ventana
            tv_from_changes = local_tv_ids.intersection(changed_tv_ids)

            # 3. Seguimiento Activo de Series en Emisión / Producción
            active_tv_q = select(Titulo.tmdb_id).where(
                Titulo.tipo == "tv",
                Titulo.status_tmdb.in_(["Returning Series", "In Production", "Planned"])
            )
            res_active_tv = await self.db.execute(active_tv_q)
            active_tv_ids = set(res_active_tv.scalars().all())
            active_tv_remaining = active_tv_ids - tv_from_changes

            all_tv_to_update = tv_from_changes.union(active_tv_remaining)
            logger.info(
                f"Series a sincronizar hoy: {len(all_tv_to_update)} "
                f"({len(tv_from_changes)} por changes, {len(active_tv_remaining)} por seguimiento activo)."
            )

            for tmdb_id in all_tv_to_update:
                if tmdb_id:
                    try:
                        t = await self.upsert_series(
                            tmdb_id,
                            fetch_episodes=True,
                            allow_unreleased=allow_unrel,
                            fetch_reviews=False
                        )
                        if t is not None:
                            updated_series_count += 1
                            await self.db.commit()
                    except Exception as e:
                        logger.error(f"Error actualizando serie id {tmdb_id}: {e}")
                        await self.db.rollback()

            # 4. Consultar /movie/changes y refrescar películas locales modificadas
            try:
                changed_movie_ids = await get_all_changes("movie")
                logger.info(f"TMDB /movie/changes devolvió {len(changed_movie_ids)} películas con modificaciones en la ventana.")
                local_movie_q = select(Titulo.tmdb_id).where(Titulo.tipo == "movie")
                res_local_movies = await self.db.execute(local_movie_q)
                local_movie_ids = set(res_local_movies.scalars().all())
                movies_to_update = local_movie_ids.intersection(changed_movie_ids)
                logger.info(f"Películas locales a sincronizar por changes: {len(movies_to_update)}.")
                for m_id in movies_to_update:
                    try:
                        t = await self.upsert_movie(m_id, allow_unreleased=allow_unrel, fetch_reviews=False)
                        if t is not None:
                            updated_movies_count += 1
                            await self.db.commit()
                    except Exception as e:
                        logger.error(f"Error actualizando película cambiada id {m_id}: {e}")
                        await self.db.rollback()
            except Exception as e:
                logger.warning(f"No se pudo sincronizar /movie/changes: {e}")
        else:
            logger.info("Ventana de cambios es 0 hs: omitiendo consulta de /changes (solo nuevos estrenos).")

        # 5. Ingestar nuevos estrenos calificados (películas y series)
        new_movies_count = 0
        page = 1
        while page <= 5:
            data = await self.client.discover(
                media_type="movie",
                sort_by="popularity.desc",
                page=page,
                release_date_gte=releases_start_date,
                release_date_lte=releases_end_date,
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
                            t = await self.upsert_movie(tmdb_id, allow_unreleased=allow_unrel, fetch_reviews=True)
                            if t is not None:
                                new_movies_count += 1
                                await self.db.commit()
                        except Exception as e:
                            logger.error(f"Error ingesting new movie {tmdb_id}: {e}")
                            await self.db.rollback()
            page += 1

        # Series nuevas estrenadas en la ventana
        new_series_count = 0
        page = 1
        while page <= 5:
            data = await self.client.discover(
                media_type="tv",
                sort_by="popularity.desc",
                page=page,
                release_date_gte=releases_start_date,
                release_date_lte=releases_end_date,
            )
            results = data.get("results", [])
            if not results:
                break
            for item in results:
                if item.get("popularity", 0) >= pop_threshold:
                    tmdb_id = item["id"]
                    res = await self.db.execute(select(Titulo.id).where(Titulo.tmdb_id == tmdb_id, Titulo.tipo == "tv"))
                    if not res.scalar_one_or_none():
                        try:
                            t = await self.upsert_series(tmdb_id, fetch_episodes=True, allow_unreleased=allow_unrel, fetch_reviews=True)
                            if t is not None:
                                new_series_count += 1
                                await self.db.commit()
                        except Exception as e:
                            logger.error(f"Error ingesting new series {tmdb_id}: {e}")
                            await self.db.rollback()
            page += 1

        # 6. Refrescar métricas (popularidad y votos) para todo el catálogo y recalcular percentiles y ratings
        try:
            await self.refresh_catalog_metrics()
        except Exception as e:
            logger.error(f"Error en refresh_catalog_metrics durante sync diaria: {e}")
            await self.recalculate_percentiles()
            await self.recalculate_unified_ratings()

        # 7. Sincronizar embeddings pendientes para nuevos títulos
        try:
            await self.sync_pending_embeddings()
        except Exception as e:
            logger.warning(f"No se pudieron sincronizar embeddings tras sync diaria: {e}")

        # 8. Invalidar caché del catálogo y Home en memoria
        try:
            from app.services.catalog_service import clear_catalog_cache
            clear_catalog_cache()
        except Exception as e:
            logger.warning(f"No se pudo limpiar la caché tras sync diaria: {e}")

        logger.info(
            f"Sincronización diaria terminada: {updated_series_count} series y {updated_movies_count} películas actualizadas, "
            f"{new_movies_count} nuevos estrenos de películas, {new_series_count} nuevas series."
        )
        return {
            "updated_series": updated_series_count,
            "updated_movies": updated_movies_count,
            "new_movies": new_movies_count,
            "new_series": new_series_count,
        }

    async def sync_pending_embeddings(self, batch_size: int = 50) -> Dict[str, int]:
        """Calcula embeddings pendientes para los títulos que aún no tienen vector generado."""
        bind = self.db.bind or (self.db.get_bind() if hasattr(self.db, "get_bind") else None)
        if bind and bind.dialect.name != "postgresql":
            logger.info("Base de datos local es SQLite (sin soporte pgvector). Omitiendo sincronización de embeddings.")
            return {"total_pending": 0, "total_updated": 0, "total_failed": 0}

        from app.jobs.sync_embeddings import sync_catalog_embeddings
        return await sync_catalog_embeddings(batch_size=batch_size, db=self.db)

    # -------------------------------------------------------------------------
    # SANEAMIENTO DE TÍTULOS NO ESTRENADOS
    # -------------------------------------------------------------------------
    async def cleanup_unreleased_titles(self) -> Dict[str, int]:
        """
        Elimina títulos de la base de datos que aún no han sido estrenados
        (películas con fecha_estreno nula o futura, o series sin temporadas emitidas).
        """
        logger.info("Iniciando saneamiento de títulos no estrenados en la base de datos...")
        today = date.today()

        # 1. Películas sin fecha de estreno o con fecha futura
        res_m = await self.db.execute(select(Titulo).where(Titulo.tipo == "movie"))
        movies = res_m.scalars().all()
        deleted_movies = 0
        for m in movies:
            if not m.fecha_estreno or m.fecha_estreno > today:
                logger.info(f"Limpiando película no estrenada: '{m.nombre}' (ID: {m.id}, TMDB: {m.tmdb_id}, Estreno: {m.fecha_estreno})")
                await self.db.delete(m)
                deleted_movies += 1

        # 2. Series sin ninguna temporada estrenada
        res_s = await self.db.execute(select(Titulo).where(Titulo.tipo == "tv"))
        series = res_s.scalars().all()
        deleted_series = 0
        for s in series:
            res_seas = await self.db.execute(select(Temporada).where(Temporada.titulo_id == s.id))
            seasons = res_seas.scalars().all()
            has_aired = False
            if s.fecha_estreno and s.fecha_estreno <= today:
                has_aired = True
            else:
                for seas in seasons:
                    if seas.fecha_estreno and seas.fecha_estreno <= today:
                        has_aired = True
                        break
            if not has_aired:
                logger.info(f"Limpiando serie sin temporadas emitidas: '{s.nombre}' (ID: {s.id}, TMDB: {s.tmdb_id})")
                await self.db.delete(s)
                deleted_series += 1

        if deleted_movies > 0 or deleted_series > 0:
            await self.db.commit()
            await self.recalculate_percentiles()
            await self.recalculate_unified_ratings()

        logger.info(f"Saneamiento completado: {deleted_movies} películas y {deleted_series} series eliminadas.")
        return {"deleted_movies": deleted_movies, "deleted_series": deleted_series}

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
    # REFRESCO DE MÉTRICAS (POPULARIDAD Y VOTOS)
    # -------------------------------------------------------------------------
    async def refresh_catalog_metrics(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Refresca popularidad, vote_average_tmdb y vote_count_tmdb para todos los títulos
        del catálogo haciendo consultas ultraligeras a TMDB sin traer elenco ni temporadas.
        Luego recalcula los percentiles de popularidad y ratings unificados en base de datos.
        """
        logger.info("Iniciando refresco de métricas de catálogo (popularidad y votos)...")
        res = await self.db.execute(
            select(Titulo.id, Titulo.tmdb_id, Titulo.tipo).where(Titulo.tmdb_id.isnot(None))
        )
        titles_info = res.all()
        total_titles = len(titles_info)
        updated_count = 0

        async def fetch_metric(tit_id: int, tmdb_id: int, tipo: str):
            try:
                # append_to_response="" para traer solo los campos básicos del título (muy ligero)
                details = await self.client.get_details(tipo, tmdb_id, append_to_response="")
                pop = details.get("popularity", 0.0)
                v_avg = details.get("vote_average", 0.0)
                v_cnt = details.get("vote_count", 0)
                return tit_id, pop, v_avg, v_cnt
            except Exception as e:
                logger.debug(f"Error obteniendo métricas de {tipo} {tmdb_id}: {e}")
                return None

        # Procesar en lotes concurrentes respetando el semáforo del cliente
        for i in range(0, total_titles, batch_size):
            chunk = titles_info[i:i + batch_size]
            tasks = [fetch_metric(tid, tmid, mtype) for tid, tmid, mtype in chunk]
            results = await asyncio.gather(*tasks)

            for res_item in results:
                if res_item:
                    tid, pop, v_avg, v_cnt = res_item
                    await self.db.execute(
                        update(Titulo)
                        .where(Titulo.id == tid)
                        .values(
                            popularidad=pop,
                            vote_average_tmdb=v_avg,
                            vote_count_tmdb=v_cnt
                        )
                    )
                    updated_count += 1

            await self.db.commit()

        logger.info(f"Métricas actualizadas para {updated_count}/{total_titles} títulos. Recalculando percentiles y ratings...")
        await self.recalculate_percentiles()
        await self.recalculate_unified_ratings()
        return {"total_titles": total_titles, "updated": updated_count}

    # -------------------------------------------------------------------------
    # BACKFILL DE PAÍSES (ORIGEN Y PRODUCCIÓN CONSOLIDADOS)
    # -------------------------------------------------------------------------
    async def backfill_catalog_countries(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Recorre todos los títulos del catálogo en lotes concurrentes y actualiza
        el campo 'pais' con la lista consolidada de códigos ISO extraída de TMDB
        (origin_country con fallback a production_countries).
        """
        logger.info("Iniciando backfill de países para todos los títulos del catálogo...")
        res = await self.db.execute(
            select(Titulo.id, Titulo.tmdb_id, Titulo.tipo, Titulo.pais).where(Titulo.tmdb_id.isnot(None))
        )
        titles_info = res.all()
        total_titles = len(titles_info)
        updated_count = 0

        async def fetch_and_extract_country(tit_id: int, tmdb_id: int, tipo: str, current_pais: Optional[str]):
            try:
                details = await self.client.get_details(tipo, tmdb_id, append_to_response="")
                new_pais = extract_tmdb_countries(details)
                if new_pais != current_pais:
                    return tit_id, new_pais
                return None
            except Exception as e:
                logger.debug(f"Error obteniendo países para {tipo} {tmdb_id}: {e}")
                return None

        for i in range(0, total_titles, batch_size):
            chunk = titles_info[i:i + batch_size]
            tasks = [fetch_and_extract_country(tid, tmid, mtype, cpais) for tid, tmid, mtype, cpais in chunk]
            results = await asyncio.gather(*tasks)

            for res_item in results:
                if res_item:
                    tid, new_pais = res_item
                    await self.db.execute(
                        update(Titulo)
                        .where(Titulo.id == tid)
                        .values(pais=new_pais)
                    )
                    updated_count += 1

            await self.db.commit()
            logger.info(f"Progreso backfill países: {min(i + batch_size, total_titles)}/{total_titles} procesados ({updated_count} modificados)...")

        logger.info(f"Backfill de países completado: {updated_count}/{total_titles} títulos actualizados con nuevos códigos.")
        return {"total_titles": total_titles, "updated": updated_count}

    # -------------------------------------------------------------------------
    # PURGA SELECTIVA DE TÍTULOS INCOMPLETOS O NO LEGIBLES
    # -------------------------------------------------------------------------
    async def purge_invalid_or_incomplete_titles(self) -> Dict[str, Any]:
        """
        Elimina en cascada todos los títulos que incumplan las condiciones mínimas de calidad:
        1. Nombres con caracteres no latinos (sin traducción al inglés).
        2. Títulos sin fecha de estreno (fecha_estreno IS NULL).
        3. Títulos sin idioma original (idioma_original IS NULL).
        4. Títulos sin país (pais IS NULL).
        Tras la purga, recalcula percentiles y ratings unificados, e invalida la caché del catálogo.
        """
        logger.info("Iniciando auditoría y purga de títulos incompletos o no legibles...")
        res = await self.db.execute(
            select(
                Titulo.id,
                Titulo.tmdb_id,
                Titulo.tipo,
                Titulo.nombre,
                Titulo.fecha_estreno,
                Titulo.idioma_original,
                Titulo.pais,
            )
        )
        all_titles = res.all()

        to_delete: List[Dict[str, Any]] = []
        for tid, tmid, tipo, nombre, fecha, idioma, pais in all_titles:
            reasons = []
            if not is_latin_legible(nombre):
                reasons.append("alfabeto_no_latino")
            if fecha is None:
                reasons.append("sin_fecha_estreno")
            if not idioma:
                reasons.append("sin_idioma_original")
            if not pais:
                reasons.append("sin_pais")

            if reasons:
                to_delete.append({
                    "id": tid,
                    "tmdb_id": tmid,
                    "tipo": tipo,
                    "nombre": nombre,
                    "motivos": reasons,
                })

        if not to_delete:
            logger.info("No se encontraron títulos para purgar. El catálogo cumple al 100% las directivas de calidad.")
            return {"purged_count": 0, "purged_titles": []}

        target_ids = [t["id"] for t in to_delete]
        logger.warning(f"Purgando {len(target_ids)} títulos del catálogo por directivas de calidad...")

        # 1. Eliminar episodios de series dependientes
        season_ids_res = await self.db.execute(
            select(Temporada.id).where(Temporada.titulo_id.in_(target_ids))
        )
        season_ids = season_ids_res.scalars().all()
        if season_ids:
            await self.db.execute(
                delete(Episodio).where(Episodio.temporada_id.in_(season_ids))
            )

        # 2. Eliminar temporadas
        await self.db.execute(
            delete(Temporada).where(Temporada.titulo_id.in_(target_ids))
        )

        # 3. Eliminar relaciones de tablas intermedias
        await self.db.execute(
            delete(titulos_generos).where(titulos_generos.c.titulo_id.in_(target_ids))
        )
        await self.db.execute(
            delete(titulos_elenco).where(titulos_elenco.c.titulo_id.in_(target_ids))
        )

        # 4. Eliminar estados de usuario y reseñas asociadas si existieran
        await self.db.execute(
            delete(EstadoUsuarioTitulo).where(EstadoUsuarioTitulo.titulo_id.in_(target_ids))
        )
        await self.db.execute(
            delete(Resena).where(Resena.titulo_id.in_(target_ids))
        )

        # 5. Eliminar títulos principales
        await self.db.execute(
            delete(Titulo).where(Titulo.id.in_(target_ids))
        )
        await self.db.commit()

        # 6. Recalcular percentiles y ratings unificados
        await self.recalculate_percentiles()
        await self.recalculate_unified_ratings()

        # 7. Invalidar caché del catálogo
        try:
            from app.services.catalog_service import clear_catalog_cache
            clear_catalog_cache()
        except Exception as e:
            logger.debug(f"Aviso al limpiar caché de catálogo post-purga: {e}")

        logger.info(f"Purga completada exitosamente. Se eliminaron {len(target_ids)} títulos.")
        return {
            "purged_count": len(target_ids),
            "purged_titles": to_delete
        }

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
        Optimizado: actualiza en lote a vote_average_tmdb y solo itera sobre los títulos que
        efectivamente tienen reseñas locales de usuarios.
        """
        logger.info("Recalculando rating unificado...")
        if titulo_id:
            # Caso individual
            q_res = select(
                func.coalesce(func.sum(Resena.puntaje), 0.0),
                func.count(Resena.id)
            ).where(
                Resena.titulo_id == titulo_id,
                Resena.usuario_id.isnot(None),
                Resena.puntaje.isnot(None)
            )
            r = await self.db.execute(q_res)
            sum_users, count_users = r.one()
            tit_res = await self.db.execute(select(Titulo).where(Titulo.id == titulo_id))
            tit = tit_res.scalar_one_or_none()
            if tit:
                total_votes = tit.vote_count_tmdb + count_users
                if total_votes > 0:
                    tit.rating_unificado = round(((tit.vote_average_tmdb * tit.vote_count_tmdb) + float(sum_users)) / total_votes, 2)
                else:
                    tit.rating_unificado = 0.0
                await self.db.commit()
            return 1

        # Caso masivo:
        # 1. Establecer rating base de TMDB para todos los títulos
        await self.db.execute(
            update(Titulo)
            .values(rating_unificado=Titulo.vote_average_tmdb)
            .where(Titulo.vote_count_tmdb > 0)
        )
        await self.db.execute(
            update(Titulo)
            .values(rating_unificado=0.0)
            .where(Titulo.vote_count_tmdb == 0)
        )

        # 2. Consultar solo los títulos que TIENEN reseñas de usuarios locales
        user_reviews_q = select(
            Resena.titulo_id,
            func.coalesce(func.sum(Resena.puntaje), 0.0).label("sum_puntaje"),
            func.count(Resena.id).label("count_reviews")
        ).where(
            Resena.usuario_id.isnot(None),
            Resena.puntaje.isnot(None)
        ).group_by(Resena.titulo_id)

        res_user_revs = await self.db.execute(user_reviews_q)
        reviewed_titles = res_user_revs.all()

        for tid, sum_users, count_users in reviewed_titles:
            tit_res = await self.db.execute(select(Titulo).where(Titulo.id == tid))
            tit = tit_res.scalar_one_or_none()
            if tit:
                total_votes = tit.vote_count_tmdb + count_users
                if total_votes > 0:
                    tit.rating_unificado = round(((tit.vote_average_tmdb * tit.vote_count_tmdb) + float(sum_users)) / total_votes, 2)

        await self.db.commit()
        logger.info(f"Rating unificado recalculado con éxito ({len(reviewed_titles)} títulos con reseñas de usuarios).")
        return len(reviewed_titles)

    # -------------------------------------------------------------------------
    # EXPANSIÓN DE CATÁLOGO POR GÉNEROS (CRITERIO 1)
    # -------------------------------------------------------------------------
    async def expand_catalog_by_genres(
        self,
        genre: Optional[Any] = None,
        media_type: str = "both",
        target_per_genre: Optional[int] = None,
        min_vote_count: Optional[int] = None,
        min_vote_average: Optional[float] = None,
        allow_unreleased: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Criterio 1: Expande el catálogo vía /discover filtrando por género y umbrales de calidad.
        Permite especificar un género (ID o nombre) o procesar todos los géneros existentes.
        """
        target = target_per_genre if target_per_genre is not None else settings.TMDB_EXPAND_TITLES_PER_GENRE
        min_votes = min_vote_count if min_vote_count is not None else settings.TMDB_EXPAND_MIN_VOTE_COUNT
        min_avg = min_vote_average if min_vote_average is not None else settings.TMDB_EXPAND_MIN_VOTE_AVERAGE
        allow_unrel = settings.TMDB_ALLOW_UNRELEASED if allow_unreleased is None else allow_unreleased
        release_date_lte = None if allow_unrel else date.today().strftime("%Y-%m-%d")

        # 1. Asegurar catálogo de géneros
        res_genres = await self.db.execute(select(Genero).order_by(Genero.id))
        all_db_genres = res_genres.scalars().all()
        if not all_db_genres:
            logger.info("Catálogo de géneros vacío en base de datos. Sincronizando desde TMDB...")
            await self.sync_genres()
            res_genres = await self.db.execute(select(Genero).order_by(Genero.id))
            all_db_genres = res_genres.scalars().all()

        # 2. Filtrar géneros objetivo
        target_genres: List[Genero] = []
        if genre is not None:
            genre_str = str(genre).strip()
            if genre_str.isdigit():
                gid = int(genre_str)
                target_genres = [g for g in all_db_genres if g.id == gid]
            else:
                target_genres = [g for g in all_db_genres if genre_str.lower() in g.nombre.lower()]

            if not target_genres:
                raise ValueError(f"No se encontró ningún género que coincida con '{genre}'.")
        else:
            target_genres = all_db_genres

        # 3. Determinar media_types a procesar
        if media_type in ("movie", "tv"):
            media_types_to_process = [media_type]
        else:
            media_types_to_process = ["movie", "tv"]

        logger.info(
            f"Iniciando expansión por géneros: {len(target_genres)} géneros, "
            f"tipos: {media_types_to_process}, target por género: {target}, "
            f"min_votes: {min_votes}, min_rating: {min_avg}"
        )

        total_movies_added = 0
        total_series_added = 0

        for g in target_genres:
            logger.info(f"--- Procesando Género: {g.nombre} (ID: {g.id}) ---")

            for mtype in media_types_to_process:
                # Cargar IDs existentes para evitar llamadas get_details redundantes
                res_existing = await self.db.execute(select(Titulo.tmdb_id).where(Titulo.tipo == mtype))
                existing_ids: Set[int] = set(res_existing.scalars().all())

                genre_added = 0
                page = 1
                # Permitir explorar suficientes páginas según el target (hasta 50 páginas o más si el target es alto)
                max_pages = min(500, max(50, (target // 20) * 4 + 10))

                while genre_added < target and page <= max_pages:
                    try:
                        data = await self.client.discover(
                            media_type=mtype,
                            sort_by="popularity.desc",
                            page=page,
                            vote_count_gte=min_votes,
                            vote_average_gte=min_avg,
                            with_genres=str(g.id),
                            release_date_lte=release_date_lte,
                        )
                    except Exception as e:
                        logger.error(f"Error consultando discover ({mtype}, genero: {g.nombre}, pag: {page}): {e}")
                        break

                    results = data.get("results", [])
                    total_pages = data.get("total_pages", 0)
                    if not results:
                        break

                    for item in results:
                        if genre_added >= target:
                            break

                        tmdb_id = item.get("id")
                        if not tmdb_id or tmdb_id in existing_ids:
                            continue

                        try:
                            if mtype == "movie":
                                t = await self.upsert_movie(tmdb_id, allow_unreleased=allow_unrel)
                            else:
                                t = await self.upsert_series(tmdb_id, fetch_episodes=True, allow_unreleased=allow_unrel)

                            existing_ids.add(tmdb_id)
                            if t is not None:
                                genre_added += 1
                                if mtype == "movie":
                                    total_movies_added += 1
                                else:
                                    total_series_added += 1

                                await self.db.commit()
                                logger.info(
                                    f"[EXPAND] [{g.nombre}] {mtype.upper()} ({genre_added}/{target}): "
                                    f"'{t.nombre}' (TMDB ID: {tmdb_id}, Rating: {t.rating_unificado})"
                                )
                        except Exception as e:
                            logger.error(f"Error upserting {mtype} id {tmdb_id} en género {g.nombre}: {e}")
                            await self.db.rollback()

                    if page >= total_pages or genre_added >= target:
                        break

                    page += 1

        # 4. Recalcular métricas si hubo nuevos títulos
        if (total_movies_added + total_series_added) > 0:
            logger.info("Recalculando percentiles y ratings tras expansión...")
            await self.recalculate_percentiles()
            await self.recalculate_unified_ratings()

        summary = {
            "genres_processed": len(target_genres),
            "movies_added": total_movies_added,
            "series_added": total_series_added,
            "total_added": total_movies_added + total_series_added,
        }
        logger.info(f"Expansión por géneros completada: {summary}")
        return summary


