import logging
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.config import settings
from app.db.session import AsyncSessionLocal, get_db
from app.services import catalog_service
from app.services.tmdb_client import TMDBClient
from app.services.tmdb_sync_service import TMDBSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administración"])


# -------------------------------------------------------------------------
# ESQUEMAS DE ENTRADA / SALIDA
# -------------------------------------------------------------------------
class JobResponse(BaseModel):
    status: str = "accepted"
    job: str
    message: str


class InitialIngestRequest(BaseModel):
    priority: Optional[Literal["popular_first", "toprated_first"]] = Field(
        default=None, description="Prioridad de ingesta: popular_first o toprated_first"
    )
    movies_target: Optional[int] = Field(
        default=None, ge=1, le=10000, description="Objetivo de películas a ingestar"
    )
    series_target: Optional[int] = Field(
        default=None, ge=1, le=10000, description="Objetivo de series a ingestar"
    )
    allow_unreleased: Optional[bool] = Field(
        default=None, description="Permitir títulos no estrenados (default: False / según config)"
    )


class DailySyncRequest(BaseModel):
    changes_hours_window: Optional[int] = Field(
        default=None, ge=1, le=720, description="Ventana de horas hacia atrás para consultar /changes de TMDB en series y películas (default config: 48 hs)"
    )
    releases_days_window: Optional[int] = Field(
        default=None, ge=1, le=90, description="Ventana de días hacia atrás para consultar estrenos recientes en cartelera (default config: 15 días)"
    )
    hours_window: Optional[int] = Field(
        default=None, ge=1, le=720, description="Alias compatible de changes_hours_window"
    )
    allow_unreleased: Optional[bool] = Field(
        default=None, description="Permitir títulos no estrenados (default: False / según config)"
    )


class ReviewsSyncRequest(BaseModel):
    limit_per_title: Optional[int] = Field(
        default=None, ge=1, le=50, description="Límite máximo de reseñas a sincronizar por título"
    )


class ImportTMDBItem(BaseModel):
    tmdb_id: int = Field(..., ge=1, description="ID del título en TMDB")
    type: Literal["movie", "tv"] = Field(default="movie", description="Tipo de contenido ('movie' o 'tv')")


class ImportTMDBRequest(BaseModel):
    tmdb_id: Optional[int] = Field(default=None, ge=1, description="ID individual en TMDB")
    type: Literal["movie", "tv"] = Field(default="movie", description="Tipo de contenido individual ('movie' o 'tv')")
    items: Optional[List[ImportTMDBItem]] = Field(default=None, description="Lista opcional de títulos para importar en lote")


class RefreshMetricsRequest(BaseModel):
    batch_size: Optional[int] = Field(default=50, ge=1, le=200, description="Tamaño de lote para consultas concurrentes a TMDB")


class ExpandCatalogRequest(BaseModel):
    genre: Optional[str] = Field(
        default=None, description="Nombre o ID del género a expandir (si es null/omitido, expande todos los géneros)"
    )
    media_type: Literal["both", "movie", "tv"] = Field(
        default="both", description="Tipo de contenido a expandir ('both', 'movie' o 'tv')"
    )
    min_vote_count: Optional[int] = Field(
        default=None, ge=0, description="Umbral mínimo de votos requeridos en TMDB (default: config)"
    )
    min_vote_average: Optional[float] = Field(
        default=None, ge=0.0, le=10.0, description="Calificación promedio mínima en TMDB (default: config)"
    )
    target_per_genre: Optional[int] = Field(
        default=None, ge=1, le=500, description="Cantidad objetivo de títulos por género (default: config)"
    )
    allow_unreleased: Optional[bool] = Field(
        default=False, description="Permitir títulos no estrenados (default: False)"
    )


class ActorPhotosSyncRequest(BaseModel):
    limit: Optional[int] = Field(
        default=None, ge=0, description="Límite de actores sin foto a procesar. Enviar 0 para sin límite, o null para usar TMDB_ACTOR_PHOTOS_LIMIT de config (default: 500)"
    )
    actor_id: Optional[int] = Field(
        default=None, description="Procesar un actor específico por ID local"
    )


# -------------------------------------------------------------------------
# FUNCIONES WRAPPER PARA BACKGROUND TASKS
# -------------------------------------------------------------------------
async def _run_job_genres():
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.sync_genres()
    except Exception as e:
        logger.error(f"[Job Background] Error en sincronización de géneros: {e}")
    finally:
        await client.close()


