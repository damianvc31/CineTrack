# CineTrack 🎬

Aplicación web de seguimiento de cine y series estilo "TV Time" con arquitectura de 3 capas (Presentación, Lógica y Persistencia) y recomendaciones asistidas por IA.

---

## 1. Requisitos Previos

- **Python:** 3.12+ (testeado con Python 3.14)
- **Node.js:** 20+ LTS (testeado con Node.js 24 LTS)
- **Base de Datos:** PostgreSQL 15+

---

## 2. Variables de Entorno

Copiar `.env.example` a `.env` y configurar las claves necesarias:

```bash
cp .env.example .env
```

Variables clave requeridas:
- `DATABASE_URL`: Cadena de conexión PostgreSQL (ej. `postgresql+asyncpg://usuario:password@localhost:5432/cinetrack`)
- `AUTH_SECRET_KEY`: Clave secreta para firma de sesiones/tokens del login
- `TMDB_API_KEY`: Read Access Token o API Key de The Movie Database (TMDB)
- `AI_PROVIDER_API_KEY`: API Key para el servicio de IA del recomendador (Google Gemini o Groq)

---

## 3. Instalación y Ejecución

### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Aplicar migraciones de Base de Datos (Alembic)
alembic upgrade head

# Correr tests
pytest

# Iniciar servidor de desarrollo
uvicorn app.main:app --reload --port 8000
```

#### Comandos de Migraciones (Alembic)
```powershell
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Ver la revisión/migración actual de la base de datos
alembic current

# Ver el historial de migraciones
alembic history --verbose

# Generar una nueva migración automáticamente tras modificar modelos
alembic revision --autogenerate -m "descripcion_del_cambio"

# Revertir la última migración aplicada (rollback de 1 paso)
alembic downgrade -1
```

#### Comandos de Ingesta y Sincronización TMDB
```powershell
# Sincronizar catálogo de géneros
python -m app.jobs.sync_tmdb --genres

# Ingesta inicial de catálogo (opciones: --priority popular_first | toprated_first)
python -m app.jobs.sync_tmdb --initial --priority popular_first

# Sincronización diaria (series en seguimiento + nuevos estrenos)
python -m app.jobs.sync_tmdb --daily

# Recalcular percentiles de popularidad
python -m app.jobs.sync_tmdb --percentiles

# Sincronizar reseñas de TMDB para todos los títulos hasta el tope (20)
python -m app.jobs.sync_tmdb --reviews

# Carga manual mediante archivo JSON (ver docs/templates/ para formato)
python -m app.jobs.sync_tmdb --import-json docs/templates/template_pelicula.json

# Importar título individual por ID de TMDB
python -m app.jobs.sync_tmdb --import-tmdb-id 157336 --type movie
```

#### Calificación Unificada y Política de Reseñas
CineTrack no divide de forma confusa el puntaje entre "TMDB" y "CineTrack", sino que presenta un **puntaje promedio ponderado unificado**:

$$\text{Rating} = \frac{(\text{vote\_average\_tmdb} \times \text{vote\_count\_tmdb}) + \sum_{i=1}^{N} \text{puntaje\_usuario}_i}{\text{vote\_count\_tmdb} + N}$$

- **Reseñas de TMDB:** Se sincronizan hasta un tope configurable (`TMDB_REVIEWS_PER_TITLE_LIMIT = 20`) exclusivamente para dar contexto enriquecido y opiniones al catálogo inicial. No alteran el cálculo ponderado porque los votos de TMDB ya están reflejados en `vote_average_tmdb`.
- **Reseñas de CineTrack:** No tienen límite por título y cada reseña con puntaje emitida por un usuario registrado impacta dinámicamente en el rating consolidado.

#### Endpoints Administrativos (API HTTP)
Todos los jobs de sincronización pueden dispararse también vía HTTP (`HTTP 202 Accepted` con ejecución asíncrona mediante `BackgroundTasks`):
- `POST /api/v1/admin/sync/genres`: Sincronización de géneros.
- `POST /api/v1/admin/sync/initial`: Ingesta inicial (`priority`, `movies_target`, `series_target`).
- `POST /api/v1/admin/sync/daily`: Sync diaria (`hours_window`).
- `POST /api/v1/admin/sync/percentiles`: Recálculo de percentiles y rating unificado.
- `POST /api/v1/admin/sync/reviews`: Sincronización de reseñas TMDB (`limit_per_title`).
- `POST /api/v1/admin/sync/import-tmdb`: Importar título por TMDB ID (`tmdb_id`, `type`).
- `POST /api/v1/admin/sync/import-json`: Carga masiva desde lista JSON según plantillas.

*Autenticación requerida:* Enviar cabecera `Authorization: Bearer <token_admin>` (usuario con `es_admin=True`) o cabecera `X-Admin-Key: <ADMIN_API_KEY>`.

#### Tareas Programadas en Producción (Cron)
Para mantener actualizado el catálogo automáticamente en un servidor o contenedor, se programa la ejecución diaria del comando `--daily` mediante cron (o invocando el endpoint `/daily` con curl y la API Key):
```bash
# Ejemplo CLI: ejecutar todos los días a las 03:00 AM
0 3 * * * cd /app/backend && /app/backend/.venv/bin/python -m app.jobs.sync_tmdb --daily >> /var/log/cinetrack_sync.log 2>&1

# Ejemplo HTTP: invocar endpoint administrativo con curl
0 3 * * * curl -X POST http://localhost:8000/api/v1/admin/sync/daily -H "X-Admin-Key: cinetrack-dev-admin-secret-key" -H "Content-Type: application/json" -d "{}"
```

### Frontend
```powershell
cd frontend
npm install
npm test
npm run dev
```

---

## 4. Estructura del Proyecto

Consultar [ARCHITECTURE.md](ARCHITECTURE.md) para el detalle del diseño técnico, [TASK_PLAN.md](TASK_PLAN.md) para el estado del desarrollo, y [ROADMAP.md](ROADMAP.md) para los hitos planificados.
