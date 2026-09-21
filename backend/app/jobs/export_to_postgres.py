import argparse
import asyncio
from datetime import date, datetime
import logging
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, inspect, select, text
from sqlalchemy.ext.asyncio import create_async_engine

# Asegurar import de modelos para registrar metadata completa
from app.db.base import Base
import app.models  # noqa: F401
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("export_to_postgres")

# Orden estricto respetando Foreign Keys
TABLE_EXPORT_ORDER = [
    "generos",
    "actores",
    "usuarios",
    "titulos",
    "titulos_generos",
    "titulos_elenco",
    "temporadas",
    "episodios",
    "resenas",
    "estados_usuario_titulos",
    "episodios_vistos",
]

# Tablas con clave primaria autoincremental / serial en PostgreSQL
SERIAL_PRIMARY_KEYS = {
    "generos": "id",
    "actores": "id",
    "usuarios": "id",
    "titulos": "id",
    "temporadas": "id",
    "episodios": "id",
    "resenas": "id",
    "estados_usuario_titulos": "id",
    "episodios_vistos": "id",
}


def normalize_postgres_url(url: str) -> str:
    """Normaliza la URL para SQLAlchemy + asyncpg."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "sslmode=require" in url:
        url = url.replace("sslmode=require", "ssl=require")
    return url


def transform_value(col_type: Any, val: Any) -> Any:
    """Convierte tipos primitivos de SQLite a los tipos esperados por PostgreSQL/asyncpg."""
    if val is None:
        return None

    if isinstance(col_type, Boolean):
        if isinstance(val, (int, str)):
            return bool(int(val))
        return bool(val)

    if isinstance(col_type, Date):
        if isinstance(val, str):
            clean_str = val.strip()[:10]
            if clean_str:
                try:
                    return date.fromisoformat(clean_str)
                except ValueError:
                    return None
            return None
        return val

    if isinstance(col_type, DateTime):
        if isinstance(val, str):
            clean_str = val.strip()
            if clean_str:
                try:
                    return datetime.fromisoformat(clean_str)
                except ValueError:
                    return None
            return None
        return val

    if isinstance(col_type, Float):
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    return val


def get_sqlite_table_counts(sqlite_path: Path) -> dict[str, int]:
    """Obtiene el recuento de filas por tabla en SQLite."""
    counts = {}
    with sqlite3.connect(sqlite_path) as conn:
        cursor = conn.cursor()
        for table_name in TABLE_EXPORT_ORDER:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                counts[table_name] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table_name] = 0

        # Recuento de alembic_version si existe
        try:
            cursor.execute("SELECT version_num FROM alembic_version")
            row = cursor.fetchone()
            counts["alembic_version"] = 1 if row else 0
        except sqlite3.OperationalError:
            counts["alembic_version"] = 0
    return counts


async def export_data(
    source_sqlite: Path,
    target_url: str,
    batch_size: int = 5000,
    dry_run: bool = False,
    truncate_target: bool = False,
) -> None:
    """Ejecuta la migración de datos desde SQLite a PostgreSQL."""
    if not source_sqlite.exists():
        logger.error(f"Base de datos SQLite origen no encontrada en: {source_sqlite}")
        sys.exit(1)

    counts = get_sqlite_table_counts(source_sqlite)
    total_records = sum(counts[t] for t in TABLE_EXPORT_ORDER)

    logger.info("=" * 65)
    logger.info("CineTrack — Migrador Masivo SQLite -> PostgreSQL")
    logger.info(f"Origen SQLite: {source_sqlite} ({source_sqlite.stat().st_size / (1024 * 1024):.2f} MB)")
    logger.info(f"Total registros a transferir: {total_records:,}")
    logger.info("=" * 65)
    for t in TABLE_EXPORT_ORDER:
        logger.info(f"  • {t:<26} : {counts.get(t, 0):>9,} filas")
    logger.info("=" * 65)

    if dry_run:
        logger.info("[DRY RUN] Verificación completada con éxito. No se realizaron escrituras en PostgreSQL.")
        return

    normalized_url = normalize_postgres_url(target_url)
    # Ocultar contraseña en logs
    safe_display_url = normalized_url
    if "@" in safe_display_url:
        prefix_part, host_part = safe_display_url.split("@", 1)
        scheme_and_user = prefix_part.split(":", 2)
        if len(scheme_and_user) >= 3:
            safe_display_url = f"{scheme_and_user[0]}:{scheme_and_user[1]}:****@{host_part}"

    logger.info(f"Conectando a PostgreSQL destino: {safe_display_url}")

    engine = create_async_engine(
        normalized_url,
        echo=False,
        connect_args={"statement_cache_size": 0},
        pool_pre_ping=True
    )

    t0 = time.perf_counter()

    async with engine.begin() as conn:
        # 1. Crear esquema si no existe
        logger.info("Verificando y creando tablas de base de datos en destino...")
        await conn.run_sync(Base.metadata.create_all)

        # 2. Asegurar tabla alembic_version y sincronizar revisión
        logger.info("Sincronizando estado de versión Alembic (0004_composite_tmdb_id_tipo)...")
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));"
        ))
        await conn.execute(text("DELETE FROM alembic_version;"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0004_composite_tmdb_id_tipo');"))

        # 3. Truncar si se solicitó
        if truncate_target:
            logger.warning("Vaciando tablas destino (--truncate activado)...")
            reversed_tables = list(reversed(TABLE_EXPORT_ORDER))
            truncate_query = "TRUNCATE TABLE " + ", ".join(reversed_tables) + " RESTART IDENTITY CASCADE;"
            try:
                await conn.execute(text(truncate_query))
                logger.info("Tablas truncadas exitosamente.")
            except Exception as e:
                logger.warning(f"Truncate cascade falló ({e}), limpiando con DELETE...")
                for t in reversed_tables:
                    await conn.execute(text(f"DELETE FROM {t};"))

    # 4. Migración tabla por tabla en streaming
    sqlite_conn = sqlite3.connect(source_sqlite)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        for table_name in TABLE_EXPORT_ORDER:
            expected_count = counts.get(table_name, 0)
            if expected_count == 0:
                logger.info(f"[{table_name}] 0 filas para migrar. Omitiendo.")
                continue

            sa_table = Base.metadata.tables.get(table_name)
            if sa_table is None:
                logger.error(f"Tabla {table_name} no encontrada en los metadatos de SQLAlchemy.")
                continue

            col_types = {c.name: c.type for c in sa_table.columns}

            logger.info(f"[{table_name}] Iniciando transferencia de {expected_count:,} filas...")
            t_table = time.perf_counter()

            cursor = sqlite_conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")

            processed = 0
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                batch_dicts = []
                for r in rows:
                    row_dict = {}
                    for col_name in r.keys():
                        if col_name in col_types:
                            row_dict[col_name] = transform_value(col_types[col_name], r[col_name])
                    batch_dicts.append(row_dict)

                async with engine.begin() as conn:
                    await conn.execute(sa_table.insert(), batch_dicts)

                processed += len(batch_dicts)
                pct = (processed / expected_count) * 100
                if expected_count > 10000 and (processed % 25000 == 0 or processed == expected_count):
                    logger.info(f"  • {table_name}: {processed:,} / {expected_count:,} filas ({pct:.1f}%)")

            elapsed_t = time.perf_counter() - t_table
            logger.info(f"[{table_name}] Completada: {processed:,} filas en {elapsed_t:.2f}s ({processed / max(elapsed_t, 0.001):.0f} filas/s).")

        # 5. Sincronizar secuencias serial de PostgreSQL
        logger.info("Actualizando secuencias autoincrementales en PostgreSQL...")
        async with engine.begin() as conn:
            for table_name, pk_col in SERIAL_PRIMARY_KEYS.items():
                try:
                    seq_sql = f"""
                        SELECT setval(
                            pg_get_serial_sequence('{table_name}', '{pk_col}'),
                            COALESCE((SELECT MAX({pk_col}) FROM {table_name}), 1)
                        );
                    """
                    await conn.execute(text(seq_sql))
                except Exception as ex:
                    logger.warning(f"No se pudo actualizar secuencia para {table_name}.{pk_col}: {ex}")

        total_elapsed = time.perf_counter() - t0
        logger.info("=" * 65)
        logger.info(f"Migración completada exitosamente en {total_elapsed:.2f} segundos.")
        logger.info("=" * 65)

    finally:
        sqlite_conn.close()
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="CineTrack - Migración Masiva de SQLite a PostgreSQL")
    parser.add_argument(
        "--target-url",
        type=str,
        default=None,
        help="Cadena de conexión a PostgreSQL destino (o env TARGET_DATABASE_URL / DATABASE_URL)"
    )
    parser.add_argument(
        "--source-db",
        type=str,
        default=None,
        help="Ruta al archivo cinetrack.db origen (por defecto: cinetrack.db en raíz)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Tamaño de lote para inserción (default: 5000)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analiza el origen SQLite y reporta inventario sin escribir en PostgreSQL"
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Vacía las tablas destino antes de insertar"
    )

    args = parser.parse_args()

    # Resolver base de datos origen
    if args.source_db:
        source_path = Path(args.source_db).resolve()
    else:
        root_dir = Path(__file__).resolve().parents[3]
        source_path = root_dir / "cinetrack.db"

    # Resolver URL destino
    target_url = args.target_url or os.getenv("TARGET_DATABASE_URL")
    if not target_url and not args.dry_run:
        # Verificar si settings.DATABASE_URL es postgresql
        if settings.DATABASE_URL.startswith("postgresql"):
            target_url = settings.DATABASE_URL
        else:
            logger.error("Debe proporcionar --target-url o definir TARGET_DATABASE_URL con una conexión a PostgreSQL.")
            sys.exit(1)

    asyncio.run(export_data(
        source_sqlite=source_path,
        target_url=target_url or "",
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        truncate_target=args.truncate
    ))


if __name__ == "__main__":
    main()