async def _run_job_initial(
    priority: Optional[str],
    movies_target: Optional[int],
    series_target: Optional[int],
    allow_unreleased: Optional[bool] = None,
):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.run_initial_ingest(
                priority=priority,
                movies_target=movies_target,
                series_target=series_target,
                allow_unreleased=allow_unreleased,
            )
    except Exception as e:
        logger.error(f"[Job Background] Error en ingesta inicial: {e}")
    finally:
        await client.close()


async def _run_job_daily(
    changes_hours_window: Optional[int] = None,
    releases_days_window: Optional[int] = None,
    hours_window: Optional[int] = None,
    allow_unreleased: Optional[bool] = None,
):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            changes_h = changes_hours_window if changes_hours_window is not None else hours_window
            await service.run_daily_sync(
                changes_hours_window=changes_h,
                releases_days_window=releases_days_window,
                allow_unreleased=allow_unreleased,
            )
    except Exception as e:
        logger.error(f"[Job Background] Error en sincronización diaria: {e}")
    finally:
        await client.close()


async def _run_job_percentiles():
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.recalculate_percentiles()
            await service.recalculate_unified_ratings()
    except Exception as e:
        logger.error(f"[Job Background] Error recalculando métricas: {e}")
    finally:
        await client.close()


async def _run_job_reviews(limit_per_title: Optional[int]):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.sync_all_missing_reviews(limit_per_title=limit_per_title)
    except Exception as e:
        logger.error(f"[Job Background] Error sincronizando reseñas: {e}")
    finally:
        await client.close()


async def _run_job_import_tmdb(
    items: Optional[List[tuple[int, str]]] = None,
    tmdb_id: Optional[int] = None,
    media_type: Optional[str] = "movie",
):
    if items is None:
        if tmdb_id is not None:
            items = [(tmdb_id, media_type or "movie")]
        else:
            items = []
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            for tmdb_id, media_type in items:
                try:
                    if media_type == "movie":
                        await service.upsert_movie(tmdb_id, fetch_reviews=True)
                    else:
                        await service.upsert_series(tmdb_id, fetch_episodes=True, fetch_reviews=True)
                    await db.commit()
                except Exception as item_err:
                    logger.error(f"[Job Background] Error importando {media_type} id {tmdb_id}: {item_err}")
                    await db.rollback()

            await service.recalculate_percentiles()
            await service.recalculate_unified_ratings()
            try:
                await service.sync_pending_embeddings()
            except Exception as e:
                logger.warning(f"No se pudieron sincronizar embeddings tras import-tmdb: {e}")
            try:
                from app.services.catalog_service import clear_catalog_cache
                clear_catalog_cache()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"[Job Background] Error general en importación TMDB: {e}")
    finally:
        await client.close()


async def _run_job_refresh_metrics(batch_size: int):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.refresh_catalog_metrics(batch_size=batch_size)
            try:
                from app.services.catalog_service import clear_catalog_cache
                clear_catalog_cache()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"[Job Background] Error en refresco de métricas: {e}")
    finally:
        await client.close()


async def _run_job_backfill_countries():
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.backfill_catalog_countries()
            try:
                from app.services.catalog_service import clear_catalog_cache
                clear_catalog_cache()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"[Job Background] Error en backfill de países: {e}")
    finally:
        await client.close()


async def _run_job_purge_incomplete():
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.purge_invalid_or_incomplete_titles()
    except Exception as e:
        logger.error(f"[Job Background] Error en purga de títulos incompletos: {e}")
    finally:
        await client.close()


async def _run_job_import_json(items: List[Dict[str, Any]]):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.import_from_json_data(items)
    except Exception as e:
        logger.error(f"[Job Background] Error importando JSON manual: {e}")
    finally:
        await client.close()


async def _run_job_expand(
    genre: Optional[str],
    media_type: str,
    target_per_genre: Optional[int],
    min_vote_count: Optional[int],
    min_vote_average: Optional[float],
    allow_unreleased: Optional[bool],
):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.expand_catalog_by_genres(
                genre=genre,
                media_type=media_type,
                target_per_genre=target_per_genre,
                min_vote_count=min_vote_count,
                min_vote_average=min_vote_average,
                allow_unreleased=allow_unreleased,
            )
    except Exception as e:
        logger.error(f"[Job Background] Error en expansión de catálogo: {e}")
    finally:
        await client.close()


