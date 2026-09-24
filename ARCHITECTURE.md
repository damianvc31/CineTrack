# Architecture.md — CineTrack

Este documento define la arquitectura técnica de CineTrack tras la evaluación y aprobación de la Fase 1.

---

## 1. Stack Técnico Confirmado

| Capa | Tecnología | Fundamento Técnico |
|---|---|---|
| **Backend** | Python + FastAPI | Soporte asíncrono nativo (`asyncio` / `httpx`) para optimizar I/O concurrente contra TMDB y proveedores de IA. Validación estricta y generación automática de contratos OpenAPI con Pydantic v2. Ecosistema natural de Python para el motor del recomendador por IA. |
| **Base de Datos** | PostgreSQL | Modelo relacional complejo (relaciones N:M para géneros/elenco, 1:N para temporadas/episodios, estados por usuario). Soporte nativo de funciones analíticas de ventana (`PERCENT_RANK()`) para cálculo de percentiles de popularidad. Migraciones versionadas con Alembic. |
| **Frontend** | React + Vite + TypeScript | Arquitectura de 3 capas limpia (SPA desacoplada que consume la API de FastAPI). Evita la duplicación de capas de servidor que implicaría Next.js (Node.js + Python). Compilación a estáticos de alto rendimiento con HMR instantáneo y sin complejidad de hidratación SSR. |
| **Estilos UI** | Tailwind CSS | Sistema de diseño ágil mediante clases utilitarias, consistente con los wireframes y componentes definidos en `docs/`. |

---

## 2. Modelo de Datos y Estrategia de Persistencia

### 2.1. Estrategia de Herencia (Título / Película / Serie)
Se adopta **Single Table Inheritance** / Tabla Unificada para `titulos`:
- Tabla `titulos`: contiene atributos comunes (nombre, sinopsis, portada, popularidad, vote_average, vote_count, percentil, status de emisión, etc.) con discriminador `tipo` (`'movie' | 'tv'`).
- **Clave candidata compuesta:** Restricción `UNIQUE (tmdb_id, tipo)` que permite la coexistencia de películas y series con identificadores idénticos en TMDB sin colisión, manteniendo como clave primaria interna un entero simple auto-incremental (`id`).
- Las películas aprovechan campos específicos (como `duracion`).
- Las series se relacionan 1:N con `temporadas` y a su vez 1:N con `episodios`.
- **Beneficio:** Elimina `JOINs` costosos en las pantallas principales y de exploración ("Todos", "Trending", "Estrenos") donde se presentan películas y series de forma unificada.

### 2.2. Esquema Relacional Principal
1. **`usuarios`**: Autenticación mínima (login/password con hash `bcrypt`/`argon2`), perfil (país, ciudad, biografía, `avatar_url`, `avatar_binario` para persistencia nativa de imagen recortada, fecha_registro, flag `es_admin`).
2. **`titulos`**: Catálogo de películas y series con metadatos técnicos y de TMDB. Utiliza campos exactos tipo `Date` (`fecha_estreno` y `fecha_fin`), exponiendo propiedades calculadas `@property anio_estreno` y `anio_fin` con setters para retrocompatibilidad total. Columna indexada y persistida `rating_unificado`.
3. **`generos`** & **`titulos_generos`**: Clasificación N:M (un título pertenece a múltiples géneros).
4. **`actores`** & **`titulos_elenco`**: Reparto principal N:M con columnas `foto_url` (imagen oficial TMDB `w185`), `personaje` y `orden`.
5. **`temporadas`** & **`episodios`**: Jerarquía episódica de series con duraciones por episodio y fechas de emisión.
6. **`estados_usuario_titulos`**: Estado granular por usuario (`favorito` booleano independiente, y `estado` mutuamente excluyente: `watchlist`, `siguiendo`, `vista`, o `null`), con sus respectivas marcas temporales para ordenamiento.
7. **`episodios_vistos`**: Historial atómico de episodios vistos por usuario y fecha.
8. **`resenas`**: Reseñas y puntajes. Diseñado con autor polimórfico: `usuario_id` (FK nullable a `usuarios`) o `autor_tmdb` (texto) con identificador externo `tmdb_review_id` para deduplicación.

