import argparse
import asyncio
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.actor import Actor
from app.services.tmdb_client import TMDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("populate_actor_photos")


async def populate_actor_photos(limit: int = 100, actor_id: int | None = None, batch_size: int = 20):
    client = TMDBClient()
    total_updated = 0
    total_checked = 0

    try:
        async with AsyncSessionLocal() as db:
            query = select(Actor).where(Actor.tmdb_id.isnot(None))
            if actor_id:
                query = query.where(Actor.id == actor_id)
            else:
                query = query.where(Actor.foto_url.is_(None)).limit(limit)

            res = await db.execute(query)
            actors = res.scalars().all()

            logger.info(f"Encontrados {len(actors)} actores sin foto_url para consultar en TMDB...")

            for idx, actor in enumerate(actors, 1):
                total_checked += 1
                try:
                    person_data = await client.get_person(actor.tmdb_id)
                    profile_path = person_data.get("profile_path")
                    if profile_path:
                        actor.foto_url = f"https://image.tmdb.org/t/p/w185{profile_path}"
                        total_updated += 1
                        logger.info(f"[{idx}/{len(actors)}] Foto encontrada para '{actor.nombre}': {actor.foto_url}")
                    else:
                        logger.debug(f"[{idx}/{len(actors)}] '{actor.nombre}' no tiene profile_path en TMDB.")
                except Exception as err:
                    logger.warning(f"[{idx}/{len(actors)}] Error consultando TMDB para '{actor.nombre}' ({actor.tmdb_id}): {err}")

                # Commit en lotes
                if total_checked % batch_size == 0:
                    await db.commit()
                    logger.info(f"Progreso: {total_checked}/{len(actors)} procesados ({total_updated} fotos actualizadas).")

                # Breve pausa para respetar rate limit
                await asyncio.sleep(0.05)

            await db.commit()
            logger.info(f"Finalizado: {total_checked} actores procesados, {total_updated} fotos de perfil actualizadas exitosamente.")
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(description="Poblar fotos de actores desde TMDB")
    parser.add_argument("--limit", type=int, default=100, help="Límite de actores a procesar (default: 100)")
    parser.add_argument("--actor-id", type=int, default=None, help="Procesar un actor específico por ID local")
    parser.add_argument("--batch-size", type=int, default=20, help="Tamaño de lote para commits (default: 20)")
    args = parser.parse_args()

    asyncio.run(populate_actor_photos(limit=args.limit, actor_id=args.actor_id, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
