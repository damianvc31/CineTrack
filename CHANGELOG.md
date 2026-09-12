# CHANGELOG.md — Registro de Cambios: CineTrack

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [v0.5.4] - 2026-09-12
### Agregado
- Exposición de `popularidad_percentil` en los esquemas `TitleCardResponse` y `TitleDetailResponse` para alimentar el badge visual de popularidad (🔥 xx%) en las tarjetas de la UI.
- Separación ortogonal de parámetros en `GET /api/v1/titles`:
  - `section`: Filtro de colección curada (`new_releases`, `trending`, `classics`, `top_rated`, `others`).
  - `sort_by`: Criterio puro de ordenamiento (`popularity`, `rating`, `release_date`, `title`).
  - `order`: Dirección del ordenamiento (`desc` por defecto, `asc`).
- Soporte para filtrado por nombres en texto (strings) además de IDs:
  - `genero`: Nombre de género insensible a mayúsculas (ej. `Drama`, `Fantasy`, `Comedy`).
  - `actor`: Nombre de actor del elenco (ej. `DiCaprio`, `Tom Cruise`).
  - `actor_id`: Identificador numérico de actor para navegación directa desde fichas de reparto.
- Búsqueda abierta por texto (`q`) extendida para buscar coincidencias tanto en título, director y guionista como en actores del elenco.

### Modificado
- Robustez en cálculo de Trending para series: ahora evalúa la fecha de emisión del último episodio real emitido (`MAX(Episodio.fecha_estreno)`), evitando falsos positivos con temporadas futuras sin episodios.
- Persistencia de `fecha_estreno` en el modelo `Temporada` durante la sincronización TMDB y backfill en base de datos (`cinetrack.db`) para 7.481 temporadas.
- Depuración de 181 temporadas vacías (placeholders sin episodios emitidos) en catálogo local y regla de omisión automática en `upsert_series`.

## [v0.5.3] - 2026-09-12
### Modificado
- Restricción de unicidad de TMDB convertida a clave candidata compuesta: `UNIQUE (tmdb_id, tipo)` en la tabla `titulos`, permitiendo que películas y series con el mismo identificador de TMDB (ej. *The Lord of the Rings: The Two Towers* y *Doctor Who*, ambas ID 121) coexistan sin colisiones.
- Migración de base de datos Alembic `0004_composite_tmdb_id_tipo.py`.
- Test unitario automatizado `test_pelicula_y_serie_mismo_tmdb_id` en `test_models.py` (suite total ampliada a 45 tests, 100% pasando en verde en < 5s).

## [v0.5.2] - 2026-09-12
### Agregado
- Endpoint administrativo de vaciado `DELETE /api/v1/admin/catalog?confirm=true` y opción CLI `python -m app.jobs.sync_tmdb --clear` con limpieza en cascada (títulos, temporadas, episodios, reseñas, estados y actores huérfanos) preservando usuarios y catálogo de géneros.

## [v0.5.1] - 2026-09-12
### Modificado
- Migración de columnas de año a fechas exactas (`Date`): `fecha_estreno` y `fecha_fin` en el modelo `Titulo` (manteniendo propiedades `@property anio_estreno` y `@property anio_fin` con setters para compatibilidad completa).
- Migración de base de datos Alembic `0003_dates_and_home_specs.py`.
- Refactorización de la lógica del catálogo de inicio (`/api/v1/home`):
  - **New Releases:** títulos estrenados en los últimos 60 días (configurable).
  - **Trending:** títulos de los últimos 90 días por popularidad, considerando la fecha de la última temporada para series de TV.
  - **Classics:** exclusivamente películas con más de 20 años de antigüedad, rating $\ge 7.5$ y $\ge 500$ votos; muestra aleatoria de un pool de 50 títulos (omitido cuando se filtra por `tipo=tv`).
  - **Top Rated:** muestra aleatoria de las mejores calificadas con al menos 100 votos (pool de 100).
  - **By Genre y Others:** carruseles individuales para géneros con $\ge 10$ títulos; géneros minoritarios con $< 10$ títulos agrupados en la sección `others`.
  - **Exclusión de Vistos:** omisión automática de títulos marcados con estado `vista` para usuarios autenticados en todas las secciones exploratorias de Home.
- Documentación en `README.md`: sección de comandos de migraciones Alembic (`upgrade`, `current`, `history`, `revision`, `downgrade`).
- Optimización de pruebas en `test_admin.py`: mock de `BackgroundTasks.add_task` previniendo disparos de workers reales a TMDB durante pruebas de API; la suite completa de 42 tests corre en menos de 5 segundos.

