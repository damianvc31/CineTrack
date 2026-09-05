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
    parser.add_argument("--daily", action="store_true", help="Ejecutar sincronización diaria")
    parser.add_argument("--percentiles", action="store_true", help="Recalcular percentiles de popularidad")
    parser.add_argument("--import-json", type=str, help="Ruta al archivo JSON con títulos a importar")
    parser.add_argument("--import-tmdb-id", type=int, help="Importar un título específico por su ID de TMDB")
    parser.add_argument("--type", choices=["movie", "tv"], default="movie", help="Tipo de título para --import-tmdb-id")

    args = parser.parse_args()

    client = TMDBClient()

    try:
        async with AsyncSessionLocal() as db:
            service = TMDBSyncService(db, client)

            if args.genres:
                logger.info("-> Sincronizando géneros...")
                count = await service.sync_genres()
                logger.info(f"Total géneros nuevos agregados: {count}")

            elif args.initial:
                logger.info(f"-> Ejecutando ingesta inicial (prioridad: {args.priority or 'default'})...")
                res = await service.run_initial_ingest(priority=args.priority)
                logger.info(f"Resultado de ingesta inicial: {res}")

            elif args.daily:
                logger.info("-> Ejecutando sincronización diaria...")
                res = await service.run_daily_sync()
                logger.info(f"Resultado sincronización diaria: {res}")

            elif args.percentiles:
                logger.info("-> Recalculando percentiles de popularidad...")
                await service.recalculate_percentiles()
                logger.info("Percentiles recalculados exitosamente.")

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
                logger.info(f"-> Importando {args.type} TMDB ID: {args.import_tmdb_id}...")
                if args.type == "movie":
                    titulo = await service.upsert_movie(args.import_tmdb_id)
                else:
                    titulo = await service.upsert_series(args.import_tmdb_id, fetch_episodes=True)
                if titulo:
                    await db.commit()
                    await service.recalculate_percentiles()
                    logger.info(f"Título importado con éxito: {titulo.titulo} (ID local: {titulo.id})")
                else:
                    logger.error(f"No se pudo importar el título con ID {args.import_tmdb_id}")

            else:
                parser.print_help()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