### 2.3. Desacoplamiento de Reglas de Negocio
> *Las especificaciones funcionales y de dominio —incluyendo los criterios de curación de la Home, ventanas temporales, pools dinámicos, máquina de estados por episodios, fórmula de calificación unificada, políticas de ingesta inicial, sincronización diaria y reglas de créditos de elenco— están formalmente desacopladas en [docs/CATALOG_SPECS.md](docs/CATALOG_SPECS.md).*

### 2.4. Almacenamiento de Avatares y Encuadre Interactivo
- **Encuadre/Centrado Interactivo (Cropper):** En `EditProfileModal`, el usuario puede cargar cualquier imagen local (`.png`, `.jpg`, `.webp`), arrastrarla libremente para posicionarla en un visor circular y regular un zoom continuo (0.2x a 3.0x con presets rápidos *"Ajustar Completa"*, *"Llenar Círculo"* y *"Centrar"*).
- **Persistencia Binaria:** Al aplicar el encuadre, se renderiza la composición a un `<canvas>` 256×256 px en formato JPEG con fondo `#141414` de respaldo, transmitido a `POST /api/v1/users/me/avatar` que almacena los bytes en `Usuario.avatar_binario` y versiona la URL con timestamp (`/api/v1/users/{id}/avatar?v={timestamp}`).
- **Prevención de Tainted Canvas y CORS:** Para re-encuadrar avatares ya guardados en el servidor, `handleRecenter` descarga la imagen vía `fetch` y la convierte a un `Data URL` local, garantizando que el `<canvas>` nunca sea marcado como contaminado por el navegador. El endpoint `GET /api/v1/users/{user_id}/avatar` incluye cabeceras explícitas `Access-Control-Allow-Origin: *` y directivas `Cache-Control: no-cache, no-store, must-revalidate` para forzar refrescos inmediatos sin retener imágenes desactualizadas en la memoria caché del navegador.

---

## 3. Integración Externa y Arquitectura de Tareas Asíncronas

1. **Cliente HTTP y Comunicación con TMDB:**
   - **Cliente Asíncrono (`TMDBClient`):** Basado en `httpx.AsyncClient` con cabecera `Authorization: Bearer <TMDB_API_KEY>` (formato v4) y fallback a query param `api_key` v3.
   - **Control de Flujo y Resiliencia:** Pool de conexiones asíncrono con control de concurrencia mediante `asyncio.Semaphore(10)` y mecanismo de reintentos automáticos con retroceso exponencial ante errores transitorios de red o límites de tasa (`HTTP 429 Too Many Requests`).

2. **Procesamiento en Background y Ejecución Desacoplada:**
   - **API Asíncrona (`BackgroundTasks`):** Los endpoints administrativos de sincronización e importación (`/api/v1/admin/sync/*`) delegan la ejecución pesada a `fastapi.BackgroundTasks` respondiendo inmediatamente con `HTTP 202 Accepted`. Esto previene el bloqueo del hilo de peticiones y evita timeouts de clientes o proxies inversos.
   - **Módulo CLI (`app.jobs.sync_tmdb`):** Interfaz por línea de comandos desacoplada del ciclo de vida del servidor web para ejecuciones masivas iniciales, tareas cron o mantenimiento en terminal.

3. **Seguridad y Autenticación Administrativa Dual:**
   - **JWT de Administrador:** Dependencia de autorización que valida tokens JWT de usuarios registrados con el flag booleano `es_admin == True`.
   - **API Key M2M (`X-Admin-Key`):** Cabecera HTTP estática validada contra `ADMIN_API_KEY` para permitir invocaciones directas desde cron jobs, scripts externos o pipelines de CI/CD sin necesidad de mantener sesiones interactivas de usuario.

4. **Cálculo de Percentiles y Métricas Estadísticas:**
   - Uso de la función analítica SQL `PERCENT_RANK() OVER (ORDER BY popularidad ASC)` con fallback algorítmico en memoria para bases de datos que carezcan de soporte nativo para funciones de ventana.
   - Recálculo atómico disparado tras la incorporación o actualización de lotes en el catálogo.
