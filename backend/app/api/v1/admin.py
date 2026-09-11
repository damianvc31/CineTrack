import logging
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_admin
from app.db.session import AsyncSessionLocal
from app.services.tmdb_client import TMDBClient
from app.services.tmdb_sync_service import TMDBSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/sync", tags=["Administración - Sincronización"])


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


class DailySyncRequest(BaseModel):
    hours_window: Optional[int] = Field(
        default=None, ge=1, le=168, description="Ventana de horas hacia atrás para consultar cambios en TMDB (ej. 48)"
    )


class ReviewsSyncRequest(BaseModel):
    limit_per_title: Optional[int] = Field(
        default=None, ge=1, le=50, description="Límite máximo de reseñas a sincronizar por título"
    )


class ImportTMDBRequest(BaseModel):
    tmdb_id: int = Field(..., ge=1, description="ID del título en TMDB")
    type: Literal["movie", "tv"] = Field(default="movie", description="Tipo de contenido ('movie' o 'tv')")


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


async def _run_job_initial(priority: Optional[str], movies_target: Optional[int], series_target: Optional[int]):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.run_initial_ingest(
                priority=priority,
                movies_target=movies_target,
                series_target=series_target
            )
    except Exception as e:
        logger.error(f"[Job Background] Error en ingesta inicial: {e}")
    finally:
        await client.close()


async def _run_job_daily(hours_window: Optional[int]):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            await service.run_daily_sync(hours_window=hours_window)
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
            await service.sync_all_missing_reviews(limit=limit_per_title)
    except Exception as e:
        logger.error(f"[Job Background] Error sincronizando reseñas: {e}")
    finally:
        await client.close()


async def _run_job_import_tmdb(tmdb_id: int, media_type: str):
    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)
            if media_type == "movie":
                await service.upsert_movie(tmdb_id)
            else:
                await service.upsert_series(tmdb_id, fetch_episodes=True)
            await db.commit()
            await service.recalculate_percentiles()
            await service.recalculate_unified_ratings()
    except Exception as e:
        logger.error(f"[Job Background] Error importando título {tmdb_id} ({media_type}): {e}")
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


# -------------------------------------------------------------------------
# ENDPOINTS
# -------------------------------------------------------------------------
@router.post("/genres", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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


@router.post("/initial", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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
        series_target=payload.series_target
    )
    return JobResponse(
        job="initial_ingest",
        message=f"Ingesta inicial encolada en segundo plano (prioridad: {payload.priority or 'config default'})."
    )


@router.post("/daily", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_daily_sync(
    payload: DailySyncRequest,
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Ejecuta la sincronización diaria de cambios TMDB y cartelera en background."""
    background_tasks.add_task(_run_job_daily, hours_window=payload.hours_window)
    return JobResponse(
        job="daily_sync",
        message=f"Sincronización diaria iniciada en segundo plano (ventana: {payload.hours_window or 'config default'} hs)."
    )


@router.post("/percentiles", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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


@router.post("/reviews", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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


@router.post("/import-tmdb", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_import_tmdb_id(
    payload: ImportTMDBRequest,
    background_tasks: BackgroundTasks,
    _: Any = Depends(get_current_admin)
) -> JobResponse:
    """Importa un título específico de TMDB por su identificador en background."""
    background_tasks.add_task(_run_job_import_tmdb, tmdb_id=payload.tmdb_id, media_type=payload.type)
    return JobResponse(
        job="import_tmdb",
        message=f"Importación de {payload.type} con TMDB ID {payload.tmdb_id} iniciada en segundo plano."
    )


@router.post("/import-json", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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
