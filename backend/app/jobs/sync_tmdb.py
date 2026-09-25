import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from app.db.session import AsyncSessionLocal
from app.services.tmdb_sync_service import TMDBSyncService
from app.services.tmdb_client import TMDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sync_tmdb")


async def main():
    parser = argparse.ArgumentParser(description="CineTrack - Sincronización e Ingesta de TMDB")
    parser.add_argument("--genres", action="store_true", help="Sincronizar catálogo de géneros")
    parser.add_argument("--initial", action="store_true", help="Ejecutar ingesta inicial de títulos")
    parser.add_argument("--priority", choices=["popular_first", "toprated_first"], default=None, help="Prioridad de ingesta inicial")
    parser.add_argument("--movies-target", type=int, default=None, help="Cantidad objetivo de películas para ingesta inicial")
    parser.add_argument("--series-target", type=int, default=None, help="Cantidad objetivo de series para ingesta inicial")
    parser.add_argument("--daily", action="store_true", help="Ejecutar sincronización diaria liviana")
    parser.add_argument("--deep", action="store_true", help="Ejecutar sincronización profunda semanal de cambios TMDB")
    parser.add_argument("--changes-days", type=int, default=None, help="Ventana en días para consultar /changes de TMDB en sincronización profunda (default: 7 días, máx: 14)")
    parser.add_argument("--changes-hours", type=int, default=None, help="Ventana en horas para consultar /changes de TMDB en series y películas (default config: 48 hs, ej. 120 para 5 días)")
    parser.add_argument("--releases-days", type=int, default=None, help="Ventana en días para consultar estrenos recientes en cartelera (default config: 15 días)")
    parser.add_argument("--hours-window", type=int, default=None, help="Alias compatible de --changes-hours")
    parser.add_argument("--allow-unreleased", action="store_true", default=False, help="Permitir títulos no estrenados (películas futuras o series sin temporadas emitidas, default: False)")
    parser.add_argument("--cleanup-unreleased", action="store_true", help="Eliminar títulos no estrenados existentes de la base de datos y recalcular métricas")
    parser.add_argument("--percentiles", action="store_true", help="Recalcular percentiles de popularidad")
    parser.add_argument("--ratings", action="store_true", help="Recalcular rating unificado para todos los títulos")
    parser.add_argument("--refresh-metrics", action="store_true", help="Refrescar popularidad y votos para todo el catálogo desde TMDB")
    parser.add_argument("--backfill-countries", action="store_true", help="Actualizar la columna 'pais' con origen y producción consolidados para todo el catálogo")
    parser.add_argument("--purge-incomplete", action="store_true", help="Purgar títulos con caracteres no latinos o sin fecha, idioma o país")
    parser.add_argument("--reviews", action="store_true", help="Sincronizar reseñas de TMDB para todos los títulos hasta el tope (20)")
    parser.add_argument("--import-json", type=str, help="Ruta al archivo JSON con títulos a importar")
    parser.add_argument("--import-tmdb-id", type=str, help="Importar o actualizar títulos por ID(s) de TMDB (ej. 319562 o separados por coma: 319562,550)")
    parser.add_argument("--type", choices=["movie", "tv"], default="movie", help="Tipo de título para --import-tmdb-id")
    parser.add_argument("--expand", action="store_true", help="Expande el catálogo por géneros vía /discover con filtros de calidad (Criterio 1)")
    parser.add_argument("--genre", type=str, default=None, help="Género específico para --expand (nombre o ID). Si se omite, procesa todos los géneros")
    parser.add_argument("--media-type", choices=["both", "movie", "tv"], default="both", help="Tipo de medio a expandir ('both', 'movie' o 'tv')")
    parser.add_argument("--min-vote-count", type=int, default=None, help="Mínimo de votos para --expand (default config)")
    parser.add_argument("--min-vote-average", type=float, default=None, help="Mínimo de calificación promedio para --expand (default config)")
    parser.add_argument("--target-per-genre", type=int, default=None, help="Cantidad objetivo de títulos por género para --expand (default config)")
    parser.add_argument("--clear", action="store_true", help="Vaciar todo el catálogo de títulos y entidades dependientes")

    args = parser.parse_args()

    client = TMDBClient()

    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)

            if args.clear:
                logger.warning("-> Vaciando catálogo completo de títulos y relaciones...")
                from app.services.catalog_service import clear_entire_catalog
                res = await clear_entire_catalog(db)
                logger.info(f"Catálogo vaciado exitosamente: {res}")

            elif args.genres:
                logger.info("-> Sincronizando géneros...")
                count = await service.sync_genres()
                logger.info(f"Total géneros nuevos agregados: {count}")

            elif args.initial:
                logger.info(f"-> Ejecutando ingesta inicial (prioridad: {args.priority or 'default'}, allow_unreleased: {args.allow_unreleased})...")
                res = await service.run_initial_ingest(
                    priority=args.priority,
                    movies_target=args.movies_target,
                    series_target=args.series_target,
                    allow_unreleased=args.allow_unreleased,
                )
                logger.info(f"Resultado de ingesta inicial: {res}")

            elif args.daily:
                logger.info(f"-> Ejecutando sincronización diaria liviana (allow_unreleased: {args.allow_unreleased})...")
                changes_h = args.changes_hours if args.changes_hours is not None else args.hours_window
                res = await service.run_daily_sync(
                    changes_hours_window=changes_h,
                    releases_days_window=args.releases_days,
                    allow_unreleased=args.allow_unreleased,
                )
                logger.info(f"Resultado sincronización diaria: {res}")

            elif args.deep:
                logger.info(f"-> Ejecutando sincronización profunda semanal (changes_days: {args.changes_days or 7}, allow_unreleased: {args.allow_unreleased})...")
                res = await service.run_deep_sync(
                    changes_days_window=args.changes_days,
                    releases_days_window=args.releases_days,
                    allow_unreleased=args.allow_unreleased,
                )
                logger.info(f"Resultado sincronización profunda: {res}")

            elif args.cleanup_unreleased:
                logger.info("-> Saneando catálogo: eliminando títulos no estrenados...")
                res = await service.cleanup_unreleased_titles()
                logger.info(f"Resultado de saneamiento: {res}")

            elif args.percentiles:
                logger.info("-> Recalculando percentiles de popularidad y ratings unificados...")
                await service.recalculate_percentiles()
                await service.recalculate_unified_ratings()
                logger.info("Métricas recalculadas exitosamente.")

            elif args.ratings:
                logger.info("-> Recalculando rating unificado para todos los títulos...")
                total = await service.recalculate_unified_ratings()
                logger.info(f"Rating unificado recalculado para {total} títulos.")

            elif args.refresh_metrics:
                logger.info("-> Refrescando métricas (popularidad y votos) para todo el catálogo...")
                res = await service.refresh_catalog_metrics()
                logger.info(f"Métricas refrescadas exitosamente: {res}")

            elif args.reviews:
                logger.info("-> Sincronizando reseñas de TMDB para todos los títulos...")
                res = await service.sync_all_missing_reviews()
                logger.info(f"Resultado de sincronización de reseñas: {res}")

            elif args.import_json:
                path = Path(args.import_json)
                if not path.exists():
                    logger.error(f"El archivo {args.import_json} no existe.")
                    sys.exit(1)
                logger.info(f"-> Importando títulos desde {path}...")
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
                res = await service.import_from_json_data(data)
                logger.info(f"Importación completada: {res['imported']} importados, {len(res['errors'])} errores.")
                if res["errors"]:
                    for err in res["errors"]:
                        logger.warning(f"  - {err}")

            elif args.import_tmdb_id:
                # Soportar un ID o varios separados por comas
                raw_ids = [s.strip() for s in str(args.import_tmdb_id).split(",") if s.strip().isdigit()]
                if not raw_ids:
                    logger.error(f"Valor inválido para --import-tmdb-id: {args.import_tmdb_id}")
                    sys.exit(1)

                logger.info(f"-> Importando/actualizando {len(raw_ids)} títulos ({args.type}): {raw_ids}...")
                success_count = 0
                for r_id_str in raw_ids:
                    t_id = int(r_id_str)
                    try:
                        if args.type == "movie":
                            titulo = await service.upsert_movie(t_id, fetch_reviews=True)
                        else:
                            titulo = await service.upsert_series(t_id, fetch_episodes=True, fetch_reviews=True)
                        if titulo:
                            await db.commit()
                            success_count += 1
                            logger.info(f"  [OK] '{titulo.nombre}' (TMDB ID: {t_id}, ID local: {titulo.id})")
                        else:
                            logger.error(f"  [FAIL] No se pudo obtener/guardar título con ID {t_id}")
                    except Exception as e:
                        logger.error(f"  [ERROR] Fallo al procesar ID {t_id}: {e}")
                        await db.rollback()

                if success_count > 0:
                    await service.recalculate_percentiles()
                    await service.recalculate_unified_ratings()
                    try:
                        await service.sync_pending_embeddings()
                    except Exception as e:
                        logger.warning(f"No se pudieron sincronizar embeddings: {e}")
                    try:
                        from app.services.catalog_service import clear_catalog_cache
                        clear_catalog_cache()
                    except Exception:
                        pass
                logger.info(f"Importación de IDs completada: {success_count}/{len(raw_ids)} procesados con éxito.")

            elif args.expand:
                genre_desc = args.genre or "TODOS los géneros"
                logger.info(f"-> Ejecutando expansión de catálogo por géneros (Criterio 1) para: {genre_desc}...")
                res = await service.expand_catalog_by_genres(
                    genre=args.genre,
                    media_type=args.media_type,
                    target_per_genre=args.target_per_genre,
                    min_vote_count=args.min_vote_count,
                    min_vote_average=args.min_vote_average,
                    allow_unreleased=args.allow_unreleased,
                )
            elif args.backfill_countries:
                logger.info("-> Ejecutando backfill de países consolidados para todo el catálogo...")
                res = await service.backfill_catalog_countries()
                logger.info(f"Backfill de países completado: {res}")

            elif args.purge_incomplete:
                logger.info("-> Ejecutando purga selectiva de títulos incompletos o no legibles...")
                res = await service.purge_invalid_or_incomplete_titles()
                logger.info(f"Purga completada: {res['purged_count']} títulos eliminados.")

            else:
                parser.print_help()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

