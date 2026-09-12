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
1. **`usuarios`**: Autenticación mínima (login/password con hash `bcrypt`/`argon2`), perfil (país, ciudad, biografía, avatar, fecha_registro, flag `es_admin`).
2. **`titulos`**: Catálogo de películas y series con metadatos técnicos y de TMDB. Utiliza campos exactos tipo `Date` (`fecha_estreno` y `fecha_fin`), exponiendo propiedades calculadas `@property anio_estreno` y `anio_fin` con setters para retrocompatibilidad total. Columna indexada y persistida `rating_unificado`.
3. **`generos`** & **`titulos_generos`**: Clasificación N:M (un título pertenece a múltiples géneros).
4. **`actores`** & **`titulos_elenco`**: Reparto principal N:M con columnas `personaje` y `orden`.
5. **`temporadas`** & **`episodios`**: Jerarquía episódica de series con duraciones por episodio y fechas de emisión.
6. **`estados_usuario_titulos`**: Estado granular por usuario (`favorito` booleano independiente, y `estado` mutuamente excluyente: `watchlist`, `siguiendo`, `vista`, o `null`), con sus respectivas marcas temporales para ordenamiento.
7. **`episodios_vistos`**: Historial atómico de episodios vistos por usuario y fecha.
8. **`resenas`**: Reseñas y puntajes. Diseñado con autor polimórfico: `usuario_id` (FK nullable a `usuarios`) o `autor_tmdb` (texto) con identificador externo `tmdb_review_id` para deduplicación.

### 2.3. Desacoplamiento de Reglas de Negocio
> *Las especificaciones funcionales y de dominio —incluyendo los criterios de curación de la Home, ventanas temporales, pools dinámicos, máquina de estados por episodios, fórmula de calificación unificada, políticas de ingesta inicial, sincronización diaria y reglas de créditos de elenco— están formalmente desacopladas en [docs/CATALOG_SPECS.md](docs/CATALOG_SPECS.md).*

### 2.4. Almacenamiento de Avatares
- **Versión Mínima:** Selección de avatares predeterminados locales (identicons/SVGs) o URLs externas. Subida de avatares guardando una miniatura optimizada directamente en la base de datos (`BYTEA` / Base64 limitada a <300 KB), evitando la pérdida de archivos en filesystems efímeros de hosting PaaS.

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
5. **Recomendador de IA Embebido:**
   - Desacoplado de los hubs del entorno de desarrollo.
   - **Versión Mínima:** Recomendador simple sin function calling (implementado como última pieza del flujo núcleo según `spec.md`). Conexión vía API a modelo gratuito/eficiente (Google Gemini API / Groq API) con un prompt directo estructurado que combina el texto del usuario con sus preferencias de perfil (favoritos, vistos, reseñas) y puntajes de comunidad.
   - **Versión Superior:** Evolución planificada a *function calling* estructurado (herramientas de búsqueda exacta + similitud semántica con embeddings vectoriales), con la arquitectura de FastAPI ya preparada para soportar ambas modalidades.

6. **Motor Integral de Reseñas y Calificación Decimal:**
   - **Regla Estricta 1 Reseña por Usuario por Título:** Garantizada mediante validación y upsert a nivel de servicio y restricciones de unicidad.
   - **Escala de Calificación Decimal:** Puntaje de 0.0 a 10.0 en múltiplos exactos de 0.5 (`abs(v*2 - round(v*2)) < 1e-6`) validado por Pydantic en `ReviewCreate`, aplicado exclusivamente a las reseñas locales de CineTrack. Las notas de TMDB se preservan con sus valores originales continuos.
   - **Puntaje Opcional y Rating Unificado:** Si el usuario no asigna puntaje (`puntaje = None`), la reseña es puramente textual y se excluye de la fórmula de promedio ponderado `rating_unificado`, evitando penalizar o sesgar el catálogo.
   - **Recálculo Atómico de Rating:** Toda inserción, actualización o eliminación (`DELETE /api/v1/titles/{id}/reviews`) dispara `recalculate_unified_ratings(titulo_id)` de forma atómica.
   - **Endpoints de Usuario:** `/api/v1/users/me/reviews` (paginado) y `/api/v1/users/me/unreviewed-watched` (títulos vistos sin reseña).

7. **Ciclo de Vida y Transición de Estados en Series:**
   - **Abandono y Reanudación Fluida:** El abandono (`POST /titles/{id}/unfollow`) quita el estado activo (`estado = None` en base de datos) conservando intactos los registros en `EpisodioVisto`, deduciéndose como "abandonada" en tiempo de lectura e interfaces. El endpoint `POST /titles/{id}/follow` permite reanudarla directamente a `siguiendo` sin forzar la alteración del checklist de episodios.

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
