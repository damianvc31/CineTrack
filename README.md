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

# Sincronización diaria estándar (valores por defecto: 48 hs para cambios y 15 días para cartelera)
python -m app.jobs.sync_tmdb --daily

# Sincronización diaria con parámetros personalizados:
# --changes-hours: ventana en horas para /changes en series y películas de TMDB (ej. 120 para 5 días, o 0 para omitir cambios)
# --releases-days: ventana en días para /discover de nuevos estrenos en cartelera de películas y series (ej. 15 días)
# --allow-unreleased: permitir títulos no estrenados (por defecto False; omite películas futuras y series sin temporadas emitidas)
python -m app.jobs.sync_tmdb --daily --changes-hours 120 --releases-days 15

# Saneamiento de títulos no estrenados (elimina películas futuras y series sin temporadas de la base de datos)
python -m app.jobs.sync_tmdb --cleanup-unreleased

# Recalcular percentiles de popularidad
python -m app.jobs.sync_tmdb --percentiles

# Sincronizar reseñas de TMDB para todos los títulos hasta el tope (20)
python -m app.jobs.sync_tmdb --reviews

# Carga manual mediante archivo JSON (ver docs/templates/ para formato)
python -m app.jobs.sync_tmdb --import-json docs/templates/template_pelicula.json

# Importar título individual por ID de TMDB
python -m app.jobs.sync_tmdb --import-tmdb-id 157336 --type movie

# Expansión de catálogo por géneros (Criterio 1: discover con thresholds de votos y rating)
# Para todos los géneros:
python -m app.jobs.sync_tmdb --expand
# Para un género puntual (por nombre o ID de TMDB) con parámetros personalizados:
python -m app.jobs.sync_tmdb --expand --genre "Ciencia ficción" --min-vote-count 300 --min-vote-average 7.0 --target-per-genre 50
python -m app.jobs.sync_tmdb --expand --genre 28 --media-type movie

