# CineTrack 🎬

Aplicación web de seguimiento de cine y series estilo "TV Time" con arquitectura de 3 capas (Presentación, Lógica y Persistencia) y recomendaciones asistidas por IA.

---

## 1. Requisitos Previos

- **Python:** 3.12+ (testeado con Python 3.14)
- **Node.js:** 20+ LTS (testeado con Node.js 24 LTS)
- **Base de Datos:** PostgreSQL 15+ o SQLite 3 (soporte dual para desarrollo y producción)

---

## 2. Variables de Entorno

Copiar `.env.example` a `.env` y configurar las claves necesarias:

```bash
cp .env.example .env
```

Variables clave requeridas:
- `DATABASE_URL`: Cadena de conexión (ej. `postgresql+asyncpg://usuario:password@localhost:5432/cinetrack` o `sqlite+aiosqlite:///cinetrack.db`)
- `AUTH_SECRET_KEY`: Clave secreta para firma de sesiones/tokens JWT del login
- `ADMIN_API_KEY`: Clave secreta para endpoints y tareas administrativas automatizadas
- `TMDB_API_KEY`: Read Access Token o API Key de The Movie Database (TMDB)
- `AI_PROVIDER_API_KEY`: API Key para el servicio de IA del recomendador (Google Gemini o Groq)
- `HOME_*`: Parámetros de ajuste de ventanas temporales, pools y umbrales de Home (`HOME_NEW_RELEASES_DAYS=30`, `HOME_TRENDING_DAYS=90`, `HOME_TRENDING_MIN_POPULARITY_PERCENTILE=0.80`, etc.)

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

# Vaciar completamente el catálogo (títulos, temporadas, episodios, reseñas y relaciones)
python -m app.jobs.sync_tmdb --clear
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
- `DELETE /api/v1/admin/catalog?confirm=true`: Vaciado total del catálogo y entidades dependientes (preserva usuarios y géneros).

*Autenticación requerida:* Enviar cabecera `Authorization: Bearer <token_admin>` (usuario con `es_admin=True`) o cabecera `X-Admin-Key: <ADMIN_API_KEY>`.

#### Endpoints Principales de la Aplicación (API HTTP)
- **Autenticación:**
  - `POST /api/v1/auth/register`: Registro de usuario.
  - `POST /api/v1/auth/login`: Login y obtención de JWT Bearer Token.
  - `GET /api/v1/auth/me`: Perfil del usuario autenticado.
- **Catálogo y Exploración:**
  - `GET /api/v1/home`: Secciones curadas (New Releases, Trending, Classics, Top Rated, By Genre, Others) con exclusión automática de títulos vistos para usuarios logueados. Soporta filtro `?tipo=movie|tv`.
  - `GET /api/v1/titles`: Listado paginado con filtros (`tipo`, `genero_id`, `q`, `sort_by`: popularity, rating, newest, classics).
  - `GET /api/v1/titles/{id}`: Detalle completo de película o serie (elenco jerarquizado, temporadas y episodios con estado `visto`).
  - `GET /api/v1/genres`: Listado maestro de géneros.
- **Reseñas de Usuarios:**
  - `GET /api/v1/titles/{id}/reviews`: Reseñas paginadas del título (TMDB y usuarios locales).
  - `POST /api/v1/titles/{id}/reviews`: Publicar/editar reseña propia con puntaje (recalcula automáticamente el `rating_unificado`).
- **Biblioteca y Seguimiento (Estados de Título):**
  - `POST /api/v1/titles/{id}/favorite`: Marcar / desmarcar favorito.
  - `POST /api/v1/titles/{id}/watchlist`: Agregar / quitar de watchlist.
  - `POST /api/v1/titles/{id}/watched`: Marcar película como vista (o desmarcar).
  - `POST /api/v1/titles/{id}/seasons/{season}/episodes/{episode}/watch`: Marcar / desmarcar episodio visto (transición a `siguiendo` o `vista`).
  - `POST /api/v1/titles/{id}/seasons/{season}/watch`: Marcar / desmarcar temporada completa en lote.
- **Perfil y Métricas del Usuario:**
  - `GET /api/v1/users/me/library`: Biblioteca del usuario dividida en `following`, `favorites`, `watchlist` y `recently_watched`.
  - `GET /api/v1/users/me/stats`: Estadísticas de tiempo invertido (horas en cine vs TV), conteos y Top 5 (popularidad, rating comunitario y calificaciones propias).


#### Tareas Programadas en Producción (Cron)
Para mantener actualizado el catálogo automáticamente en un servidor o contenedor, se programa la ejecución diaria del comando `--daily` mediante cron (o invocando el endpoint `/daily` con curl y la API Key):
```bash
# Ejemplo CLI: ejecutar todos los días a las 03:00 AM
0 3 * * * cd /app/backend && /app/backend/.venv/bin/python -m app.jobs.sync_tmdb --daily >> /var/log/cinetrack_sync.log 2>&1

# Ejemplo HTTP: invocar endpoint administrativo con curl
0 3 * * * curl -X POST http://localhost:8000/api/v1/admin/sync/daily -H "X-Admin-Key: cinetrack-dev-admin-secret-key" -H "Content-Type: application/json" -d "{}"
```

### Frontend (SPA React 19 + TypeScript + Vite 8 + Tailwind CSS v4)
```powershell
cd frontend
npm install

# Ejecutar suite de pruebas unitarias
npm test

# Iniciar servidor de desarrollo en http://localhost:5173
npm run dev

# Compilar para producción (carpeta dist/)
npm run build
```

#### Variables de Entorno del Frontend
En `frontend/.env` (o `.env.local`):
```env
VITE_API_URL=http://localhost:8000/api/v1
```

#### Pantallas Principales de la Aplicación
- `/`: **Home** con Hero banner, botón de recomendador IA y carruseles con snap-scroll para móvil y desktop.
- `/catalog`: **Catálogo completo** con filtros multidimensionales (sección, género, actor, tipo, ordenamiento y paginación).
- `/titles/:id`: **Ficha de Título** con backdrop, sinopsis, reparto con fotos, seguimiento de temporadas/episodios y reseñas.
- `/library`: **Mi Biblioteca** con pestañas de Favoritos, Watchlist, Siguiendo y Vistas.
- `/profile`: **Perfil de Usuario** con desglose de estadísticas de tiempo invertido (horas/días) y colecciones.
- `/recommendations`: **Recomendador Inteligente** por estado de ánimo y preferencias guiadas (previsualización Fase 6).
- **PWA Instalable:** Acceso directo como app nativa en teléfonos móviles gracias al soporte de `manifest.json`.

---

## 4. Estructura del Proyecto

Consultar [ARCHITECTURE.md](ARCHITECTURE.md) para el detalle del diseño técnico, [TASK_PLAN.md](TASK_PLAN.md) para el estado del desarrollo, y [ROADMAP.md](ROADMAP.md) para los hitos planificados.