5. **Recomendador de IA Embebido (RAG Híbrido Vectorial + SQL — Fase 8):**
   - Desacoplado de los hubs del entorno de desarrollo.
   - **Búsqueda Semántica Vectorial (`pgvector`):** Vectores de 768 dimensiones generados con Google AI Studio (`gemini-embedding-001`) persistidos en la columna `embedding` de PostgreSQL e indexados con HNSW (`vector_cosine_ops`).
   - **Filtrado Negativo Estricto:** Detección de exclusiones ("no anime", "sin comedia") y restricciones duras aplicadas en cláusulas SQL `WHERE` antes de computar distancias.
   - **Cascada Jerárquica y Grounding:** Pool acotado de los 20 mejores candidatos conceptuales inyectados al LLM (Gemini / Groq) con justificación personalizada y fallback determinista.

6. **Motor Integral de Reseñas y Calificación Decimal:**
   - **Regla Estricta 1 Reseña por Usuario por Título:** Garantizada mediante validación y upsert a nivel de servicio y restricciones de unicidad.
   - **Escala de Calificación Decimal:** Puntaje de 0.0 a 10.0 en múltiplos exactos de 0.5 (`abs(v*2 - round(v*2)) < 1e-6`) validado por Pydantic en `ReviewCreate`, aplicado exclusivamente a las reseñas locales de CineTrack. Las notas de TMDB se preservan con sus valores originales continuos.
   - **Puntaje Opcional y Rating Unificado:** Si el usuario no asigna puntaje (`puntaje = None`), la reseña es puramente textual y se excluye de la fórmula de promedio ponderado `rating_unificado`, evitando penalizar o sesgar el catálogo.
   - **Recálculo Atómico de Rating:** Toda inserción, actualización o eliminación (`DELETE /api/v1/titles/{id}/reviews`) dispara `recalculate_unified_ratings(titulo_id)` de forma atómica.
   - **Endpoints de Usuario:** `/api/v1/users/me/reviews` (paginado) y `/api/v1/users/me/unreviewed-watched` (títulos vistos sin reseña).

7. **Ciclo de Vida y Transición de Estados en Series:**
   - **Abandono y Reanudación Fluida:** El abandono (`POST /titles/{id}/unfollow`) quita el estado activo (`estado = None` en base de datos) conservando intactos los registros en `EpisodioVisto`, deduciéndose como "abandonada" en tiempo de lectura e interfaces. El endpoint `POST /titles/{id}/follow` permite reanudarla directamente a `siguiendo` sin forzar la alteración del checklist de episodios.

8. **Motor de Progreso de Temporadas y Regla de Regresión:**
   - **Cálculo sobre Episodios Estrenados:** El porcentaje de avance en series en seguimiento se calcula estrictamente sobre episodios ya estrenados (`fecha_estreno <= today`), evitando penalizar series en emisión con futuros episodios.
   - **Regla de Regresión a la Temporada Incompleta más Temprana:** Al evaluar el estado textual (`following_status_text`), se busca la primera temporada cronológica con episodios estrenados sin ver. Si se desmarca un episodio previo, el indicador retrocede a esa entrega (ej. `● S1 in progress`) de forma determinística, reflejando fielmente el punto pendiente.
   - **Orden Cronológico en Biblioteca:** Ordenamiento por `fecha_favorito DESC` para favoritos y `fecha_estado DESC` para watchlist, siguiendo y vistas recientes, actualizado en tiempo real al registrar avance en episodios.

9. **Endpoints de Usuario y Estadísticas de Perfil:**
   - `PATCH /api/v1/users/me`: Actualización de biografía, país, ciudad y URL de avatar (nombre de usuario inmutable).
   - `POST /api/v1/users/me/avatar`: Carga de avatar recortado en Base64, persistido en `avatar_binario` y referenciado en `avatar_url`.
   - `GET /api/v1/users/{id}/avatar`: Entrega pública de la imagen del avatar con cabeceras de caché HTTP.
   - `POST /api/v1/users/me/change-password`: Verificación de contraseña actual y actualización segura con hash `bcrypt`.
   - `GET /api/v1/users/me/stats`: Incorporación de `avg_movies_per_week` y `seasons_completed_count`, preservando la calificación personal verificada (`Resena.puntaje`) en el Top 5 por calificación.

10. **Reparto Principal con Fotos y Job de Población:**
    - Modelo `Actor` con columna `foto_url` (resolución TMDB `w185`).
    - Job asíncrono `app.jobs.populate_actor_photos` para consultar en lote fotos de actores en TMDB con control de rate limit.
    - Componente visual de Top Cast en `TitleDetailPage` con avatares circulares de actores, fotos oficiales, nombres y personajes.

