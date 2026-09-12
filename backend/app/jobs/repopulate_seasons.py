import argparse
import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.titulo import Titulo
from app.models.temporada import Temporada
from app.services.tmdb_client import TMDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("repopulate_seasons")


async def repopulate_series_seasons(db, client: TMDBClient, tmdb_id: int | None = None):
    query = select(Titulo).where(Titulo.tipo == "tv")
    if tmdb_id:
        query = query.where(Titulo.tmdb_id == tmdb_id)

    res = await db.execute(query)
    series_list = res.scalars().all()
    logger.info(f"Checking confirmed seasons for {len(series_list)} TV series in database...")

    total_added = 0
    total_updated = 0

    for idx, titulo in enumerate(series_list, 1):
        try:
            details = await client.get_details("tv", titulo.tmdb_id)
        except Exception as err:
            logger.warning(f"[{idx}/{len(series_list)}] Failed to fetch TMDB details for {titulo.nombre} ({titulo.tmdb_id}): {err}")
            continue

        seasons_data = details.get("seasons", [])
        if not seasons_data:
            continue

        # Check existing seasons in DB
        res_seasons = await db.execute(select(Temporada).where(Temporada.titulo_id == titulo.id))
        existing_seasons = {s.numero: s for s in res_seasons.scalars().all()}

        # Also update status_tmdb and proximo_episodio_fecha if changed
        new_status = details.get("status")
        if new_status and new_status != titulo.status_tmdb:
            titulo.status_tmdb = new_status

        next_ep = details.get("next_episode_to_air")
        if next_ep and next_ep.get("air_date"):
            try:
                titulo.proximo_episodio_fecha = datetime.strptime(next_ep["air_date"], "%Y-%m-%d").date()
            except ValueError:
                pass

        series_added = 0
        for s_info in seasons_data:
            s_num = s_info.get("season_number")
            if s_num is None or s_num < 1:  # ignore specials (season 0)
                continue

            s_air_date = None
            s_ad_str = s_info.get("air_date")
            if s_ad_str:
                try:
                    s_air_date = datetime.strptime(s_ad_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if s_num not in existing_seasons:
                overview = s_info.get("overview") or None
                new_season = Temporada(
                    titulo_id=titulo.id,
                    numero=s_num,
                    sinopsis=overview,
                    fecha_estreno=s_air_date,
                )
                db.add(new_season)
                existing_seasons[s_num] = new_season
                total_added += 1
                series_added += 1
            else:
                existing_season = existing_seasons[s_num]
                if s_air_date and existing_season.fecha_estreno != s_air_date:
                    existing_season.fecha_estreno = s_air_date
                    total_updated += 1

        if series_added > 0:
            logger.info(f"[{idx}/{len(series_list)}] {titulo.nombre}: added {series_added} confirmed upcoming season(s)")
            await db.flush()

    await db.commit()
    logger.info(f"Done. Total new confirmed seasons added: {total_added}, updated dates: {total_updated}")


async def main():
    parser = argparse.ArgumentParser(description="Repopulate confirmed TV seasons from TMDB")
    parser.add_argument("--tmdb-id", type=int, help="Single series TMDB ID to check/repopulate")
    args = parser.parse_args()

    client = TMDBClient()
    try:
        async with AsyncSessionLocal() as db:
            await repopulate_series_seasons(db, client, tmdb_id=args.tmdb_id)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
