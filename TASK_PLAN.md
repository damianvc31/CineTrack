# TASK_PLAN.md — Plan de Trabajo Activo: CineTrack

## Hito Actual: Fase 3 — Autenticación y Motor de Estados de Título (Completada)

- [x] **Fase 1:** Scaffolding inicial y smoke tests en verde (v0.1.0).
- [x] **Fase 2:** Persistencia y modelos relacionales completos en SQLAlchemy 2.0 (v0.2.0).
- [x] **Fase 3: Autenticación y Motor de Estados de Título (v0.3.0):**
  - [x] **Paso 3.1:** Actualizar `backend/requirements.txt` con `bcrypt>=4.1.0` y `pyjwt>=2.8.0` e instalar dependencias.
  - [x] **Paso 3.2:** Crear `backend/app/core/security.py` con funciones de hashing (`bcrypt`) y tokens JWT usando estrictamente `AUTH_SECRET_KEY`.
  - [x] **Paso 3.3:** Crear esquemas Pydantic v2 en `backend/app/schemas/auth.py` y `backend/app/schemas/state.py`.
  - [x] **Paso 3.4:** Implementar servicio de autenticación `backend/app/services/auth_service.py`, dependencia `get_current_user` y endpoints en `backend/app/api/v1/auth.py`.
  - [x] **Paso 3.5:** Consultar a `qwen2.5-coder:7b` vía MCP para refinar la implementación transaccional del servicio de estados.
  - [x] **Paso 3.6:** Implementar `backend/app/services/state_service.py` con el motor completo de transiciones (películas y series, marcas temporales y reseteo de fechas).
  - [x] **Paso 3.7:** Implementar router `backend/app/api/v1/states.py` y unificar los endpoints en `backend/app/api/v1/api.py`.
  - [x] **Paso 3.8:** Implementar suite de pruebas exhaustivas en `backend/tests/test_auth.py` y `backend/tests/test_state_machine.py`.
  - [x] **Paso 3.9:** Ejecutar `pytest` y verificar que la suite completa pase en verde (16/16 tests passed).
  - [x] **Paso 3.10:** Actualizar documentación viva (`CHANGELOG.md`, `ROADMAP.md`), commit, tag `v0.3.0` y push a GitHub.

---

## Próximas Fases (No iniciar sin aprobación previa del usuario)
- **Fase 4:** Clientes y servicios de integración con TMDB (con mocks para testing).
- **Fase 5:** Frontend UI conectada a los endpoints reales (Home, Detalle, Perfil).
- **Fase 6:** Recomendador inteligente por IA.
