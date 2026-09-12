# TASK_PLAN.md — Plan de Trabajo Activo: CineTrack

## Hito Actual: Fase 3 — Autenticación y Motor de Estados de Título (Completada)

- [x] **Fase 1:** Scaffolding inicial y smoke tests en verde (v0.1.0).
- [x] **Fase 2:** Persistencia y modelos relacionales completos en SQLAlchemy 2.0 (v0.2.0).
- [x] **Fase 3: Autenticación JWT y Motor de Estados (v0.3.0)**
  - [x] Modelo de seguridad con HS256 y expiración configurable.
  - [x] Endpoints `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`.
  - [x] Endpoints `/api/v1/titulos/{id}/estado`, `/api/v1/series/{id}/temporadas/{t}/episodios/{e}/visto`.
  - [x] Transiciones de estado estrictas y seguimiento atómico de episodios.
  - [x] Suite de 16 tests automatizados con `pytest` pasando.
  - [x] Tag `v0.3.0` generado y pusheado a GitHub.

- [x] **Fase 4: Integración TMDB y Sincronización (v0.4.0 - v0.4.2)**
  - [x] Paso 4.1: Plantillas JSON de referencia en `docs/templates/` (`template_pelicula.json`, `template_serie.json`).
  - [x] Paso 4.2: Parámetros de configuración en `backend/app/core/config.py` (cuotas, límites, prioridad de ingesta).
  - [x] Paso 4.3: Esquemas Pydantic de validación para importación manual en `backend/app/schemas/import_export.py`.
  - [x] Paso 4.4: Cliente HTTP asíncrono `TMDBClient` en `backend/app/services/tmdb_client.py` con semáforo de concurrencia y reintentos.
  - [x] Paso 4.5: Servicio `TMDBSyncService` en `backend/app/services/tmdb_sync_service.py` (ingesta inicial popular/top-rated, enriquecimiento de créditos, temporadas/episodios, sync diaria, recálculo de percentiles y carga manual con búsqueda inteligente).
  - [x] Paso 4.6: Script CLI `backend/app/jobs/sync_tmdb.py` para ejecución modular de tareas.
  - [x] Paso 4.7: Fixtures sintéticas de TMDB y suite de pruebas unitarias/integración con mocks en `backend/tests/test_tmdb_sync.py` (Zero-Waste).
  - [x] Paso 4.8: Verificación de tests (23/23 backend tests pasando sin llamadas externas reales).
  - [x] Paso 4.9: Actualización de documentación viva (`ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`, `README.md`).
  - [x] Paso 4.10: Commit y tag `v0.4.0`.
  - [x] Paso 4.11: Sincronización de reseñas TMDB (`--reviews`) y fórmula de rating unificado (v0.4.1).
  - [x] Paso 4.12: Integración de `/tv/changes` y `/movie/changes` en sync diaria (v0.4.2).

- [x] **Ajustes Técnicos Previos a Fase 5 (v0.4.3)**
  - [x] Parametrización de `TMDB_CHANGES_HOURS_WINDOW` (default 48 horas) en `backend/app/core/config.py` y `run_daily_sync`.
  - [x] Persistencia de columna indexada `rating_unificado` en modelo `Titulo` y método `recalculate_unified_ratings` ponderando TMDB + usuarios locales.
  - [x] Enriquecimiento de `titulos_elenco` con columnas `personaje` y `orden` para elenco jerarquizado y detallado.
  - [x] Flag `es_admin` en modelo `Usuario` y clave `ADMIN_API_KEY` para autenticación administrativa.
  - [x] Router de administración `backend/app/api/v1/admin.py` con `BackgroundTasks` para invocar todos los jobs vía API HTTP (`HTTP 202 Accepted`) con soporte completo de parámetros.
  - [x] Migración Alembic `0002_technical_adjustments.py`.
  - [x] Suite de tests ampliada a 32 tests (100% pasando en verde).

- [x] **Fase 5: Endpoints de Catálogo, Biblioteca y Reseñas (v0.5.0 - v0.5.1)**
  - [x] Esquemas Pydantic v2 en `backend/app/schemas/catalog.py`.
  - [x] Servicio de catálogo `backend/app/services/catalog_service.py`.
  - [x] Endpoints `/api/v1/home`, `/api/v1/titles`, `/api/v1/titles/{id}`, `/api/v1/genres`.
  - [x] Endpoints de reseñas `/api/v1/titles/{id}/reviews` (GET y POST) con recálculo de rating unificado.
  - [x] Endpoints de usuario `/api/v1/users/me/library` y `/api/v1/users/me/stats`.
  - [x] Suite de tests unitarios e integración en `backend/tests/test_catalog.py` (40 tests totales pasando en verde).
  - [x] Migración de `anio_estreno` y `anio_fin` a `fecha_estreno` y `fecha_fin` (`Date`) con Alembic `0003_dates_and_home_specs.py` (v0.5.1).
  - [x] Refactorización de secciones Home (`/api/v1/home`): New Releases (60d), Trending (90d con fecha de última temporada en series), Classics (películas >20a, rating $\ge 7.5$, votos $\ge 500$, pool 50 aleatorio), Top Rated (pool 100 aleatorio), By Genre ($\ge 10$ títulos) y Others ($< 10$ títulos).
  - [x] Exclusión automática de títulos vistos (`vista`) para usuarios autenticados en Home.
  - [x] Optimización de tests (mock de BackgroundTasks en `test_admin.py`, suite de 42 tests en < 5s).
  - [x] Vaciado de catálogo administrativo `DELETE /api/v1/admin/catalog` y CLI `--clear` (v0.5.2).
  - [x] Restricción de unicidad compuesta `UNIQUE (tmdb_id, tipo)` y migración Alembic `0004_composite_tmdb_id_tipo.py` para permitir colisiones de IDs TMDB entre películas y series (v0.5.3).
  - [x] Suite de tests ampliada a 45 tests (100% pasando en verde en < 5s).

---

## Próximos Hitos: Frontend UI (Fase 5)
- [ ] **Hito 5.2:** Setup de Tailwind CSS en Vite, routing (`react-router-dom`), iconografía (`lucide-react`) y `AuthContext`.
- [ ] **Hito 5.3:** Pantalla 1 — Home (Header, Carruseles por categoría/género, Panel de IA, Drawer de accesos de usuario).
- [ ] **Hito 5.4:** Pantalla 2 — Detalle de Título (Películas y Series según wireframe).
- [ ] **Hito 5.5:** Pantalla 3 — Perfil de Usuario y Estadísticas.
- [ ] **Hito 5.6:** Pantallas complementarias (Favoritos, Watchlist, Following, History, Reviews, Settings, "Ver más").
- [ ] **Fase 6:** Recomendador Inteligente por IA.