## [v0.5.0] - 2026-09-12
### Agregado
- Endpoints de Catálogo y Home (`/api/v1/home`, `/api/v1/titles`, `/api/v1/titles/{id}`, `/api/v1/genres`) con soporte para filtros por tipo, género, búsqueda por texto, ordenamiento y paginación.
- Endpoints de Reseñas (`GET /api/v1/titles/{id}/reviews` y `POST /api/v1/titles/{id}/reviews`) con creación de reseñas de usuario y recálculo automático de `rating_unificado`.
- Endpoints de Perfil y Biblioteca (`GET /api/v1/users/me/library` y `GET /api/v1/users/me/stats`) con cálculo de horas vistas, distribución de géneros y rankings Top 5 según wireframes.
- Esquemas Pydantic v2 en `backend/app/schemas/catalog.py` y capa de servicios `backend/app/services/catalog_service.py`.
- Suite ampliada a 40 tests unitarios e integración (100% pasando en verde).

## [v0.4.3] - 2026-09-11
### Agregado
- Router administrativo `/api/v1/admin/sync` para ejecutar jobs en segundo plano con `BackgroundTasks` de FastAPI (`HTTP 202 Accepted`): `/initial`, `/daily`, `/genres`, `/percentiles`, `/reviews`, `/import-tmdb` e `/import-json`, con soporte completo para todos los parámetros de configuración.
- Autenticación dual administrativa: soporte para JWT de usuario administrador (`es_admin=True`) y cabecera `X-Admin-Key` validada contra `ADMIN_API_KEY`.
- Columna indexada y persistida `rating_unificado` en modelo `Titulo` con recálculo automático ponderado de TMDB y reseñas locales (`recalculate_unified_ratings`).
- Enriquecimiento de la tabla asociativa `titulos_elenco` con columnas `personaje` y `orden`, vinculada mediante el modelo relacional `TituloElenco`.
- Parametrización en configuración de la ventana horaria para cambios en TMDB (`TMDB_CHANGES_HOURS_WINDOW`, default 48 horas) y configuración `TMDB_LANGUAGE` (default `en-US`).
- Endpoints semánticos para tracking de series y temporadas:
  - `POST /titles/{title_id}/seasons/{season_number}/episodes/{episode_number}/watch`: marcar/desmarcar episodio por numeración semántica (ej. S01E02).
  - `POST /seasons/{season_id}/watch` y `POST /titles/{title_id}/seasons/{season_number}/watch`: marcar/desmarcar temporada completa en lote con recálculo automático del estado de la serie.
- Migración Alembic `0002_technical_adjustments.py` y suite de tests ampliada a 35 tests automatizados (100% pasando en verde).
- Actualización de diagramas UML en `docs/UML/modelo_datos/`.

## [v0.4.2] - 2026-09-05
### Agregado
- Integración proactiva de los endpoints `/tv/changes` y `/movie/changes` en `run_daily_sync`: detección automática de series con nuevos episodios o cambio de estado emitidos en las últimas 48h (incluso si ningún usuario las sigue aún) y actualización de películas del catálogo local con mínimo consumo de cuota de API.
- Especificación formal y matemática de la fórmula de calificación unificada en `README.md` y `ARCHITECTURE.md`.
- Test unitario de integración `test_daily_sync_updates_untracked_titles_from_changes` comprobando la actualización autónoma de títulos locales no seguidos mediante `/changes`.

## [v0.4.1] - 2026-09-05
### Agregado
- Sincronización de reseñas externas de TMDB con límite configurable (`TMDB_REVIEWS_PER_TITLE_LIMIT = 20`) por título en `TMDBSyncService.sync_reviews_for_title` y `sync_all_missing_reviews`.
- Comando CLI dedicado `python -m app.jobs.sync_tmdb --reviews` para backfill y actualización desatendida de reseñas.
- Definición de política de autor polimórfico en reseñas de TMDB (exclusivamente contexto descriptivo sin alterar votos agregados de TMDB).

