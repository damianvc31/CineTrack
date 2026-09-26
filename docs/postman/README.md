# CineTrack — Colección de Postman (Admin & Sync API)

Esta carpeta contiene la colección oficial de Postman y los entornos configurados en el formato nativo moderno (**YAML v10+**), listos para sincronización con Git y ejecución de todos los endpoints administrativos y jobs de sincronización TMDB.

---

## 📁 Estructura del Proyecto Postman

```text
docs/postman/
├── CineTrack - Production.environment.example.yaml        # Plantilla Entorno Producción (Render)
├── CineTrack - Local - Dev.environment.example.yaml       # Plantilla Entorno Local (localhost:8000)
├── CineTrack - Admin & Sync API/                           # Colección modular en YAML (Postman Git Workspace)
│   ├── .resources/definition.yaml                         # Autenticación automática X-Admin-Key: {{admin_key}}
│   ├── 1. Telemetría y Monitoreo/
│   ├── 2. Expansión de Catálogo (-discover)/
│   ├── 3. Calidad y Purga de Catálogo/
│   ├── 4. Sincronización Automatizada (Daily & Deep)/
│   └── 5. Ingesta Manual/
└── README.md                                              # Esta guía
```

---

## ⚙️ Entornos y Seguridad

| Entorno | Variable `base_url` | Variable `admin_key` | Propósito |
|---|---|---|---|
| **CineTrack - Production** | `https://cinetrack-api-zsen.onrender.com` | `{{admin_key}}` | Operar sobre la base de producción en Render. |
| **CineTrack - Local / Dev** | `http://localhost:8000` | `{{admin_key}}` | Pruebas locales y desarrollo. |

> [!SECURITY]
> **Gestión de Secretos:**
> Siguiendo las directivas de seguridad del proyecto, los entornos reales con claves de acceso privadas (`*.environment.yaml`) están en `.gitignore` y **nunca se suben al repositorio**.
> 
> En git se versionan únicamente las plantillas sanitizadas con sufijo `.example.yaml` (`admin_key: ""`).
> Al importar las plantillas en Postman, solo debés ingresar el valor de tu `ADMIN_API_KEY` en la columna **Current Value** de Postman. Postman almacena ese valor únicamente en la memoria de tu sesión local.

---

## 🚀 Endpoints y Ejemplos de Uso

### 1. Ingesta Manual (`POST /api/v1/admin/sync/import-tmdb`)

Permite traer obras puntuales o paquetes específicos desde TMDB sin esperar a un ciclo programado.

#### A. Importar un título puntual (Película o Serie):
```json
{
  "tmdb_id": 157336,
  "type": "movie",
  "allow_unreleased": true
}
```

#### B. Ingesta masiva en lote (Múltiples títulos en un solo request):
Ideal para cargar listas curadas de IDs de TMDB (tanto películas como series combinadas):
```json
{
  "items": [
    { "tmdb_id": 157336, "type": "movie" },
    { "tmdb_id": 27205, "type": "movie" },
    { "tmdb_id": 1399, "type": "tv" },
    { "tmdb_id": 94605, "type": "tv" }
  ],
  "allow_unreleased": true
}
```

---

### 2. Expansión de Catálogo (`POST /api/v1/admin/sync/expand`)

Utiliza el motor de descubrimiento `/discover` de TMDB con filtros de calidad y actualiza automáticamente los embeddings de los títulos estrenados.

#### A. Expansión Estándar (Todos los géneros, estrenados y aclamados):
Recorre los 19 géneros incorporando los títulos más votados y mejor calificados:
```json
{
  "media_type": "both",
  "target_per_genre": 25,
  "min_vote_count": 300,
  "min_vote_average": 7.0,
  "allow_unreleased": false
}
```

#### B. Expansión por Género Específico (ej. Terror con umbrales particulares):
Focaliza la ingesta únicamente en un género determinado:
```json
{
  "genre": "Terror",
  "media_type": "movie",
  "target_per_genre": 30,
  "min_vote_count": 150,
  "min_vote_average": 6.0,
  "allow_unreleased": false
}
```

