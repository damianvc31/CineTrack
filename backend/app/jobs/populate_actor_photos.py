import argparse
import asyncio
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.actor import Actor, titulos_elenco
from app.models.titulo import Titulo
from app.services.tmdb_client import TMDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("populate_actor_photos")


async def populate_actor_photos(
    limit: Optional[int] = 100,
    actor_id: Optional[int] = None,
    batch_size: int = 20,
    db: Optional[AsyncSession] = None,
    client: Optional[TMDBClient] = None
) -> dict[str, int]:
    """
    Busca fotos de perfil en TMDB para actores que no tienen foto_url,
    priorizando los actores de títulos más populares.
    """
    own_client = client is None
    tmdb_client = client or TMDBClient()

    total_updated = 0
    total_checked = 0

    async def _execute_with_session(session: AsyncSession):
        nonlocal total_updated, total_checked

        query = select(Actor).where(Actor.tmdb_id.isnot(None))
        if actor_id:
            query = query.where(Actor.id == actor_id)
        else:
            # Priorizar actores de películas/series más populares y con menor orden de elenco
            query = (
                query.where(Actor.foto_url.is_(None))
                .outerjoin(titulos_elenco, titulos_elenco.c.actor_id == Actor.id)
                .outerjoin(Titulo, Titulo.id == titulos_elenco.c.titulo_id)
                .group_by(Actor.id)
                .order_by(func.coalesce(func.max(Titulo.popularidad), 0).desc(), Actor.id.asc())
            )
            if limit is not None:
                query = query.limit(limit)

        res = await session.execute(query)
        actors = res.scalars().all()

        logger.info(f"Encontrados {len(actors)} actores sin foto_url (límite: {limit or 'sin límite'}) para consultar en TMDB...")

        for idx, actor in enumerate(actors, 1):
            total_checked += 1
            try:
                person_data = await tmdb_client.get_person(actor.tmdb_id)
                profile_path = person_data.get("profile_path")
                if profile_path:
                    actor.foto_url = f"https://image.tmdb.org/t/p/w185{profile_path}"
                    total_updated += 1
                    logger.info(f"[{idx}/{len(actors)}] Foto encontrada para '{actor.nombre}': {actor.foto_url}")
                else:
                    logger.debug(f"[{idx}/{len(actors)}] '{actor.nombre}' no tiene profile_path en TMDB.")
            except Exception as err:
                logger.warning(f"[{idx}/{len(actors)}] Error consultando TMDB para '{actor.nombre}' ({actor.tmdb_id}): {err}")

            if total_checked % batch_size == 0:
                await session.commit()
                logger.info(f"Progreso: {total_checked}/{len(actors)} procesados ({total_updated} fotos actualizadas).")

            await asyncio.sleep(0.05)

        await session.commit()
        logger.info(f"Finalizado: {total_checked} actores procesados, {total_updated} fotos de perfil actualizadas exitosamente.")
        return {"total_checked": total_checked, "total_updated": total_updated}

    try:
        if db is not None:
            return await _execute_with_session(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _execute_with_session(session)
    finally:
        if own_client:
            await tmdb_client.close()


def main():
    parser = argparse.ArgumentParser(description="Poblar fotos de actores desde TMDB")
    parser.add_argument("--limit", type=int, default=100, help="Límite de actores a procesar (default: 100, 0 o omitido para sin límite)")
    parser.add_argument("--actor-id", type=int, default=None, help="Procesar un actor específico por ID local")
    parser.add_argument("--batch-size", type=int, default=20, help="Tamaño de lote para commits (default: 20)")
    args = parser.parse_args()

    lim = args.limit if args.limit and args.limit > 0 else None
    asyncio.run(populate_actor_photos(limit=lim, actor_id=args.actor_id, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
