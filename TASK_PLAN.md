# TASK_PLAN.md — Plan de Trabajo Activo: CineTrack

## Hito Actual: Fase 2 — Persistencia y Modelos Relacionales (Completada)

- [x] **Fase 1:** Scaffolding inicial y smoke tests en verde (v0.1.0).
- [x] **Fase 2: Persistencia y Modelo Relacional (v0.2.0):**
  - [x] **Paso 2.1:** Actualizar `backend/requirements.txt` con SQLAlchemy, Alembic, asyncpg, greenlet, aiosqlite e instalar dependencias.
  - [x] **Paso 2.2:** Consultar a `qwen2.5-coder:7b` vía MCP para estructura de modelos declarativos SQLAlchemy 2.0.
  - [x] **Paso 2.3:** Crear `backend/app/db/base.py` y `backend/app/db/session.py`.
  - [x] **Paso 2.4:** Crear modelos en `backend/app/models/` (`usuario.py`, `titulo.py`, `genero.py`, `actor.py`, `temporada.py`, `episodio.py`, `estado.py`, `episodio_visto.py`, `resena.py`, `__init__.py`).
  - [x] **Paso 2.5:** Inicializar y configurar Alembic para migraciones asíncronas (`alembic.ini`, `env.py`).
  - [x] **Paso 2.6:** Generar migración inicial `0001_initial_schema.py`.
  - [x] **Paso 2.7:** Implementar suite de pruebas de modelos en `backend/tests/test_models.py` y verificar ejecución en verde con `pytest` (7/7 tests passed).
  - [x] **Paso 2.8:** Actualizar documentación viva (`CHANGELOG.md`, `ROADMAP.md`), commit y push a GitHub.

---

## Próximas Fases (No iniciar sin aprobación previa del usuario)
- **Fase 3:** Endpoints núcleo de autenticación y transiciones de estados de título (con tests unitarios exhaustivos).
- **Fase 4:** Clientes y servicios de integración con TMDB (con mocks para testing).
- **Fase 5:** Frontend UI conectada a los endpoints reales (Home, Detalle, Perfil).
- **Fase 6:** Recomendador inteligente por IA.
