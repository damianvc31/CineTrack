import argparse
import asyncio
import logging
import time
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.titulo import Titulo
from app.services.embedding_service import EmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sync_embeddings")


async def sync_catalog_embeddings(
    batch_size: int = 50,
    limit: Optional[int] = None,
    force: bool = False,
    db: Optional[AsyncSession] = None,
    embedding_service: Optional[EmbeddingService] = None,
) -> dict[str, int]:
    """
    Sincroniza y calcula los vectores de embedding para los títulos del catálogo
    que aún no tienen vector generado (o todos si force=True).
    """
    emb_svc = embedding_service or EmbeddingService()

    total_updated = 0
    total_failed = 0
    total_pending = 0

    async def _execute_with_session(session: AsyncSession):
        nonlocal total_updated, total_failed, total_pending

        bind = session.bind or (session.get_bind() if hasattr(session, "get_bind") else None)
        if bind and bind.dialect.name != "postgresql":
            logger.info("Base de datos actual es SQLite (sin soporte pgvector). Omitiendo cálculo de embeddings.")
            return

        query = select(Titulo).options(selectinload(Titulo.generos))
        if not force:
            query = query.where(Titulo.embedding.is_(None))

        # Contar total pendiente
        count_query = select(func.count(Titulo.id))
        if not force:
            count_query = count_query.where(Titulo.embedding.is_(None))
        total_pending = await session.scalar(count_query) or 0

        logger.info(f"Títulos pendientes de embedding: {total_pending} (force={force})")
        if total_pending == 0:
            return

        if limit and limit > 0:
            query = query.limit(limit)
            logger.info(f"Límite aplicado: procesando hasta {limit} títulos.")

        # Ordenar por popularidad descendente para que los títulos más vistos se vectoricen primero
        query = query.order_by(Titulo.popularidad.desc())

        result = await session.execute(query)
        titulos = result.scalars().all()
        to_process = len(titulos)

        logger.info(f"Iniciando cálculo para {to_process} títulos en lotes de {batch_size}...")
        start_time = time.time()

        for i in range(0, to_process, batch_size):
            batch = titulos[i : i + batch_size]
            texts = [
                emb_svc.build_title_text(
                    nombre=t.nombre,
                    tipo=t.tipo,
                    generos=[g.nombre for g in t.generos],
                    director=t.director,
                    sinopsis=t.sinopsis,
                )
                for t in batch
            ]

            embeddings = await emb_svc.get_embeddings_batch(texts)

            for titulo, emb in zip(batch, embeddings):
                if emb:
                    titulo.embedding = emb
                    total_updated += 1
                else:
                    total_failed += 1

            await session.commit()

            processed_so_far = min(i + batch_size, to_process)
            elapsed = time.time() - start_time
            rate = processed_so_far / elapsed if elapsed > 0 else 0
            logger.info(
                f"Progreso: {processed_so_far}/{to_process} títulos procesados "
                f"({total_updated} actualizados, {total_failed} fallos) | "
                f"Velocidad: {rate:.1f} tít/seg"
            )

            # Pausa preventiva entre lotes (4.0s garantiza no superar los 15 RPM por clave)
            await asyncio.sleep(4.0)


    if db:
        await _execute_with_session(db)
    else:
        async with AsyncSessionLocal() as session:
            await _execute_with_session(session)

    return {
        "total_pending": total_pending,
        "total_updated": total_updated,
        "total_failed": total_failed,
    }


def main():
    parser = argparse.ArgumentParser(description="Sincronizador masivo de embeddings vectoriales para CineTrack")
    parser.add_argument("--batch-size", type=int, default=30, help="Tamaño del lote para batchEmbedContents (default: 30)")
    parser.add_argument("--limit", type=int, default=None, help="Límite máximo de títulos a procesar")
    parser.add_argument("--force", action="store_true", help="Recalcular embeddings para títulos que ya tienen uno")

    args = parser.parse_args()

    asyncio.run(
        sync_catalog_embeddings(
            batch_size=args.batch_size,
            limit=args.limit,
            force=args.force,
        )
    )


if __name__ == "__main__":
    main()