# Vaciar completamente el catálogo (títulos, temporadas, episodios, reseñas y relaciones)
python -m app.jobs.sync_tmdb --clear
```

#### Calificación Unificada y Política de Reseñas
CineTrack no divide de forma confusa el puntaje entre "TMDB" y "CineTrack", sino que presenta un **puntaje promedio ponderado unificado**:

$$\text{Rating} = \frac{(\text{vote\_average\_tmdb} \times \text{vote\_count\_tmdb}) + \sum_{i=1}^{N} \text{puntaje\_usuario}_i}{\text{vote\_count\_tmdb} + N}$$

- **Reseñas de TMDB:** Se sincronizan hasta un tope configurable (`TMDB_REVIEWS_PER_TITLE_LIMIT = 20`) exclusivamente para dar contexto enriquecido y opiniones al catálogo inicial. No alteran el cálculo ponderado porque los votos de TMDB ya están reflejados en `vote_average_tmdb`.
- **Reseñas de CineTrack:** 
  - **1 reseña por usuario por título:** Se gestiona mediante edición (lápiz) o eliminación (tacho de basura) en lugar de crear duplicados.
  - **Saltos de 0.5 (0.0 a 10.0):** Restricción exclusiva para calificaciones emitidas en CineTrack (`0.0, 0.5, 1.0, ..., 10.0`). Los puntajes de TMDB se preservan intactos.
  - **Puntaje opcional:** Si el usuario no marca la opción de calificar, la reseña se guarda como texto de opinión y no impacta ni desvirtúa la media ponderada del `rating_unificado`.
  - **Pantalla `/reviews`:** Interfaz dedicada con pestañas "My Reviews" (gestión de reseñas propias) y "Pending Reviews" (títulos vistos sin reseñar con redactor rápido in-place).

#### Endpoints Administrativos (API HTTP)
Todos los jobs de sincronización pueden dispararse también vía HTTP (`HTTP 202 Accepted` con ejecución asíncrona mediante `BackgroundTasks`):
- `POST /api/v1/admin/sync/genres`: Sincronización de géneros.
- `POST /api/v1/admin/sync/initial`: Ingesta inicial (`priority`, `movies_target`, `series_target`, `allow_unreleased`).
- `POST /api/v1/admin/sync/daily`: Sync diaria (`changes_hours_window`, `releases_days_window`, `allow_unreleased`).
- `POST /api/v1/admin/sync/cleanup-unreleased`: Saneamiento inmediato de títulos no estrenados.
- `POST /api/v1/admin/sync/percentiles`: Recálculo de percentiles y rating unificado.
- `POST /api/v1/admin/sync/reviews`: Sincronización de reseñas de TMDB.
- `POST /api/v1/admin/sync/import-tmdb`: Importación puntual de título por ID TMDB.
- `POST /api/v1/admin/sync/import-json`: Ingesta por archivo JSON.
- `DELETE /api/v1/admin/catalog`: Vaciado total de catálogo (preservando usuarios).

*Autenticación requerida:* Enviar cabecera `Authorization: Bearer <token_admin>` (usuario con `es_admin=True`) o cabecera `X-Admin-Key: <ADMIN_API_KEY>`.

#### Endpoints Principales de la Aplicación (API HTTP)
- **Autenticación (JWT):**
  - `POST /api/v1/auth/register`: Registro de usuario.
  - `POST /api/v1/auth/login`: Login y obtención de JWT Bearer Token.
  - `GET /api/v1/auth/me`: Perfil del usuario autenticado.
- **Catálogo y Exploración:**
  - `GET /api/v1/home`: Secciones curadas (New Releases, Trending, Classics, Top Rated, By Genre, Others). Soporta filtro `?tipo=movie|tv`.
  - `GET /api/v1/titles`: Listado paginado con filtros (`section`, `tipo`, `genero`, `actor`, `q`, `sort_by`, `order`).
  - `GET /api/v1/titles/{id}`: Detalle completo de película o serie (elenco jerarquizado, temporadas y episodios con estado `visto`).
  - `GET /api/v1/genres`: Listado maestro de géneros.
- **Reseñas de Usuarios:**
  - `GET /api/v1/titles/{id}/reviews`: Reseñas públicas del título (TMDB con badge y comunidad local).
  - `POST /api/v1/titles/{id}/reviews`: Publicar/editar reseña propia con o sin puntaje (recalcula automáticamente `rating_unificado`).
  - `DELETE /api/v1/titles/{id}/reviews`: Eliminar reseña propia y recalcular `rating_unificado`.
  - `GET /api/v1/users/me/reviews`: Listado paginado de todas las reseñas del usuario.
  - `GET /api/v1/users/me/unreviewed-watched`: Títulos marcados como vistos que aún no tienen reseña del usuario.
- **Biblioteca y Seguimiento (Estados de Título):**
  - `POST /api/v1/titles/{id}/favorite`: Marcar / desmarcar favorito.
  - `POST /api/v1/titles/{id}/watchlist`: Agregar / quitar de watchlist.
  - `POST /api/v1/titles/{id}/watched`: Marcar película como vista (o desmarcar).
  - `POST /api/v1/titles/{id}/seasons/{season}/episodes/{episode}/watch`: Marcar / desmarcar episodio visto.
  - `POST /api/v1/titles/{id}/seasons/{season}/watch`: Marcar / desmarcar temporada completa en lote.
- **Perfil y Métricas del Usuario:**
  - `GET /api/v1/users/me/library`: Biblioteca del usuario dividida en `following`, `favorites`, `watchlist` y `recently_watched`.
  - `GET /api/v1/users/me/stats`: Estadísticas de tiempo invertido (horas en cine vs TV), conteos y Top 5.


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
Vite está configurado para leer directamente las variables desde el archivo `.env` en la raíz del repositorio (`envDir: '../'`), evitando duplicar archivos de configuración:
```env
VITE_API_URL=http://localhost:8000/api/v1
```

#### Pantallas Principales de la Aplicación
- `/`: **Home** con Hero banner, recomendador IA en columna izquierda y carruseles con snap-scroll.
- `/catalog`: **Catálogo completo** con filtros multidimensionales (sección, género, actor, tipo, ordenamiento y paginación).
- `/titles/:id`: **Ficha de Título** con backdrop, sinopsis, reparto con fotos, seguimiento de temporadas/episodios y motor de reseñas (edición/eliminación in-place, puntaje 0.5 opcional).
- `/reviews`: **Reseñas y Opiniones** con pestañas "My Reviews" (gestión centralizada) y "Pending Reviews" (títulos vistos sin reseñar).
- `/library`: **Mi Biblioteca** con pestañas de Favoritos, Watchlist, Siguiendo y Vistas.
- `/profile`: **Perfil de Usuario** con desglose de estadísticas de tiempo invertido (horas/días) y colecciones.
- `/recommendations`: **Recomendador Inteligente** por estado de ánimo y preferencias guiadas (previsualización Fase 6).
- **PWA Instalable:** Acceso directo como app nativa en teléfonos móviles gracias al soporte de `manifest.json`.

---

## 4. Estructura del Proyecto

Consultar [ARCHITECTURE.md](ARCHITECTURE.md) para el detalle del diseño técnico, [TASK_PLAN.md](TASK_PLAN.md) para el estado del desarrollo, y [ROADMAP.md](ROADMAP.md) para los hitos planificados.