async def _run_job_actor_photos(limit: Optional[int], actor_id: Optional[int]):
    from app.jobs.populate_actor_photos import populate_actor_photos
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            await populate_actor_photos(limit=limit, actor_id=actor_id, db=db, client=client)
    except Exception as e:
        logger.error(f"[Job Background] Error en sincronización de fotos de actores: {e}")
    finally:
        await client.close()


# -------------------------------------------------------------------------
# ESQUEMA PARA LIMPIEZA DE CATÁLOGO
# -------------------------------------------------------------------------
class ClearCatalogResponse(BaseModel):
    status: str = "success"
    message: str
    deleted: Dict[str, int]


# -------------------------------------------------------------------------
# ENDPOINTS
# -------------------------------------------------------------------------
@router.post("/sync/genres", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync_genres(
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Sincroniza el catálogo completo de géneros de TMDB en background."""
    background_tasks.add_task(_run_job_genres)
    return JobResponse(
        job="sync_genres",
        message="Sincronización de géneros iniciada en segundo plano."
    )


@router.post("/sync/initial", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_initial_ingest(
    payload: InitialIngestRequest,
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Ejecuta la ingesta inicial masiva de títulos en background."""
    background_tasks.add_task(
        _run_job_initial,
        priority=payload.priority,
        movies_target=payload.movies_target,
        series_target=payload.series_target,
        allow_unreleased=payload.allow_unreleased,
    )
    return JobResponse(
        job="initial_ingest",
        message=f"Ingesta inicial encolada en segundo plano (prioridad: {payload.priority or 'config default'})."
    )


@router.post("/sync/daily", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_daily_sync(
    payload: DailySyncRequest,
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Ejecuta la sincronización diaria de cambios TMDB y cartelera en background."""
    changes_h = payload.changes_hours_window if payload.changes_hours_window is not None else payload.hours_window
    background_tasks.add_task(
        _run_job_daily,
        changes_hours_window=changes_h,
        releases_days_window=payload.releases_days_window,
        allow_unreleased=payload.allow_unreleased,
    )
    changes_desc = f"{changes_h} hs" if changes_h is not None else "config default (48 hs)"
    releases_desc = f"{payload.releases_days_window} días" if payload.releases_days_window else "config default (15 días)"
    return JobResponse(
        job="daily_sync",
        message=f"Sincronización diaria iniciada en segundo plano (cambios: {changes_desc}, cartelera: {releases_desc})."
    )


@router.post("/sync/cleanup-unreleased", response_model=JobResponse, status_code=status.HTTP_200_OK)
async def trigger_cleanup_unreleased(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Elimina del catálogo las películas no estrenadas y series sin temporadas emitidas, recalculando métricas."""
    client = TMDBClient()
    try:
        service = TMDBSyncService(db, client)
        res = await service.cleanup_unreleased_titles()
        return JobResponse(
            status="success",
            job="cleanup_unreleased",
            message=f"Saneamiento completado: {res.get('deleted_movies', 0)} películas y {res.get('deleted_series', 0)} series eliminadas."
        )
    finally:
        await client.close()


@router.post("/sync/percentiles", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_recalculate_percentiles(
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Recalcula percentiles de popularidad y ratings unificados en background."""
    background_tasks.add_task(_run_job_percentiles)
    return JobResponse(
        job="recalculate_metrics",
        message="Recálculo de percentiles y rating unificado iniciado en segundo plano."
    )


@router.post("/sync/reviews", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync_reviews(
    payload: ReviewsSyncRequest,
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Sincroniza reseñas externas de TMDB para todos los títulos en background."""
    background_tasks.add_task(_run_job_reviews, limit_per_title=payload.limit_per_title)
    return JobResponse(
        job="sync_reviews",
        message=f"Sincronización de reseñas encolada en segundo plano (límite por título: {payload.limit_per_title or 'config default'})."
    )


@router.post("/sync/import-tmdb", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_import_tmdb_id(
    payload: ImportTMDBRequest,
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Importa o actualiza uno o varios títulos específicos de TMDB por su identificador en background."""
    items_to_process: List[tuple[int, str]] = []
    if payload.items:
        for it in payload.items:
            items_to_process.append((it.tmdb_id, it.type))
    elif payload.tmdb_id is not None:
        items_to_process.append((payload.tmdb_id, payload.type))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar tmdb_id individual o una lista en items."
        )

    background_tasks.add_task(_run_job_import_tmdb, items=items_to_process)
    count = len(items_to_process)
    desc = f"{count} títulos" if count > 1 else f"{items_to_process[0][1]} con TMDB ID {items_to_process[0][0]}"
    return JobResponse(
        job="import_tmdb",
        message=f"Importación/actualización de {desc} iniciada en segundo plano."
    )


@router.post("/sync/refresh-metrics", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_refresh_metrics(
    payload: Optional[RefreshMetricsRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Refresca popularidad y votos para todo el catálogo y recalcula percentiles y ratings en background."""
    bs = payload.batch_size if payload and payload.batch_size else 50
    background_tasks.add_task(_run_job_refresh_metrics, batch_size=bs)
    return JobResponse(
        job="refresh_metrics",
        message=f"Refresco de métricas de catálogo (popularidad y votos) iniciado en segundo plano (lote: {bs})."
    )


@router.post("/sync/backfill-countries", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_backfill_countries(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Actualiza la columna 'pais' con origen y producción consolidados para todo el catálogo en background."""
    background_tasks.add_task(_run_job_backfill_countries)
    return JobResponse(
        job="backfill_countries",
        message="Backfill de países consolidando origen y producción iniciado en segundo plano."
    )


@router.post("/sync/purge-incomplete", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_purge_incomplete(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Purga títulos no legibles (alfabeto no latino) o sin fecha, idioma o país en background."""
    background_tasks.add_task(_run_job_purge_incomplete)
    return JobResponse(
        job="purge_incomplete",
        message="Purga selectiva de títulos incompletos o no legibles iniciada en segundo plano."
    )


@router.post("/sync/import-json", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_import_json(
    items: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Importa títulos a partir de un arreglo JSON estructurado según plantillas en background."""
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La lista de títulos para importar no puede estar vacía."
        )
    background_tasks.add_task(_run_job_import_json, items=items)
    return JobResponse(
        job="import_json",
        message=f"Importación de {len(items)} registros JSON encolada en segundo plano."
    )


@router.post("/sync/expand", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_expand_catalog(
    payload: ExpandCatalogRequest,
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Ejecuta la expansión selectiva de catálogo por géneros (Criterio 1) en background."""
    background_tasks.add_task(
        _run_job_expand,
        genre=payload.genre,
        media_type=payload.media_type,
        target_per_genre=payload.target_per_genre,
        min_vote_count=payload.min_vote_count,
        min_vote_average=payload.min_vote_average,
        allow_unreleased=payload.allow_unreleased,
    )
    genre_desc = payload.genre or "todos los géneros"
    return JobResponse(
        job="expand_catalog",
        message=f"Expansión de catálogo iniciada en segundo plano para {genre_desc} (tipo: {payload.media_type})."
    )


@router.post("/sync/actor-photos", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_actor_photos_sync(
    payload: Optional[ActorPhotosSyncRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    admin: Any = Depends(get_current_admin)
) -> JobResponse:
    """
    Dispara la sincronización en segundo plano de fotos de actores desde TMDB,
    priorizando los actores de títulos más populares.
    """
    limit: Optional[int] = None
    desc: str = ""
    raw_limit = payload.limit if payload is not None else None
    if raw_limit == 0:
        limit = 0
        desc = "sin límite"
    elif raw_limit is not None:
        limit = raw_limit
        desc = str(limit)
    else:
        limit = None  # populate_actor_photos usará settings.TMDB_ACTOR_PHOTOS_LIMIT
        desc = f"config default ({settings.TMDB_ACTOR_PHOTOS_LIMIT})"

    actor_id = payload.actor_id if payload else None
    background_tasks.add_task(_run_job_actor_photos, limit=limit, actor_id=actor_id)
    return JobResponse(
        job="sync_actor_photos",
        message=f"Sincronización de fotos de actores iniciada en background (límite: {desc})."
    )


@router.delete("/catalog", response_model=ClearCatalogResponse)
async def clear_catalog(
    confirm: bool = Query(False, description="Confirmar el vaciado total del catálogo"),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_admin)
) -> ClearCatalogResponse:
    """
    Elimina todos los títulos, temporadas, episodios, reseñas y relaciones del catálogo.
    Requiere ser administrador o cabecera X-Admin-Key, y confirmación explícita ?confirm=true.
    Preserva intactos los usuarios y el catálogo maestro de géneros.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operación destructiva. Debe enviar ?confirm=true para confirmar el vaciado del catálogo."
        )

    deleted_stats = await catalog_service.clear_entire_catalog(db)
    return ClearCatalogResponse(
        status="success",
        message="Catálogo y entidades asociadas eliminados correctamente.",
        deleted=deleted_stats
    )

