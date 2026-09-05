# CHANGELOG.md — Registro de Cambios: CineTrack

Todos los cambios notables en este proyecto serán documentados en este archivo.

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
