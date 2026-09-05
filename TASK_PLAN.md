# TASK_PLAN.md — Plan de Trabajo Activo: CineTrack

## Estado Actual: Fase 1 (Scaffolding & Smoke Tests)

- [x] **Paso 1:** Evaluación crítica de arquitectura aprobada por el usuario.
- [x] **Paso 2:** Actualización de `ARCHITECTURE.md` con las decisiones acordadas.
- [x] **Paso 3:** Verificación de entorno de ejecución (Python 3.14, Node.js 24 LTS, npm).
- [x] **Paso 4:** Scaffolding inicial de Backend (`backend/`):
  - Creación de estructura de directorios (`app/api`, `app/core`, `app/db`, `app/models`, `app/schemas`, `app/services`).
  - Creación de `backend/requirements.txt` y configuración de entorno virtual `backend/.venv`.
  - Creación de `backend/app/main.py` con endpoint `GET /health`.
  - Configuración de suite de pruebas con `pytest` y `pytest-asyncio`.
  - Creación de `backend/tests/test_smoke.py`.
  - Verificación del smoke test de backend en verde.
- [x] **Paso 5:** Scaffolding inicial de Frontend (`frontend/`):
  - Creación del proyecto Vite + React + TypeScript.
  - Configuración de suite de pruebas con `vitest` + `@testing-library/react`.
  - Creación de smoke test `frontend/src/App.test.tsx`.
  - Verificación del smoke test de frontend en verde.
- [x] **Paso 6:** Documentación viva inicial (`README.md`, `ROADMAP.md`, `CHANGELOG.md`).
- [x] **Paso 7:** Commit de cierre del hito de scaffolding (v0.1.0).

---

## Próximas Fases (No iniciar sin aprobación previa del usuario)
- **Fase 2:** Modelo de datos en SQLAlchemy y migraciones Alembic.
- **Fase 3:** Endpoints núcleo de autenticación y transiciones de estados de título (con tests unitarios exhaustivos).
- **Fase 4:** Clientes y servicios de integración con TMDB (con mocks para testing).
- **Fase 5:** Frontend UI conectada a los endpoints reales (Home, Detalle, Perfil).
- **Fase 6:** Recomendador inteligente por IA.