## [v0.4.0] - 2026-09-05
### Agregado
- Cliente asíncrono para la API de TMDB (`TMDBClient`) en `backend/app/services/tmdb_client.py` con `httpx`, autenticación Bearer Token v4 / api_key v3, semáforo de concurrencia y reintentos exponenciales.
- Servicio de ingesta y sincronización (`TMDBSyncService`) en `backend/app/services/tmdb_sync_service.py`:
  - Sincronización idempotente del catálogo de géneros (películas y series).
  - Ingesta inicial parametrizable con cuotas configurables (`TMDB_INGEST_MOVIES_TARGET`, `TMDB_INGEST_SERIES_TARGET`, defaults 1000 títulos).
  - Switch configurable de estrategia de ingesta: `popular_first` (tendencias primero y resto top-rated) o `toprated_first` (clásicos históricos primero y resto tendencias).
  - Enriquecimiento de directores, guionistas (hasta 3) y elenco (hasta 15 actores principales ordenados por créditos).
  - Ingesta estructurada de temporadas y episodios para series con mapeo de `anio_fin` desde `last_air_date` para producciones finalizadas o canceladas.
  - Sincronización diaria: refresco de series en seguimiento (`siguiendo`), absorción de nuevos episodios e ingesta de estrenos calificados dentro de una ventana de 15 días con popularidad >= 10.0.
  - Soporte de importación manual mediante JSON (`docs/templates/`) con resolución inteligente obligatoria de ID de TMDB por título/año (rechazando títulos huérfanos sin respaldo en la API para garantizar sincronización futura).
  - Motor de recálculo de percentiles de popularidad con ventana analítica SQL `PERCENT_RANK()` y fallback en memoria.
- Interfaz CLI ejecutable en `backend/app/jobs/sync_tmdb.py` para correr tareas manuales o cron jobs (`--genres`, `--initial`, `--priority`, `--daily`, `--percentiles`, `--reviews`, `--import-json`, `--import-tmdb-id`).
- Plantillas JSON de muestra documentadas en `docs/templates/template_pelicula.json` y `docs/templates/template_serie.json`.
- Fixtures sintéticas y suite de pruebas unitarias/integración con mocks en `backend/tests/test_tmdb_sync.py` (8 tests de TMDB, 24/24 tests pasando en verde en backend con cero gasto de cuota de API).

## [v0.3.0] - 2026-09-05
### Agregado
- Módulo de seguridad con hashing de contraseñas (`bcrypt`) y tokens JWT (`pyjwt`) firmado con `AUTH_SECRET_KEY` en `backend/app/core/security.py`.
- Endpoints de autenticación en `backend/app/api/v1/auth.py` (`POST /register`, `POST /login`, `GET /me`) y dependencia de seguridad `get_current_user`.
- Esquemas Pydantic v2 para autenticación y estados en `backend/app/schemas/`.
- Motor transaccional de estados de título en `backend/app/services/state_service.py` con soporte completo de transiciones para películas y series:
  - Toggle de Favorito (ortogonal).
  - Watchlist con bloqueo estricto (400) si el título está en Vista o Siguiendo.
  - Visto con limpieza de episodios asociados al desmarcar serie completa.
  - Abandonar serie (❌) conservando episodios vistos.
  - Seguimiento granular por episodio con recálculo automático de estado de serie y bloqueo de episodios futuros.
- Endpoints de estados en `backend/app/api/v1/states.py` (`/titles/{id}/favorite`, `/titles/{id}/watchlist`, `/titles/{id}/watched`, `/titles/{id}/unfollow`, `/titles/{id}/user-state`, `/episodes/{id}/watch`).
- Suite exhaustiva de pruebas en `backend/tests/test_auth.py` y `backend/tests/test_state_machine.py` (16 tests totales en verde).

## [v0.2.0] - 2026-09-05
### Agregado
- Modelos relacionales declarativos con SQLAlchemy 2.0 async en `backend/app/models/` (`Usuario`, `Titulo`, `Genero`, `Actor`, `Temporada`, `Episodio`, `EstadoUsuarioTitulo`, `EpisodioVisto`, `Resena`).
- Infraestructura de conexión y sesión asíncrona en `backend/app/db/` (`base.py`, `session.py`).
- Configuración de migraciones asíncronas con Alembic y primera migración de esquema `0001_initial_schema.py`.
- Suite exhaustiva de pruebas de modelos e integridad referencial en `backend/tests/test_models.py` (7 tests en verde).
- Integración de fixture de base de datos aislada en memoria con SQLite async (`aiosqlite`) para testing automatizado sin dependencias externas activas.

## [v0.1.0] - 2026-09-05
### Agregado
- Evaluación crítica de arquitectura aprobada y consolidada en `ARCHITECTURE.md`.
- Scaffolding base del backend con FastAPI (`backend/`).
- Suite de pruebas del backend con Pytest y smoke test inicial de salud en verde.
- Scaffolding base del frontend con Vite + React + TypeScript + Tailwind CSS (`frontend/`).
- Suite de pruebas del frontend con Vitest y smoke test inicial en verde.
- Documentación viva del proyecto (`README.md`, `TASK_PLAN.md`, `ROADMAP.md`).