11. **Motor del Recomendador Inteligente por IA (RAG Híbrido — Fase 8):**
    - **Recuperación Semántica Vectorial (`pgvector`):** Integración de embeddings con `gemini-embedding-001` (768 dimensiones) almacenados en PostgreSQL Neon y acelerados con índice HNSW (`vector_cosine_ops`).
    - **Filtrado Negativo Estricto:** Exclusión en tiempo de consulta SQL (`WHERE id NOT IN ...`) ante solicitudes explícitas de descarte (ej. *"no anime"*, *"sin terror"*).
    - **Estrategia Híbrida y Resiliencia con Cascada Jerárquica Multinivel:**
      - **Nivel 1 (Modelos Insignia / Flagship):** Se prueba primero el modelo insignia del proveedor primario (ej. Gemini `gemini-3.6-flash`). Si falla o agota cuota (HTTP 429), se intenta con el modelo insignia del proveedor secundario (ej. Groq `openai/gpt-oss-120b`), priorizando siempre la máxima capacidad de razonamiento.
      - **Nivel 2 (Modelos Alternativos / Respaldo Ligeros):** Si ambos modelos insignia fallan, se intenta en cascada ordenada con los modelos ligeros de respaldo del primario (`gemini-flash-lite-latest`, `gemini-3.5-flash-lite`, `gemini-3.8-flash`), seguidos por los de respaldo del secundario (`openai/gpt-oss-20b`, `groq/compound-mini`, `qwen/qwen3.8-27b`), aprovechando cuotas y límites independientes.
      - **Nivel 3 (Modo Offline Determinista):** Motor heurístico local si todos los servicios en la nube fallan, garantizando disponibilidad 100%.
      - **Fallo Rápido (Fail-Fast):** Detección inmediata de HTTP 429 sin pausas de reintento redundantes para conmutar de inmediato al siguiente modelo.
    - **Optimización de Cuota y Payload (Grounding Estricto):** El pool de candidatos se limita a 20 títulos (`RECOMMENDATION_CANDIDATES_LIMIT`), reduciendo el consumo en un 73% (de ~5.500 a ~1.500 tokens por consulta) para cuadruplicar el rendimiento de consultas por minuto (TPM) y cuota diaria (TPD). El modelo de lenguaje tiene prohibido inventar títulos externos y debe seleccionar exclusivamente entre los IDs del pool, respondiendo en JSON estructurado validado.
    - **Política de Resolución y Manejo de Incertidumbre (Opción C):**
      - Ante prompts genéricos o ambiguos (*"recomiéndame algo bueno"*, *"sorpréndeme"*), el recomendador ofrece 2 o 3 obras contrastantes y genera sugerencias temáticas interactivas (*chips*) para profundizar la búsqueda.
      - Ante prompts específicos, prioriza concordancia conceptual y semántica vía embeddings.
      - Validador previo permisivo que admite expresiones coloquiales en inglés/español con números y combinaciones alfanuméricas ("80s", "sci-fi"), bloqueando exclusivamente teclado machacado sin sentido.
    - **Hidratación y Contrato OpenAPI:** Endpoint `POST /api/v1/recommendations`, que devuelve cada título recomendado completamente hidratado como `TitleCardResponse` junto a la justificación personalizada de la IA (`reason`) y el proveedor y modelo exacto utilizado (`provider_used`, `model_used`).
    - **Especificación Completa y Diagrama de Arquitectura:** El flujo detallado, la cascada de resiliencia y el diagrama Mermaid están documentados en [docs/ARQUITECTURA_RECOMENDADOR.md](docs/ARQUITECTURA_RECOMENDADOR.md) y [docs/UML/recomendador/arquitectura_recomendador_hibrido.mmd](docs/UML/recomendador/arquitectura_recomendador_hibrido.mmd).

---

## 4. Arquitectura de Frontend (React 19 + Vite 8 + Tailwind CSS v4)