#### C. Próximos Estrenos (Upcoming sin límite temporal hacia el futuro):
Descubre producciones cinematográficas en preventa o posproducción sin restricción de días:
```json
{
  "media_type": "movie",
  "upcoming": true,
  "limit": 20,
  "upcoming_days": 0
}
```

#### D. Próximos Estrenos a Corto Plazo (Ventana de 90 días, Películas y Series):
Ingesta producciones cuyo estreno esté pautado dentro de los siguientes 3 meses:
```json
{
  "media_type": "both",
  "upcoming": true,
  "limit": 30,
  "upcoming_days": 90
}
```

#### E. Próximos Estrenos por Género (ej. Animación):
```json
{
  "genre": "Animación",
  "media_type": "movie",
  "upcoming": true,
  "limit": 15,
  "upcoming_days": 180
}
```

---

### 3. Calidad y Purga de Catálogo

| Job | Endpoint | Método | Descripción |
|---|---|---|---|
| **Purgar Incompletos y Sin Póster** | `/api/v1/admin/sync/purge-incomplete` | `POST` | Elimina obras sin título, año, poster_url o marcadas como Adultos. Recalcula percentiles. |
| **Saneamiento de No Estrenados** | `/api/v1/admin/sync/cleanup-unreleased` | `POST` | Convierte títulos que alcanzaron su fecha de estreno y genera sus embeddings. |
| **Refrescar Métricas** | `/api/v1/admin/sync/refresh-metrics` | `POST` | Actualiza popularidad, votos, `status_tmdb` y duración de títulos existentes. |
| **Recalcular Percentiles** | `/api/v1/admin/sync/recalculate-percentiles` | `POST` | Normaliza popularidad y recalcula calificaciones bayesianas de todo el catálogo. |
| **Backfill de Países** | `/api/v1/admin/sync/backfill-countries` | `POST` | Completa el array consolidado de países de origen para soporte multipaís. |

---

### 4. Sincronización Automatizada

- **Sync Diaria Liviana (`POST /api/v1/admin/sync/daily`):**
  Sincroniza directamente series activas, consulta estrenos recientes en cartelera, refresca métricas y activa embeddings para títulos recién estrenados.
  ```json
  {
    "releases_days_window": 15,
    "allow_unreleased": false
  }
  ```

- **Sync Profunda Semanal (`POST /api/v1/admin/sync/deep`):**
  Sincronización exhaustiva semanal con auditoría de catálogo completo y refresco de métricas.
  ```json
  {
    "changes_days_window": 7,
    "releases_days_window": 30,
    "allow_unreleased": false
  }
  ```

- **Fotos de Actores (`POST /api/v1/admin/sync/actor-photos`):**
  Rellena fotos de actores en la base priorizando títulos populares.
  ```json
  {
    "limit": 500
  }
  ```

---

### 5. Telemetría y Monitoreo

- **Health Check (`GET /health`):** Despierta la instancia de Render si está dormida (cold start).
- **Estado de Todos los Jobs (`GET /api/v1/admin/sync/jobs/status`):** Devuelve el estado actual (`idle`, `running`, `completed`, `failed`), horas de inicio/fin y resultados/errores de cada uno de los 13 jobs.
- **Estado de un Job Específico (`GET /api/v1/admin/sync/jobs/{job_name}/status`):** Consulta individual (ej. `/api/v1/admin/sync/jobs/purge_incomplete/status`).

---

## 🛠️ Cómo abrir en Postman

1. Abrir **Postman**.
2. Ir a **Workspace** → **Import** (o `Ctrl + O`).
3. Seleccionar la carpeta `docs/postman` o abrir el workspace de Git vinculado.
4. En el selector de entornos (arriba a la derecha), elegir:
   - **`CineTrack - Production`** para correr jobs en Render (`https://cinetrack-api-zsen.onrender.com`).
   - **`CineTrack - Local / Dev`** para desarrollo local (`http://localhost:8000`).
