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
- **Proveedor de IA para el recomendador (Arquitectura Híbrida Resiliente):**
  - `GEMINI_API_KEY`: Clave de API de Google AI Studio para Gemini.
  - `GEMINI_MODEL`: Identificador del modelo Gemini (default: `gemini-3.6-flash`).
  - `GROQ_API_KEY`: Clave de API de Groq Cloud para modelos de alta velocidad.
  - `GROQ_MODEL`: Identificador del modelo Groq (default: `openai/gpt-oss-120b`).
  - `AI_RECOMMENDER_PRIMARY`: Proveedor primario de IA (`gemini` o `groq`, con fallback cruzado automático y degradación elegante al motor heurístico determinista local).
- **Expansión de Catálogo TMDB (Criterio 1: /discover por géneros con filtros de calidad):**
  - `TMDB_EXPAND_MIN_VOTE_COUNT`: Umbral mínimo de votos en TMDB (default: `300`).
  - `TMDB_EXPAND_MIN_VOTE_AVERAGE`: Umbral mínimo de calificación en TMDB (default: `7.0`).
  - `TMDB_EXPAND_TITLES_PER_GENRE`: Títulos objetivo a ingerir por género (default: `50`).
- `HOME_*`: Parámetros de ajuste de ventanas temporales, pools y umbrales de Home (`HOME_NEW_RELEASES_DAYS=30`, `HOME_TRENDING_DAYS=90`, `HOME_TRENDING_MIN_POPULARITY_PERCENTILE=0.80`, etc.)
- `CACHE_*`: Parámetros de caché en memoria TTL (`CACHE_HOME_TTL_SECONDS=3600`, `CACHE_CATALOG_TTL_SECONDS=300`)

### Gestión de Ambientes en Desarrollo (`.env` vs `.env.local`)
El proyecto admite alternar fluidamente entre dos bases de datos para desarrollo local:
- **`.env` (Neon PostgreSQL / Dev Branch):** Configuración base con soporte para `pgvector` y búsqueda vectorial semántica. Es el entorno activo por defecto.
- **`.env.local` (SQLite Local):** Configuración liviana y veloz (`sqlite+aiosqlite:///cinetrack.db`), ideal para iteración rápida de interfaz o pruebas que no requieren el recomendador vectorial.

---

## 3. Instalación y Ejecución

### Ejecución Directa desde la Raíz (`CineTrack/`)
Puedes arrancar ambos servicios sin cambiar de directorio:

```powershell
# Backend con Neon PostgreSQL (.env por defecto)
uvicorn app.main:app --reload --app-dir backend

# Backend con SQLite Local (.env.local)
uvicorn app.main:app --reload --app-dir backend --env-file .env.local

# Frontend (Vite)
npm --prefix frontend run dev
```

### Ejecución Tradicional por Carpetas

#### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Aplicar migraciones de Base de Datos (Alembic)
alembic upgrade head

# Correr tests
pytest

# Iniciar servidor con Neon PostgreSQL (.env)
uvicorn app.main:app --reload --port 8000

# Iniciar servidor alternativo con SQLite (.env.local en raíz)
uvicorn app.main:app --reload --port 8000 --env-file ../.env.local
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

#### Comandos de Ingesta y Sincronización TMDB (CLI)
Todos los comandos se ejecutan desde el entorno virtual del backend mediante el módulo `app.jobs.sync_tmdb`:

```powershell
# 1. Sincronizar catálogo de géneros desde TMDB
python -m app.jobs.sync_tmdb --genres

# 2. Ingesta inicial de catálogo
#    --priority: 'popular_first' o 'toprated_first'
#    --movies-target: cantidad de películas a ingerir
#    --series-target: cantidad de series a ingerir
#    --allow-unreleased: permitir obras no estrenadas (default: False)
python -m app.jobs.sync_tmdb --initial --priority popular_first --movies-target 1000 --series-target 1000

# 3. Sincronización diaria estándar (cambios en catálogo y cartelera)
#    --changes-hours: ventana en horas para /changes de TMDB (default config: 48 hs, ej. 120 para 5 días)
#    --releases-days: ventana en días para nuevos estrenos en cartelera (default config: 15 días)
#    --allow-unreleased: permitir títulos no estrenados (default: False)
python -m app.jobs.sync_tmdb --daily --changes-hours 120 --releases-days 15

# 4. Expansión de catálogo por géneros (Criterio 1: /discover con filtros de calidad)
#    --genre: nombre o ID de TMDB (ej. "Ciencia ficción", "Crime", 80). Si se omite, procesa todos los géneros
#    --media-type: 'both' (default), 'movie' o 'tv'
#    --min-vote-count: umbral mínimo de votos en TMDB (default config: 300)
#    --min-vote-average: calificación promedio mínima en TMDB (default config: 7.0)
#    --target-per-genre: cantidad objetivo de títulos por género (default config: 50)
#    --allow-unreleased: permitir títulos no estrenados (default: False; por defecto filtra solo estrenados)
#
# Ejemplos:
# Para todos los géneros con configuración por defecto:
python -m app.jobs.sync_tmdb --expand
# Para un género puntual (por nombre) solo películas:
python -m app.jobs.sync_tmdb --expand --genre "Crime" --media-type movie --target-per-genre 15
# Para un género por ID con umbrales personalizados:
python -m app.jobs.sync_tmdb --expand --genre 878 --min-vote-count 250 --min-vote-average 7.2 --target-per-genre 30

# 5. Saneamiento de títulos no estrenados (elimina películas futuras y series sin temporadas emitidas)
python -m app.jobs.sync_tmdb --cleanup-unreleased

# 6. Recalcular percentiles de popularidad y ratings unificados
python -m app.jobs.sync_tmdb --percentiles

# 7. Sincronizar reseñas externas de TMDB para todos los títulos (hasta el tope configurable de 20)
python -m app.jobs.sync_tmdb --reviews

# 8. Carga manual mediante archivo JSON estructurado (ver docs/templates/ para formato)
python -m app.jobs.sync_tmdb --import-json docs/templates/template_pelicula.json

# 9. Importar título individual por ID de TMDB
python -m app.jobs.sync_tmdb --import-tmdb-id 157336 --type movie

# 10. Vaciar completamente el catálogo (títulos, temporadas, episodios, reseñas y relaciones; preserva usuarios)
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
Todos los jobs de sincronización pueden dispararse también vía HTTP (`HTTP 202 Accepted` con ejecución asíncrona en segundo plano mediante `BackgroundTasks`).

*Autenticación requerida:* Enviar cabecera `Authorization: Bearer <token_admin>` (usuario con `es_admin=True`) o cabecera `X-Admin-Key: <ADMIN_API_KEY>`.

- **`POST /api/v1/admin/sync/expand`** (Expansión selectiva por géneros — Criterio 1):
  ```json
  {
    "genre": "Crime",
    "media_type": "movie",
    "min_vote_count": 300,
    "min_vote_average": 7.0,
    "target_per_genre": 15,
    "allow_unreleased": false
  }
  ```
  - `genre` (*string | null*, opcional): Nombre o ID del género. Si es `null` o se omite, procesa todos los géneros.
  - `media_type` (*string*, opcional): `"both"` (default), `"movie"` o `"tv"`.
  - `min_vote_count` (*integer*, opcional): Umbral mínimo de votos en TMDB (default: valor de `TMDB_EXPAND_MIN_VOTE_COUNT`).
  - `min_vote_average` (*float*, opcional): Calificación promedio mínima (default: valor de `TMDB_EXPAND_MIN_VOTE_AVERAGE`).
  - `target_per_genre` (*integer*, opcional): Cantidad objetivo de títulos por género (default: valor de `TMDB_EXPAND_TITLES_PER_GENRE`).
  - `allow_unreleased` (*boolean*, opcional): Permitir obras no estrenadas (default: `false`).

- **`POST /api/v1/admin/sync/initial`** (Ingesta inicial masiva):
  - Body: `{"priority": "popular_first" | "toprated_first", "movies_target": 1000, "series_target": 1000, "allow_unreleased": false}`

- **`POST /api/v1/admin/sync/daily`** (Sincronización diaria periódica):
  - Body: `{"changes_hours_window": 48, "releases_days_window": 15, "allow_unreleased": false}`

- **`POST /api/v1/admin/sync/genres`** (Sincronización del catálogo de géneros):
  - Dispara la actualización de géneros desde TMDB en background.

- **`POST /api/v1/admin/sync/cleanup-unreleased`** (Saneamiento de catálogo):
  - Ejecuta de forma síncrona la eliminación de títulos no estrenados y recalcula métricas.

- **`POST /api/v1/admin/sync/percentiles`** (Recálculo de popularidad y ratings):
  - Recalcula percentiles y ratings unificados en background.

- **`POST /api/v1/admin/sync/reviews`** (Sincronización masiva de reseñas):
  - Body: `{"limit_per_title": 20}`

- **`POST /api/v1/admin/sync/import-tmdb`** (Importación puntual por ID TMDB):
  - Body: `{"tmdb_id": 157336, "type": "movie"}`

- **`POST /api/v1/admin/sync/import-json`** (Ingesta por lista JSON estructurada):
  - Body: arreglo de objetos según plantillas de `docs/templates/`.

- **`DELETE /api/v1/admin/catalog?confirm=true`** (Vaciado de catálogo):
  - Elimina títulos y datos asociados, preservando usuarios y géneros. Requiere `confirm=true`.

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
- **Recomendador Asistido por IA (Motor Híbrido Resiliente):**
  - `POST /api/v1/recommendations`: Búsqueda y recomendación inteligente con grounding estricto sobre el catálogo local. Procesa prompts libres en lenguaje natural con soporte para usuarios invitados y autenticados (personalizado según historial de vistos y favoritos), cascada de reintentos resiliente (Gemini -> Groq -> Heurístico local) y explicación contextual (`why_recommended`).

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
- `/`: **Home** con Hero banner dinámico, disparador del Asistente IA en la columna izquierda y carruseles curados con snap-scroll.
- `/catalog`: **Catálogo completo** con filtros multidimensionales (sección, género, actor, tipo de obra, ordenamiento y paginación).
- `/titles/:id`: **Ficha de Título** con backdrop cinematográfico, sinopsis, reparto con fotos de actores, seguimiento interactivo de temporadas/episodios y motor integral de reseñas (edición/eliminación in-place, puntaje 0.5 opcional).
- `/reviews`: **Reseñas y Opiniones** con pestañas "My Reviews" (gestión centralizada de reseñas propias) y "Pending Reviews" (títulos vistos sin reseñar con redactor rápido in-place).
- `/library`: **Mi Biblioteca** con pestañas de Favoritos, Watchlist, Siguiendo y Vistas (actualización silenciosa en background sin layout shifts).
- `/profile`: **Perfil de Usuario** con desglose de estadísticas de tiempo invertido (horas/semanas en cine vs TV), Top 5 personalizable y gráfico interactivo Donut SVG de distribución de géneros.
- `/recommendations`: **Asistente IA de Recomendaciones (RAG Híbrido)** con búsqueda semántica vectorial de 768 dimensiones con `pgvector` e índice HNSW, filtrado relacional con exclusiones negativas estrictas (*"sin animación"*), jerarquización de actores y directores con fuzzy matching difuso vía `pg_trgm` (*"brad pit"*), reconocimiento dual-track de procedencia (país de producción estricto vs. ambientación/locación e idioma original), y cascada multi-modelo resiliente entre Google Gemini y Groq API con degradación elegante a motor heurístico determinista local.
- `/settings`: **Configuración de Usuario** con cambio seguro de contraseña y selector de idioma reactivo para la interfaz (Español / English).
- **PWA Instalable:** Acceso directo como aplicación nativa en dispositivos móviles y de escritorio gracias al soporte de `manifest.json` y Web App Manifest.

---

---

## 5. Despliegue en Producción (Cloud PaaS: Render + Vercel + Neon + GitHub Actions)

CineTrack está preparado para desplegarse en una infraestructura serverless/PaaS desacoplada, de alta disponibilidad y sin costo:

```mermaid
flowchart TD
    User["👤 Usuario Final (Navegador / Móvil PWA)"] -->|HTTPS| Vercel["⚡ Vercel (Frontend React SPA)"]
    Vercel -->|REST API / HTTPS| Render["🚀 Render.com (Backend FastAPI)"]
    Cron["⏱️ GitHub Actions (Cron 03:00 UTC)"] -->|POST /api/v1/admin/sync/daily| Render
    Render -->|asyncpg / SSL / pooler| Neon["🐘 Neon.tech (PostgreSQL Serverless)"]
    Render -->|HTTP Requests| TMDB["🎬 TMDB API"]
    Render -->|SDK / REST| AI["🤖 Google Gemini / Groq API"]