1. **Estructura y Principios de Diseño:**
   - **Alineación con Wireframes Figma AI:** Distribución en 3 columnas en desktop (Asistente IA, catálogo curado central y panel personal), optimizado para mobile con carruseles de snap-scroll horizontal.
   - **Sistema de Tokens Cinemático:** Fondo carbón profundo `#0d0d0d`, superficies `#141414`, bordes sobrios `#262626` y acentos cálidos dorado/ámbar (`#f59e0b` / `#eab308`).
   - **Internacionalización y Resiliencia:** Interfaz unificada en inglés per wireframes, componente `<CountryFlag />` para banderas con fallback unicode, y renderizado de nombres completos de país e idioma original mediante el estándar ECMAScript `Intl.DisplayNames`.
   - **Pantalla de Reseñas (`/reviews`):** Pestañas "My Reviews" (con edición y eliminación) y "Pending Reviews" (con redacción in-place para títulos vistos).
   - **PWA Ready:** Archivo `manifest.json` y meta tags de visualización `standalone` con `theme-color: #0d0d0d` para instalación nativa directa.

2. **Atribución Legal Obligatoria de TMDB (Sección 3 de Términos de Uso):**
   - Integración del logotipo oficial `Alt short (blue)` en SVG con gradiente corporativo (`#90cea1` -> `#01b4e4`) en el `Header` (píldora *"Powered by TMDB"*) y en el `Footer`.
   - Inclusión del deslinde de responsabilidad legal exigido: *"This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB."*

3. **Capa de Comunicación y Estado:**
   - **Cliente API Tipado (`services/api.ts`):** Envoltorio sobre `fetch` nativo con intercepción automática del token JWT almacenado en `localStorage`, manejo tipado de errores (`ApiError`) y soporte para query params serializados.
   - **Autenticación Global (`context/AuthContext.tsx`):** Estado de sesión reactivo con persistencia local, hidratación al arranque vía `/api/v1/auth/me` y modal unificado (`AuthModal`) accesible desde cualquier pantalla sin recarga.

4. **Pantallas de Perfil, Configuración y Localización en Frontend:**
   - **Perfil de Usuario (`/profile` - `ProfilePage`):** Fiel a `docs/wireframes/user-profile.png` con edición in-place mediante modal (`EditProfileModal`), números dorados en estadísticas, rankings con formato `Nombre · N seasons | AAAA-AAAA`, gráfico Donut SVG de géneros y listas inferiores organizadas en pestañas.
   - **Configuración (`/settings` - `SettingsPage`):** Cambio seguro de contraseña y selector de idioma de interfaz (English / Español).
   - **Diccionario de Traducción en Frontend:** Las traducciones de géneros se resuelven exclusivamente en cliente (`genreTranslations.ts`) manteniendo la base de datos canónica y limpia.

---

## 5. Estructura del Repositorio

```
/ (raíz del proyecto)
├── docs/                   # UMLs, wireframes y especificaciones visuales
├── backend/                # API FastAPI, modelos SQLAlchemy, servicios
│   ├── app/
│   │   ├── api/            # Routers (v1: auth, titles, home, admin, users, states)
│   │   ├── core/           # Configuración, JWT, variables de entorno
│   │   ├── db/             # Conexión DB, sesión async, Base
│   │   ├── models/         # Modelos de dominio ORM
│   │   ├── schemas/        # Esquemas Pydantic v2
│   │   ├── services/       # Lógica de catálogo, TMDB, estados
│   │   └── main.py         # Entrypoint de FastAPI
│   ├── tests/              # Suite de 49 pruebas Pytest
│   └── alembic/            # Migraciones de esquema
├── frontend/               # SPA React 19 + Vite 8 + TypeScript
│   ├── public/             # Estáticos directos (manifest.json, favicon, logo TMDB)
│   ├── src/
│   │   ├── assets/         # Branding SVG (CineTrack, TMDB) y placeholders
│   │   ├── components/     # Header, Footer, TitleCard, CarouselRow, AuthModal
│   │   ├── context/        # AuthContext y hook useAuth
│   │   ├── pages/          # Home, Catalog, TitleDetail, Library, Reviews, Profile, Recommendations
│   │   ├── services/       # api.ts, catalogService.ts, authService.ts
│   │   ├── types/          # Contratos TypeScript de catálogo, usuario y auth
│   │   └── App.tsx         # Router SPA y providers
│   └── tests/              # Suite de pruebas Vitest
├── TASK_PLAN.md            # Plan de tareas activo y estado de avance
├── ARCHITECTURE.md         # Este documento
├── CHANGELOG.md            # Registro de cambios por versión/tag
├── ROADMAP.md              # Backlog y próximas fases
└── README.md               # Guía de instalación, ejecución y variables
```

---

