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
pytest
uvicorn app.main:app --reload --port 8000
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

#### Tareas Programadas en Producción (Cron)
Para mantener actualizado el catálogo automáticamente en un servidor o contenedor, se programa la ejecución diaria del comando `--daily` mediante cron:
```bash
# Ejemplo: ejecutar todos los días a las 03:00 AM
0 3 * * * cd /app/backend && /app/backend/.venv/bin/python -m app.jobs.sync_tmdb --daily >> /var/log/cinetrack_sync.log 2>&1
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