```

### Paso 1: Base de Datos en Neon.tech (PostgreSQL Serverless)
1. Crear una cuenta gratuita en [Neon.tech](https://neon.tech) y crear un proyecto nuevo (ej. `cinetrack-db`).
2. Copiar la cadena de conexión `DATABASE_URL` (formato `postgresql://usuario:password@ep-xyz.us-east-2.aws.neon.tech/cinetrack?sslmode=require`).
3. **Migrar el catálogo local enriquecido** hacia Neon sin consumir cuota de TMDB ejecutando el script masivo:
   ```powershell
   cd backend
   python -m app.jobs.export_to_postgres --target-url "postgresql://usuario:password@ep-xyz.us-east-2.aws.neon.tech/cinetrack?sslmode=require"
   ```
   *El script creará automáticamente las 12 tablas, normalizará tipos, sincronizará la revisión de Alembic, transferirá los datos en bloques y actualizará las secuencias PostgreSQL.*

### Paso 2: Backend en Render.com (Web Service)
1. Crear una cuenta en [Render.com](https://render.com) y conectar el repositorio de GitHub.
2. Crear un **New Web Service**:
   - **Root Directory:** `backend`
   - **Runtime:** `Python` (detectará automáticamente `backend/.python-version` con Python 3.12)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
3. En la pestaña **Environment Variables** de Render, definir:
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: tu URL de Neon (con `?sslmode=require`)
   - `AUTH_SECRET_KEY`: clave secreta de 32+ caracteres para firmar JWT
   - `ADMIN_API_KEY`: clave secreta para operaciones administrativas
   - `BACKEND_CORS_ORIGINS`: URL de Vercel (ej. `https://cinetrack.vercel.app,http://localhost:5173`)
   - `TMDB_API_KEY`: tu Read Access Token de TMDB
   - `GEMINI_API_KEY`: tu API Key de Google AI Studio
   - `GROQ_API_KEY`: tu API Key de Groq Cloud
4. Desplegar el servicio y copiar la URL pública asignada (ej. `https://cinetrack-api.onrender.com`).
   *Verificar salud en `https://cinetrack-api.onrender.com/health` $\rightarrow$ `{"status": "ok", "version": "1.0.0"}`.*

### Paso 3: Frontend en Vercel (SPA React 19)
1. Crear una cuenta en [Vercel](https://vercel.com) e importar el repositorio.
2. En la configuración del proyecto:
   - **Root Directory:** `frontend`
   - **Framework Preset:** `Vite`
3. En **Environment Variables** de Vercel:
   - `VITE_API_URL`: URL del backend en Render (ej. `https://cinetrack-api.onrender.com/api/v1`)
4. Desplegar. El archivo `frontend/vercel.json` gestiona automáticamente los rewrites para que la navegación cliente no devuelva 404 al recargar páginas.

### Paso 4: Automatización de Sincronización Diaria (GitHub Actions)
1. En el repositorio de GitHub, ir a **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**.
2. Agregar los siguientes **Repository Secrets**:
   - `PROD_API_URL`: URL raíz de tu backend en Render (ej. `https://cinetrack-api.onrender.com`)
   - `ADMIN_API_KEY`: el mismo valor de `ADMIN_API_KEY` configurado en Render.
3. El workflow `.github/workflows/daily_sync.yml` se disparará automáticamente todos los días a las **03:00 UTC (00:00 hora de Argentina)** para actualizar el catálogo vía `/changes` de TMDB y recalcular percentiles y ratings.
4. También puede dispararse manualmente en cualquier momento desde la pestaña **Actions $\rightarrow$ CineTrack Daily TMDB Sync $\rightarrow$ Run workflow**.

---

## 6. Estructura del Proyecto

Consultar [ARCHITECTURE.md](ARCHITECTURE.md) para el detalle del diseño técnico, [TASK_PLAN.md](TASK_PLAN.md) para el estado del desarrollo, y [ROADMAP.md](ROADMAP.md) para los hitos planificados.