## 6. Arquitectura de Despliegue en Producción (PaaS Cloud)

Para la puesta en producción y entrega final del proyecto, se adopta una **Arquitectura PaaS Desacoplada (Plataforma como Servicio)** de nivel profesional, alta disponibilidad y costo cero:

```
                      ┌─────────────────────────────────────────────────────────┐
                      │                     CLIENTES / EVALUADORES              │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼ HTTPS
                      ┌─────────────────────────────────────────────────────────┐
                      │ FRONTEND: Vercel (Edge CDN)                             │
                      │ • SPA React 19 + TypeScript + Vite 8                    │
                      │ • URL: https://cinetrack.vercel.app                     │
                      │ • Certificado SSL automático y CDN global               │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                                   ▼ REST API Fetch (HTTPS)
                      ┌─────────────────────────────────────────────────────────┐
                      │ BACKEND: Render.com (Web Service)                       │
                      │ • FastAPI + Uvicorn (Python 3.11+)                      │
                      │ • URL: https://cinetrack-api.onrender.com               │
                      │ • Auto-Deploy continuo en cada push a rama de release   │
                      └─────────────────────┬─────────────────┬─────────────────┘
                                            │                 │
                                            ▼ SQL (AsyncPG)   │ Disparo diario con
                      ┌─────────────────────────────┐         │ X-Admin-Key
                      │ BASE DE DATOS: Neon.tech    │         │
                      │ • PostgreSQL Serverless     │         │
                      │ • Pooling nativo con SSL    │         │
                      │ • Catálogo persistido       │         │
                      └─────────────────────────────┘         │
                                                              ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │ CRON DIARIO DE CATÁLOGO: GitHub Actions                 │
                      │ • Programación cron: 03:00 AM UTC diario                │
                      │ • Invoca POST /api/v1/admin/sync/daily en background    │
                      │ • Sincroniza cartelera y catálogo sin servidor extra    │
                      └─────────────────────────────────────────────────────────┘
```

### 6.1. Componentes del Despliegue

1. **Base de Datos Gestionada (Neon.tech PostgreSQL):**
   - Instancia serverless de PostgreSQL 16 con SSL nativo y soporte de pooling PgBouncer.
   - Conexión asíncrona mediante `postgresql+asyncpg://` con normalización automática de `sslmode=require` a `ssl=require`.
   - Driver asyncpg configurado con `statement_cache_size=0`, `pool_pre_ping=True` y `pool_recycle=300` para tolerar la suspensión serverless y compatibilidad total con connection poolers.
   - Script de migración masiva por lotes `export_to_postgres.py` para transferir los 3.800+ títulos y 525k+ episodios directamente desde el entorno de desarrollo sin consumir cuotas de API externa.

2. **Backend API (Render.com Web Service):**
   - Vinculado al repositorio GitHub (`damianvc31/CineTrack`).
   - Infraestructura como Código (Blueprint) mediante `render.yaml` y fijado de runtime vía `backend/.python-version` (Python 3.12).
   - **Root Directory:** `backend`.
   - **Build Command:** `pip install -r requirements.txt`.
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   - **Health Check:** `/health` (reporta versión `1.0.0`).
   - **CORS Flexible:** Validador en `config.py` que soporta listas JSON o cadenas separadas por coma (`BACKEND_CORS_ORIGINS`).

3. **Frontend SPA (Vercel):**
   - Vinculado al repositorio GitHub en el subdirectorio `frontend`.
   - Reglas de rewrite en `frontend/vercel.json` para garantizar enrutamiento SPA client-side sin 404 al recargar.
   - **Build Command:** `npm run build` (Framework preset: Vite).
   - **Output Directory:** `dist`.
   - **Variable de Entorno:** `VITE_API_URL=https://cinetrack-api.onrender.com/api/v1`.

4. **Sincronización Diaria Periódica (GitHub Actions Workflow):**
   - Workflow desacoplado en `.github/workflows/daily_sync.yml` programado a las 03:00 UTC (00:00 hora de Argentina) y con soporte manual `workflow_dispatch`.
   - Ejecuta un `curl` diario enviando la cabecera `X-Admin-Key` al endpoint administrativo `/api/v1/admin/sync/daily`, el cual delega la ingesta a `fastapi.BackgroundTasks` y responde inmediatamente con `HTTP 202 Accepted`.

5. **Mantenimiento Mensual de Fotos de Elenco (GitHub Actions Workflow):**
   - Workflow en `.github/workflows/monthly_actor_photos.yml` programado el día 1 de cada mes a las 04:00 UTC con soporte de ejecución manual.
   - Invoca `POST /api/v1/admin/sync/actor-photos` autenticado con `X-Admin-Key` procesando un lote de 500 actores (gobernado por la variable de entorno `TMDB_ACTOR_PHOTOS_LIMIT = 500`) para mantener actualizados los retratos del reparto principal.

### 6.2. Fundamento Técnico de la Elección
- **Simplicidad Operativa (KISS):** Elimina la necesidad de aprovisionar y mantener sistemas operativos Linux, túneles SSH, configuración de Nginx y certificados Let's Encrypt manuales.
- **Contenerización Transparente:** Tanto Render como Vercel ejecutan la aplicación en contenedores Linux aislados y seguros por defecto, sin obligar al desarrollador a mantener `Dockerfile` ni consumir recursos locales de Docker Desktop.
- **Integración Continua (CI/CD):** Todo cambio o fix commiteado y pusheado se compila, verifica y publica automáticamente en producción en menos de dos minutos.

---

## 7. Arquitectura del Recomendador Inteligente (RAG Híbrido & Cascadas)

```
                                  PROMPT DEL USUARIO
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │ 0. Validador Determinista Local        │
                      │ • Filtra teclado machacado (0 ms LLM)  │
                      │ • Admite términos de dominio / alfanum │
                      └──────────────────┬─────────────────────┘
                                         │ Válido
                                         ▼
                      ┌────────────────────────────────────────┐
                      │ 1. Recuperación Relacional & Semántica │
                      │ • Entidades: Actores/Directores        │
                      │ • pg_trgm: Fuzzy matching (brad pit)   │
                      │ • pgvector: Similitud Coseno (768d)    │
                      │ • Filtro Negativo: NOT IN subquery     │
                      │ • Procedencia: Origen vs. Ambientación │
                      │ • Idioma Original: ISO 639-1 estricto  │
                      └──────────────────┬─────────────────────┘
                                         │ 20 Candidatos
                                         ▼
                      ┌────────────────────────────────────────┐
                      │ 2. Cascada Jerárquica de Modelos (LLM) │
                      │ • Primario: Gemini Flash               │
                      │ • Fallback 1: Groq (gpt-oss-120b)      │
                      │ • Fallback 2: Gemini / Groq ligeros    │
                      │ • Fallback 3: Motor Heurístico Offline │
                      └──────────────────┬─────────────────────┘
                                         │ JSON Estricto
                                         ▼
                      ┌────────────────────────────────────────┐
                      │ 3. Hidratación & Respuesta API         │
                      │ • Tarjetas interactivas TitleCard      │
                      │ • Justificaciones contextuales        │
                      │ • Sugerencias interactivas (Opción C)  │
                      └────────────────────────────────────────┘
```

### 7.1. Características Técnicas Centrales
1. **Persistencia Vectorial (`pgvector`):** Columna `embedding VECTOR(768)` en `titulos` con índice HNSW (`vector_cosine_ops`), vectorizada mediante `gemini-embedding-001`.
2. **Jerarquización de Entidades y Trigramas (`pg_trgm`):** Prioridad 1 a coincidencias directas de actores y directores con tolerancia difusa (`similarity >= 0.45`), evitando que los embeddings densos diluyan búsquedas por nombres propios.
3. **Procedencia Geográfica Dual-Track:**
   - **Producción / Origen:** Filtro estricto SQL por código ISO 3166-1 (`Titulo.pais`) ante gentilicios o expresiones de origen (*"cine argentino"*), garantizando 0 intrusos extranjeros.
   - **Ambientación / Setting:** Detección de giros de locación (*"ambientada en"*, *"que transcurra en Buenos Aires"*); rescata prioritariamente producciones nacionales (que retratan su propia geografía) e integra obras internacionales filmadas o ambientadas allí, transparentando su país de origen.
4. **Filtro de Idioma Original:** Mapeo a ISO 639-1 y filtrado estricto sobre `Titulo.idioma_original`.
5. **Cascada de Resiliencia Multi-Nivel:** Conmutación automática ante errores 429/500 entre Google AI Studio y Groq API con motor heurístico local determinista como red de seguridad final.

