# TASK_PLAN.md — Plan de Trabajo Activo: CineTrack

## Estado General: Fase 11 Completada (v1.7.1)

- [x] **Fase 1:** Scaffolding inicial y smoke tests en verde (v0.1.0).
- [x] **Fase 2:** Persistencia y modelos relacionales completos en SQLAlchemy 2.0 (v0.2.0).
- [x] **Fase 3: Autenticación JWT y Motor de Estados (v0.3.0)**
  - [x] Modelo de seguridad con HS256 y expiración configurable.
  - [x] Endpoints `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`.
  - [x] Endpoints `/api/v1/titulos/{id}/estado`, `/api/v1/series/{id}/temporadas/{t}/episodios/{e}/visto`.
  - [x] Transiciones de estado estrictas y seguimiento atómico de episodios.
  - [x] Suite de 16 tests automatizados con `pytest` pasando.
  - [x] Tag `v0.3.0` generado y pusheado a GitHub.

- [x] **Fase 4: Integración TMDB y Sincronización (v0.4.0 - v0.4.2)**
  - [x] Paso 4.1: Plantillas JSON de referencia en `docs/templates/` (`template_pelicula.json`, `template_serie.json`).
  - [x] Paso 4.2: Parámetros de configuración en `backend/app/core/config.py` (cuotas, límites, prioridad de ingesta).
  - [x] Paso 4.3: Esquemas Pydantic de validación para importación manual en `backend/app/schemas/import_export.py`.
  - [x] Paso 4.4: Cliente HTTP asíncrono `TMDBClient` en `backend/app/services/tmdb_client.py` con semáforo de concurrencia y reintentos.
  - [x] Paso 4.5: Servicio `TMDBSyncService` en `backend/app/services/tmdb_sync_service.py` (ingesta inicial popular/top-rated, enriquecimiento de créditos, temporadas/episodios, sync diaria, recálculo de percentiles y carga manual con búsqueda inteligente).
  - [x] Paso 4.6: Script CLI `backend/app/jobs/sync_tmdb.py` para ejecución modular de tareas.
  - [x] Paso 4.7: Fixtures sintéticas de TMDB y suite de pruebas unitarias/integración con mocks en `backend/tests/test_tmdb_sync.py` (Zero-Waste).
  - [x] Paso 4.8: Verificación de tests (23/23 backend tests pasando sin llamadas externas reales).
  - [x] Paso 4.9: Actualización de documentación viva (`ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`, `README.md`).
  - [x] Paso 4.10: Commit y tag `v0.4.0`.
  - [x] Paso 4.11: Sincronización de reseñas TMDB (`--reviews`) y fórmula de rating unificado (v0.4.1).
  - [x] Paso 4.12: Integración de `/tv/changes` y `/movie/changes` en sync diaria (v0.4.2).

- [x] **Ajustes Técnicos Previos a Fase 5 (v0.4.3)**
  - [x] Parametrización de `TMDB_CHANGES_HOURS_WINDOW` (default 48 horas) en `backend/app/core/config.py` y `run_daily_sync`.
  - [x] Persistencia de columna indexada `rating_unificado` en modelo `Titulo` y método `recalculate_unified_ratings` ponderando TMDB + usuarios locales.
  - [x] Enriquecimiento de `titulos_elenco` con columnas `personaje` y `orden` para elenco jerarquizado y detallado.
  - [x] Flag `es_admin` en modelo `Usuario` y clave `ADMIN_API_KEY` para autenticación administrativa.
  - [x] Router de administración `backend/app/api/v1/admin.py` con `BackgroundTasks` para invocar todos los jobs vía API HTTP (`HTTP 202 Accepted`) con soporte completo de parámetros.
  - [x] Migración Alembic `0002_technical_adjustments.py`.
  - [x] Suite de tests ampliada a 32 tests (100% pasando en verde).

- [x] **Fase 5: Endpoints de Catálogo, Biblioteca y Reseñas (v0.5.0 - v0.5.1)**
  - [x] Esquemas Pydantic v2 en `backend/app/schemas/catalog.py`.
  - [x] Servicio de catálogo `backend/app/services/catalog_service.py`.
  - [x] Endpoints `/api/v1/home`, `/api/v1/titles`, `/api/v1/titles/{id}`, `/api/v1/genres`.
  - [x] Endpoints de reseñas `/api/v1/titles/{id}/reviews` (GET y POST) con recálculo de rating unificado.
  - [x] Endpoints de usuario `/api/v1/users/me/library` y `/api/v1/users/me/stats`.
  - [x] Suite de tests unitarios e integración en `backend/tests/test_catalog.py` (40 tests totales pasando en verde).
  - [x] Migración de `anio_estreno` y `anio_fin` a `fecha_estreno` y `fecha_fin` (`Date`) con Alembic `0003_dates_and_home_specs.py` (v0.5.1).
  - [x] Refactorización de secciones Home (`/api/v1/home`): New Releases (60d), Trending (90d con fecha de última temporada en series), Classics (películas >20a, rating $\ge 7.5$, votos $\ge 500$, pool 50 aleatorio), Top Rated (pool 100 aleatorio), By Genre ($\ge 10$ títulos) y Others ($< 10$ títulos).
  - [x] Exclusión automática de títulos vistos (`vista`) para usuarios autenticados en Home.
  - [x] Optimización de tests (mock de BackgroundTasks en `test_admin.py`, suite de 42 tests en < 5s).
  - [x] Vaciado de catálogo administrativo `DELETE /api/v1/admin/catalog` y CLI `--clear` (v0.5.2).
  - [x] Restricción de unicidad compuesta `UNIQUE (tmdb_id, tipo)` y migración Alembic `0004_composite_tmdb_id_tipo.py` para permitir colisiones de IDs TMDB entre películas y series (v0.5.3).
  - [x] Suite de tests ampliada a 45 tests (100% pasando en verde en < 5s).
  - [x] Refinamiento de API de catálogo y consultas (v0.5.4):
    - [x] Exposición de `popularidad_percentil` en `TitleCardResponse` para badge visual de tendencia (🔥 xx%).
    - [x] Separación de `section` (`new_releases`, `trending`, `classics`, `top_rated`, `others`), `sort_by` y `order` (`asc`/`desc`).
    - [x] Filtros por nombres en texto para `genero` y `actor`, y búsqueda abierta `q` ampliada al elenco.
    - [x] Cálculo de Trending con fecha del último episodio real emitido (`MAX(Episodio.fecha_estreno)`).
    - [x] Persistencia de `fecha_estreno` en temporadas, omisión de temporadas vacías (0 episodios) en `upsert_series` y depuración en base de datos.

---

  - [x] **Hito 5.2:** Setup de Tailwind CSS v4 en Vite 8, routing (`react-router-dom`), iconografía (`lucide-react`) y `AuthContext` con almacenamiento JWT.
  - [x] **Hito 5.3:** Pantalla 1 — Home (Header con branding + atribución oficial TMDB, Hero banner, carruseles horizontales con snap scroll para móvil y flechas desktop, banner de IA).
  - [x] **Hito 5.4:** Pantalla 2 — Detalle de Título (Backdrop, sinopsis, elenco con fotos, temporadas/episodios con checklist atómico y progreso, reseñas TMDB y locales con formulario).
  - [x] **Hito 5.5:** Pantalla 3 — Perfil de Usuario y Estadísticas (Tiempo total en horas/días, desglose cine vs. TV, colecciones).
  - [x] **Hito 5.6:** Pantallas complementarias:
    - Explorador y filtrado de catálogo (`/catalog`) con búsqueda abierta, géneros, secciones, actores y ordenamiento.
    - Mi Biblioteca (`/library`) con pestañas para Favoritos, Watchlist, Siguiendo y Vistas.
    - Previsualización del Recomendador IA (`/recommendations`).
    - Soporte PWA (`manifest.json` y meta tags para instalación en móvil) y suite de tests en Vitest.
  - [x] **Hito 5.7:** Rediseño inicial de distribución en 3 columnas y desduplicación de buscador.
  - [x] **Fase 1: Estética Real Dorado/Carbón, Inglés y Ajustes de Catálogo**
    - [x] Paleta cromática exacta de wireframes en `index.css` (negro carbón `#0d0d0d`, paneles `#141414`/`#181818`, acentos dorados `#f59e0b` y `#eab308`).
    - [x] Unificación de interfaz al inglés per wireframes (*Trending, New Releases, Classics, All/Movies/Series, AI Assistant, etc.*).
    - [x] Backend: `HOME_TRENDING_MIN_POPULARITY_PERCENTILE = 0.80` y `HOME_NEW_RELEASES_DAYS = 30` en `config.py`, `.env` y `.env.example`.
    - [x] Backend: Corregir discrepancia de filtro `section == 'others'` en `catalog_service.py`.
    - [x] Backend: Preservar títulos vistos en Home para no desvirtuar ni vaciar carruseles.
    - [x] Ícono `Gem` para Classics e íconos temáticos para géneros principales.
    - [x] Header: botón `X` de limpieza en inputs de búsqueda, ocultar botón "Explore" en `/catalog`, y avatar condicional (limpio en Home logueado, activo con campana en otras páginas).
    - [x] Retirar enlaces redundantes sueltos de catálogo en Home.
    - [x] Banderita de país en cards y detalle (con nombre completo de país e idioma original en detalle, y guión '-' para datos faltantes o duración 0).
  - [x] **Fase 2: Motor Integral de Reseñas (v0.7.0)**
    - [x] Regla estricta de 1 reseña por usuario por título: vista de reseña propia con botón de edición (lápiz) y eliminación (tacho de basura), ocultando el formulario de creación.
    - [x] Eliminación segura vía `DELETE /api/v1/titles/{id}/reviews` y recálculo automático de `rating_unificado`.
    - [x] Validación de calificación decimal de 0.0 a 10.0 en saltos exactos de 0.5 (aplicada exclusivamente a reseñas de CineTrack; calificaciones TMDB se preservan intactas).
    - [x] Checkbox / toggle para reseña opcional con o sin puntaje (`puntaje = None` / `-`), sin alterar el rating unificado global.
    - [x] Visualización completa de reseñas (comunidad local con avatares + TMDB con badge oficial `TMDB Review`), con paginación progresiva.
    - [x] Pantalla dedicada `/reviews` con dos pestañas: "My Reviews" (gestión, edición y borrado) y "Pending Reviews" (títulos marcados como vistos pendientes de reseña con redactor rápido in-place).
    - [x] Suite de 49 pruebas en backend (`pytest`) y tests unitarios en Vitest (100% pasando).
  - [x] **Ajustes de UX y Perfeccionamiento de Reseñas (v0.7.1 - v0.7.3)**
    - [x] Ocultamiento de Watchlist en películas vistas, scroll arriba automático en detalle de título, ajuste tipográfico en tarjetas para rangos de años y colapso rápido de episodios de series (v0.7.1).
    - [x] Modelo de estado `abandonada` deducido (invariante de dominio), endpoint `POST /titles/{id}/follow` (Resume / Follow) para series con progreso previo, ícono distintivo de serie abandonada en `TitleCard`, y actualización de especificaciones de catálogo (v0.7.3).
    - [x] Sincronización de temporadas confirmadas (con o sin fecha), detección de emisión en 6 estados semánticos (Currently Airing, Renewed con fecha, Renewed TBA/In Production, Pending Renewal, Ended, Canceled), filtrado de temporadas sin fecha en detalle y traducción completa de UI al inglés (v0.7.4).
  - [x] **Fase 3: Progreso de Siguiendo, Orden Cronológico, Perfil y Settings (v0.8.0)**
    - [x] Barra segmentada por temporada en Siguiendo (episodios estrenados) con regla de retroceso a la temporada incompleta más temprana y leyenda semántica (ej. `● S2 in progress`).
    - [x] Orden cronológico estricto (`fecha_favorito DESC`, `fecha_estado DESC`) en listas de usuario (`get_user_library`) y actualización atómica al registrar avance de episodios.
    - [x] Pantalla de Perfil fiel a `user-profile.png`: identidad con avatar prominente y edición de usuario por lápiz (bio, país, ciudad, avatar URL), métricas destacadas (total horas, promedio semanal cine, temporadas completadas), rankings Top 5 con formato `Nombre · N seasons | AAAA-AAAA`, puntaje personal verificado en calificación propia, Donut chart SVG de géneros, sección Following en fila completa y trío de listas inferiores.
    - [x] Pantalla dedicada de Configuración `/settings` con cambio seguro de contraseña y selector de idioma de interfaz (con traducción de géneros en frontend sin alterar la base de datos).
    - [x] Unificación a paleta dorado/carbón (`#141414`, `#262626`, `#f59e0b`), modal de autenticación (`AuthModal`) localizado a inglés con campos completos de perfil en registro, y avatares ampliados en Home (`w-14 h-14`), Header (`w-10 h-10`) y Perfil (`w-32 h-32`).
    - [x] Suite de 53 tests en backend (`pytest`) y tests unitarios en Vitest (100% pasando).

  - [x] **Fase 6: Recomendador Inteligente con IA (v0.9.0 — Versión Mínima / MVP)**
    - [x] Integración de API híbrida: Google Gemini 2.0 Flash (`gemini-2.0-flash`) como primario, con conmutación por error a Groq API (`llama-3.3-70b-versatile`) y motor heurístico local determinista.
    - [x] Grounding estricto sobre pool de 30-45 candidatos locales de PostgreSQL con extracción de sinopsis y fragmentos de reseñas locales.
    - [x] Heurística de resolución ante ambigüedad y sugerencias interactivas (*chips*) para prompts confusos (`clarification_needed`).
    - [x] Endpoint `POST /api/v1/recommendations` con validación Pydantic v2 e hidratación completa de tarjetas `TitleCardResponse`.
    - [x] Pantalla dedicada `/recommendations` (`RecommendationsPage.tsx`), sincronización con query param `?prompt=...`, botón de acceso rápido con chispa en navbar y menú mobile, disparadores temáticos y filtros rápidos por tipo de obra.
    - [x] Suite de 65 tests automatizados en backend con cobertura completa de conmutación por error y fallback (100% pasando).

  - [x] **Expansión de Catálogo por Géneros y Afinación (v0.9.1 - v0.9.2)**
    - [x] Job CLI y endpoint administrativo de expansión de catálogo por géneros con umbrales de calidad (`--expand`, v0.9.1).
    - [x] Mapeo semántico bilingüe de conceptos en español (`THEME_EXPANSION_MAP`) y búsqueda temática priorizada en SQL para sinopsis TMDB (v0.9.2).
    - [x] Elevación de piso de votos para relleno general a 150 votos y desacople de perfil en búsquedas con términos específicos (v0.9.2).

  - [x] **Optimización de Cuota y Cascada Jerárquica Multi-Nivel entre Proveedores (v0.9.3)**
    - [x] Reducción de 45 a 20 candidatos en pool (`RECOMMENDATION_CANDIDATES_LIMIT`), recortando el footprint de tokens de entrada en un 73% (~1.500 tokens).
    - [x] Cascada jerárquica de 2 niveles de calidad entre modelos de nube:
      - Nivel 1: Modelos insignia principales (Primario -> Secundario, ej. Gemini `gemini-3.6-flash` -> Groq `openai/gpt-oss-120b`).
      - Nivel 2: Modelos de respaldo ligeros con cuotas independientes (Primario -> Secundario, ej. `gemini-flash-lite-latest`, `3.5-flash-lite`, `3.8-flash` -> `openai/gpt-oss-20b`, `compound-mini`, `qwen-27b`).
      - Nivel 3: Motor heurístico offline determinista local.
    - [x] Fallo rápido inmediato ante código HTTP 429 sin pausas redundantes de reintento.
    - [x] Variables de entorno `GEMINI_FALLBACK_MODELS`, `GROQ_FALLBACK_MODELS`, `RECOMMENDATION_CANDIDATES_LIMIT` y `AI_RECOMMENDER_PRIMARY` en `.env`, `.env.example` y `config.py`.
    - [x] Suite de 70 tests de backend pasando al 100%.

  - [x] **Validación Determinista, Resiliencia y Control de Flujo del Recomendador (v0.9.4)**
    - [x] Filtro de ventana temporal en Estadísticas del Perfil (`time_window`: `1m`, `3m`, `6m`, `1y`, `5y`, `10y`, `all_time`) en backend y frontend con dropdown interactivo e i18n.
    - [x] Rediseño de tarjetas "Siguiendo" en Perfil con póster original 2:3 vertical nítido en lugar de recorte horizontal.
    - [x] Avatares de elenco en detalle de título con componente `ActorAvatar` y fallback elegante de iniciales completas (ej. *"RDJ"*).
    - [x] Detección determinista de texto basura/ininteligible (`is_unintelligible_prompt`) que evita consumo de LLMs sin interferir con consultas legítimas que contienen números (décadas, secuelas, ratings, años relativos).
    - [x] Cancelación inmediata de búsquedas en curso ("Frenar búsqueda") mediante `AbortController` en el navegador y `http_request.is_disconnected()` en el servidor FastAPI.
    - [x] Mensaje informativo claro y específico para el Validador de Entrada Local al requerir aclaración, diferenciándolo del aviso de caída de IA.
    - [x] Limpieza del prompt no entendido y reemplazo sincronizado en tiempo real de la barra superior al responder la aclaración.
    - [x] Desacoplamiento de dependencias reactivas volátiles en `executeRecommendation` para prevenir bucles de re-ejecución con `searchParams`.
    - [x] Limpieza completa y aborto de peticiones al iniciar o cerrar sesión desde cualquier punto de la aplicación.
    - [x] Suite de 71 tests en backend pasando al 100% y builds limpios en frontend.

  - [x] **Fase 7: Despliegue a Producción y Entrega Final (v1.0.0 - v1.0.2)**
    - [x] Paso 7.1: Documentación de la arquitectura de despliegue en `ARCHITECTURE.md` y `README.md`.
    - [x] Paso 7.2: Script de migración y volcado de base de datos (`export_to_postgres.py`) para trasladar el catálogo local `cinetrack.db` a PostgreSQL en la nube (verificado con `--dry-run`).
    - [x] Paso 7.3: Aprovisionamiento de base de datos PostgreSQL Serverless en Neon.tech y volcado masivo exitoso (634.107 registros verificados).
    - [x] Paso 7.3b: Ingesta masiva y sincronización de 25.116 fotos oficiales de actores (`populate_actor_photos.py`) y ampliación `String(500)` de roles de elenco.
    - [x] Paso 7.4: Despliegue del backend FastAPI en Render.com (Web Service vía Blueprint `render.yaml`) y configuración de variables de entorno de producción.
    - [x] Paso 7.5: Despliegue de la SPA React 19 en Vercel con variable `VITE_API_URL` apuntando al backend en Render y reglas `vercel.json`.
    - [x] Paso 7.6: Creación de workflows de automatización en GitHub Actions: sincronización diaria (`daily_sync.yml`) y mantenimiento mensual de fotos de elenco (`monthly_actor_photos.yml`).
    - [x] Paso 7.7: Validación funcional de extremo a extremo en entorno de producción (login, catálogo, reseñas, recomendador y cron).
    - [x] Paso 7.8: Tags formales `v1.0.0`, `v1.0.1` y `v1.0.2` generados y pusheados a GitHub.

---

## Fase 8: Robustecimiento y Calidad del Recomendador con IA (RAG Híbrido) (v1.1.0)
- [x] **Paso 8.1: Calibración del Validador Previo (`is_unintelligible_prompt`):**
  - Rediseñar el validador para que solo filtre basura extrema (teclado machacado sin vocales, strings cortísimos) sin rechazar oraciones naturales ni mezclas de números/letras (ej. "80s").
- [x] **Paso 8.2: Preparación de la Base de Datos (Neon Dev):**
  - [x] Crear rama hija en Neon (development branch) para mantener la data y aislar las pruebas.
  - [x] Modificar el modelo `Titulo` para agregar la columna vectorial `embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)`.
  - [x] Crear y ejecutar migración Alembic `0005_pgvector_embedding.py` (`CREATE EXTENSION vector;` + índice HNSW `vector_cosine_ops`).
- [x] **Paso 8.3: Integración de Embeddings (Google AI Studio Embeddings):**
  - [x] Crear `EmbeddingService` (`gemini-embedding-001` con dimensión 768 y batching `batchEmbedContents`).
  - [x] Crear job `sync_embeddings.py` y script CLI `backend/scripts/sync_embeddings.py` para calcular embeddings del catálogo.
  - [x] Integrar `sync_pending_embeddings()` en `tmdb_sync_service.py` para sincronización automática de títulos nuevos.
- [x] **Paso 8.4: Sistema de Recomendación Híbrido (Vector + SQL):**
  - [x] **Filtrado Negativo Estricto:** Detección de exclusiones ("no anime", "sin comedia", etc.) y aplicación de `WHERE id NOT IN (subquery géneros)`.
  - [x] **Búsqueda Vectorial:** Similitud coseno con `pgvector` (`Titulo.embedding.cosine_distance(user_vec).asc()`) con fallback automático y elegante a búsqueda léxica.
- [x] **Paso 8.5: Manejo de Ambigüedad:**
  - [x] Calibración de `SYSTEM_PROMPT` con la política de Opción C (respuesta amable ante pedidos vagos, repreguntas temáticas contrastantes y muestra de 2 títulos variados).
- [x] **Paso 8.6: Pruebas, Calibración Avanzada y Cierre (v1.1.0):**
  - [x] Jerarquización de entidades y fuzzy matching difuso con `pg_trgm` (tolerancia a errores ortográficos como 'brad pit' o 'scorsece').
  - [x] Soporte avanzado para rewatch: desdoblamiento de inclusión mixta (*"podés incluir lo que ya vi"*) vs. rewatch exclusivo (*"solo lo que ya vi"*).
  - [x] Reconocimiento dual-track de Procedencia Geográfica: país de producción estricto (`Titulo.pais`) vs. historias ambientadas/locación (setting/lore en sinopsis y vector search, con inclusión de títulos nacionales).
  - [x] Filtro estricto de idioma original (`Titulo.idioma_original`).
  - [x] Batería automatizada de 20 casos de prueba de borde con 100% de éxito en modo autenticado e invitado.
  - [x] Suite completa de backend ampliada a 79 tests pasando en verde (`pytest`) y tests de frontend en verde (`vitest`).
  - [x] Tag `v1.1.0`.

---

## Fase 9: Optimización de Rendimiento y Latencia Cross-Web (v1.2.0)
- [x] **Paso 9.1: Motor de Caché en Memoria en Backend (FastAPI)**
  - [x] Implementar gestor de caché con TTL en memoria (`backend/app/core/cache.py`) sin dependencias externas pesadas.
  - [x] Refactorizar `get_home_sections` en `catalog_service.py`: cachear los pools de títulos (Trending, Classics, Top Rated, New Releases, By Genre) en memoria.
  - [x] Preservar la rotación aleatoria ejecutando `random.sample` sobre los pools cacheados en cada petición (0 queries a base de datos para estructura del catálogo).
  - [x] Consulta atómica unificada de estados de usuario para inyectar `favorito`, `estado`, `rating` y abandono de series.
  - [x] Cachear conteos y consultas frecuentes en `get_titles` (Explorar Catálogo).
  - [x] Optimizar `get_user_library` para no cargar episodios de títulos que no están en seguimiento.
  - [x] Integrar invalidación de caché en jobs de sincronización TMDB y endpoints administrativos (`clear_cache`).
  - [x] Tests automatizados en `backend/tests/test_catalog.py` (81/81 tests pasando en verde).
- [x] **Paso 9.2: Integración de React Query en Frontend**
  - [x] Instalar `@tanstack/react-query` en `frontend/package.json`.
  - [x] Configurar `QueryClientProvider` en `frontend/src/App.tsx` con políticas de retención (`staleTime: 5 min`, `gcTime: 15 min`).
- [x] **Paso 9.3: Optimistic UI & Máquina de Estados Reactiva**
  - [x] Crear sistema centralizado de mutaciones optimistas para títulos y episodios (`useTitleMutations.ts` / hooks de estado).
  - [x] `onMutate`: actualización instantánea (0ms) en la caché local para feedback visual inmediato (corazón, watchlist, vista, seguir, episodios y temporadas completas).
  - [x] `onError`: rollback seguro al snapshot anterior y notificación amigable al usuario (`ToastContext.tsx`).
  - [x] `onSettled`: invalidación y revalidación suave en background.
- [x] **Paso 9.4: Migración de Páginas Clave a React Query**
  - [x] Migrar `HomePage.tsx` para consumir queries cacheadas sin re-fetching innecesario.
  - [x] Migrar `CatalogPage.tsx` con soporte de metadatos globales cacheados y queries reactivas de títulos.
  - [x] Migrar `LibraryPage.tsx` y sincronización instantánea con mutaciones de títulos.
  - [x] Migrar `ProfilePage.tsx` con soporte de caché para estadísticas multi-ventana y sincronización reactiva de biblioteca.
- [x] **Paso 9.5: Verificación Integral, Tests y Documentación Viva**
  - [x] Ejecutar suite de pruebas de backend (`pytest`: 81/81 en verde) y frontend (`vitest` + `npm run build`: 100% en verde).
  - [x] Refinamiento de performance F5 y rotación de navegación: authLoading guard en frontend, `get_optional_user_id` sin hit de BD, y caché en RAM de estados personales para Home con auto-invalidación en mutaciones (latencia de Home autenticada reducida de 2800ms a 2.6ms).
  - [x] Comprobar ausencia de regresiones visuales y funcionales.
  - [x] Actualizar `ARCHITECTURE.md`, `CHANGELOG.md`, `README.md` y `ROADMAP.md`.
  - [x] Commit y tag `v1.2.0`.

---

## Fase 10: Robustecimiento del Pipeline TMDB, Ciclo de Vida de Estrenos y Cierre Pre-Entrega (v1.2.1 - v1.6.3)

### 10.1: Paginación Exhaustiva de Changes, Active Series Sync y Refresco Diario de Métricas (v1.2.1)
- [x] **Paginación Exhaustiva de `/changes`:** Paginación dinámica hasta `total_pages` (eliminando el bug de solo leer página 1, recuperando el 100% de cambios de TMDB).
- [x] **Seguimiento Activo de Series (`Active Series Sync`):** Consulta activa de las series locales en `Returning Series`, `In Production` y `Planned` desduplicadas contra changes para actualizar transiciones a Ended/Canceled y temporadas futuras.
- [x] **Refresco Masivo de Métricas Diarias (`refresh_catalog_metrics`):** Actualización de popularidad y conteo de votos de los 3.864 títulos en la sync diaria mediante consultas ultraligeras, evitando el estancamiento de percentiles y rankings.
- [x] **Aligeramiento de Payloads TMDB:** Retiro del parámetro `keywords` no utilizado en `TMDBClient.get_details()`.
- [x] **Desacople de Reseñas en Sync Diaria:** Omitir la consulta de reviews para títulos existentes en el job diario, reservando la absorción para el workflow mensual.
- [x] **Workflow Mensual de Reseñas:** Creación de `.github/workflows/monthly_reviews_sync.yml` programado el día 1 de cada mes a las 05:00 UTC.
- [x] **Soporte de Lote en Importación/Actualización:** Ampliación de `POST /api/v1/admin/sync/import-tmdb` y CLI `--import-tmdb-id` para recibir listas de IDs y forzar sincronización in-place.
- [x] **Coherencia Temporal en Frontend (MobLand):** Ajuste de `isUnreleased` en `TitleDetailPage.tsx` considerando `proximo_episodio_fecha` para que episodios estrenando en el día permanezcan bloqueados hasta que el puntero avance.
- [x] **Verificación y Tests:** Suite de backend ampliada a 83 tests (100% en verde) y build limpio de frontend. Verificación exitosa en local de *Snowy Mountain* (TMDB ID 319562).

### 10.2: Soporte Multi-País, Banderas Históricas y Purga de Calidad (v1.2.3)
- [x] **Soporte Multi-País y Coproducciones:** Delimitación por comas en `Titulo.pais`, extracción con fallback `origin_country` -> `production_countries`, campo computado `paises: list[str]`.
- [x] **Banderas Vectoriales SVG y Países Históricos:** Banderas SVG inline para `SU`, `YU` y `CS`, y diccionario de nombres sin anacronismos en frontend.
- [x] **Blindaje Preventivo de Ingesta:** Módulo `is_latin_legible()` y descarte de obras sin fecha, país, idioma o no latinas.
- [x] **Backfill y Purga en Neon Prod:** 256 títulos enriquecidos y 7 inválidos purgados. Catálogo 100% íntegro.

### 10.3: Resiliencia PaaS, Keep-Alive y Concurrencia de Sincronización (v1.3.0)
- [x] **Prefetching Concurrente en Lotes (`asyncio.gather`):** Concurrencia de 10 peticiones simultáneas en `run_daily_sync`.
- [x] **Endpoints Administrativos de Estado de Jobs:** `/api/v1/admin/sync/jobs/{job_name}/status` y `/api/v1/admin/sync/jobs/status` respaldados por `ACTIVE_JOBS`.
- [x] **Keep-Alive en Workflows:** Polling cada 15 segundos en `daily_sync.yml`, `monthly_actor_photos.yml` y `monthly_reviews_sync.yml`.

### 10.4: Desacople de Sincronización Diaria Liviana y Sincronización Profunda Semanal (v1.4.0)
- [x] **Sincronización Diaria Liviana (`run_daily_sync`):** Retirar la consulta de `/changes` del flujo diario. Enfocar exclusivamente en series activas de CineTrack (`Returning Series`, `In Production`, `Planned`) con lotes concurrentes y Season Skipping. Cartelera simétrica centrada de 30 días y refresco masivo de métricas.
- [x] **Sincronización Profunda Semanal (`run_deep_sync`):** Implementar `run_deep_sync(changes_days_window=7, releases_days_window=15, allow_unreleased=False)` los domingos recorriendo exhaustivamente `/changes` de TMDB contra el catálogo completo.
- [x] **Endpoint Administrativo y CLI:** Registro de job `deep_sync` en `ACTIVE_JOBS`, endpoint `POST /api/v1/admin/sync/deep` y CLI `--deep`.
- [x] **Workflows de GitHub Actions Sin Colisiones:** `daily_sync.yml` lun-sáb 03:00 UTC y `weekly_deep_sync.yml` dom 02:00 UTC.

### 10.5: Modo Upcoming en Expansión, Ingesta Manual Desbloqueada y Badges Visuales (v1.5.0)
- [x] **Expansión de Catálogo en Modo Próximos Estrenos (`--expand --upcoming`):** Búsqueda de títulos futuros (`primary_release_date.gte = hoy`) con ventana temporal configurable (`--upcoming-days`, default 365 días), sin filtros de votos y popularidad $\ge 10.0$. Target de 10 títulos por género o global.
- [x] **Desbloqueo de Ingesta Manual:** `allow_unreleased: true` por defecto en endpoints y flags CLI para importar obras no estrenadas.
- [x] **Refinamiento Visual de Badges en Detalle de Título:** Desambiguación cromática ("Renewed TBA" púrpura, "En Producción" Teal, "Estrenada" verde esmeralda).
- [x] **Corrección de Series Estreno Mismo Día:** Clasificación estricta en Upcoming vs Released y descarte seguro en carruseles de Home (`_apply_base_filters`). Chips de sección en Catálogo (`CatalogPage.tsx`).
- [x] **Desacoplamiento de Límites en Expansión Upcoming:** Flags `--upcoming-days 0` (horizonte infinito) y `--limit 0` (sin tope).

### 10.6: Ciclo de Vida de Próximos Estrenos, Embeddings Selectivos y Umbrales del Recomendador (v1.6.0)
- [x] **Configuración Operativa:** `AI_RECOMMENDER_MIN_VOTES_VECTOR`, `AI_RECOMMENDER_MIN_VOTES_THEMATIC`, `AI_RECOMMENDER_MIN_VOTES_FALLBACK`, `AI_RECOMMENDER_NEW_RELEASE_DAYS`.
- [x] **Blindaje y Filtros Base:** `apply_base_filters` con `get_released_filter_condition(today)` y soporte de estrenos recientes sin piso de votos.
- [x] **Generación Selectiva de Embeddings:** Exclusión estricta de obras no estrenadas en `sync_embeddings.py` para preservar cuota de Gemini. Sincronización automática de embeddings post-expansión.
- [x] **Calidad e Integridad de Ingesta:** Exigencia de póster oficial en ingesta y purga de incompletos.

### 10.7: Suite de Postman, Telemetría de Ingesta y Resiliencia de Episodios (v1.6.2)
- [x] **Suite de Postman y Operaciones Administrativas:** Colección modular YAML (`docs/postman/`) con 5 carpetas y 20 requests completas y seguras.
- [x] **Telemetría Granular de Ingesta:** Discriminación de creados vs actualizados (`_is_new`, `created_count`, `updated_count`) en jobs de sync y logs de CLI.
- [x] **Resiliencia ante Latencia de Episodios TMDB:** Desacople de `isUnreleased` para permitir marcar visto a episodios cuya fecha ya llegó sin depender del avance del puntero de TMDB. Simplificación de `DailySyncRequest`.

### 10.8: Pulido de Interfaz, Calificaciones sin Texto y Cierre de Calidad Pre-Entrega (v1.6.3)
- [x] **Header y Búsqueda Interactiva:** Ampliación del input y botones interactivos de lupa con hover dorado.
- [x] **Reparto Principal Expandible:** Selector "Ver más / Ver menos" en `TitleDetailPage.tsx` para elencos de más de 12 actores.
- [x] **Coherencia de Temporadas:** Cálculo optimista comparando contra episodios emitidos a la fecha.
- [x] **Localización Completa de Reseñas:** Claves traducidas en `LanguageContext.tsx` y eliminación de cadenas hardcodeadas.
- [x] **Calificaciones sin Texto (Rating Directo):** Reseñas con puntaje opcional o reseña sin texto mediante `CheckConstraint` en base de datos (migración Alembic `0006_nullable_review_text.py`).

---

## Fase 11: Factor Sorpresa y Variedad en Recomendador IA (v1.7.0)

- [x] **Paso 11.1: Enum Normalizado y Configuración de Modelos (`config.py`):**
  - [x] Definición de `VarietyLevel` (`VERY_LOW`, `LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH`).
  - [x] `AI_RECOMMENDER_DEFAULT_VARIETY: VarietyLevel = VarietyLevel.MEDIUM` en `config.py`, `.env.example`, `.env`, `.env.local`, `.env.prod` y `render.yaml`.
  - [x] Actualización de fallbacks de modelos (`GEMINI_FALLBACK_MODELS` y `GROQ_FALLBACK_MODELS` con incorporación de `qwen/qwen3.8-27b`).
  - [x] Desacople dinámico de modelos de razonamiento vía `AI_REASONING_MODELS` configurable por entorno.
- [x] **Paso 11.2: Persistencia de Preferencia de Usuario y Migración:**
  - [x] Columna `preferencia_variedad_ia: Mapped[str]` en modelo `Usuario` (`default="MEDIUM"`).
  - [x] Migración Alembic `0007_user_variety_preference.py` ejecutada en SQLite local, Neon Dev y Neon Prod.
  - [x] Actualización de esquemas `UserResponse` y `UserUpdate` en backend.
- [x] **Paso 11.3: RAG Multi-Nivel con Modulación de Votos, Exención de Entidad y Guardrails (`catalog_service.py`):**
  - [x] `get_recommendation_candidates(..., variety_level: VarietyLevel = VarietyLevel.MEDIUM)`.
  - [x] Modulación de umbrales sobre `settings.AI_RECOMMENDER_MIN_VOTES_*` ($\times 1.8$ a $\times 0.3$).
  - [x] Restricción de rating crítico (`rating_unificado >= 7.5`) para `VERY_LOW`.
  - [x] Exención de entidades directas (director, actor, título explícito no se descartan por rating bajo o pocos votos).
  - [x] Salvaguarda contra inanición (si los candidatos son < 3, relaja filtros automáticamente).
- [x] **Paso 11.4: Despachador de LLM Dinámico, Directivas Semánticas y Resiliencia Multiclave (`ai_recommender_service.py`):**
  - [x] Mapeo de parámetros (`SLIDER_MAPPING`) para modelos Reasoning vs Standard.
  - [x] Inyección segura de `reasoning_effort` para modelos clasificados dinámicamente en `AI_REASONING_MODELS`.
  - [x] Inyección de directivas semánticas explícitas por nivel de variedad en `_build_user_message`.
  - [x] Iteración exhaustiva de todas las API keys configuradas por modelo antes de descender en la cascada.
- [x] **Paso 11.5: Endpoint de Recomendaciones:**
  - [x] `POST /recommendations` aceptando y respondiendo `variety_level: Optional[VarietyLevel] = None` con fallback automático a la preferencia de usuario de la BD o valor default.
- [x] **Paso 11.6: Frontend — UI de Configuración y Selector Rápido:**
  - [x] Slider de 5 posiciones en `SettingsPage.tsx` con guía central fija (*Balanceada (Recomendado)*) y tarjeta descriptiva dinámica.
  - [x] Selector interactivo directo y badge visual en `RecommendationsPage.tsx` para modular la variedad al vuelo.
  - [x] Localización completa (ES/EN) en `LanguageContext.tsx`.
- [x] **Paso 11.7: Suite de Tests Automatizados y Verificación:**
  - [x] Tests unitarios de modulación de candidatos en `test_recommendations.py`.
  - [x] Tests de inyección de `reasoning_effort` en Groq según tipo de modelo y calibración de temperatura.
  - [x] Tests de actualización de preferencia de variedad en `test_users.py`.
  - [x] Verificación total de suite `pytest` (109/109 pasando) y build de `frontend` en verde.
- [x] **Paso 11.8: Batería de Pruebas Integral en Vivo (Neon Dev):**
  - [x] Fase 1 (11 escenarios sin usuario autenticado: G1, G2, G3, G4 y G5 transversal).
  - [x] Fase 2 (Usuario real `damianvc31`: lectura automática de preferencia de variedad e interacción con 49 títulos vistos y favoritos).
  - [x] Prueba desafiante de nicho con baja calificación (*La señal*, 5.92★, 25 votos) verificada en `VERY_LOW`.
- [x] **Paso 11.9: Bloqueo de Marcado como Visto en Títulos No Estrenados (v1.7.1):**
  - [x] Ocultamiento del botón del ojo (👁) en `TitleCard.tsx` y en `TitleDetailPage.tsx` para películas no estrenadas (fecha futura o status de producción/planificación) y series sin episodios emitidos a la fecha, preservando Favorito (♥) y Watchlist (🔖).
  - [x] Condición en `TitleDetailPage.tsx` para botón "Marcar Temporada Completa", visible únicamente si la temporada cuenta con episodios emitidos.
  - [x] Utilidad centralizada `releaseUtils.ts` (`isTitleUnreleased`) con suite de 5 tests unitarios en Vitest (7 tests frontend pasando).
  - [x] Blindaje e invariante de dominio en backend (`state_service.toggle_watched`) con HTTP 400 Bad Request y 2 tests unitarios en `test_state_machine.py` (111 tests backend pasando al 100%).
  - [x] Exposición de `status_tmdb` y `proximo_episodio_fecha` en `TitleCardResponse`.
- [x] **Paso 11.10: Consolidación de Modelo de Datos y Diagramas Vectoriales de Alta Legibilidad (v1.7.2):**
  - [x] Unificación del modelo de datos de producción en un único diagrama canónico (`docs/UML/modelo_datos/modelo_datos.mmd` y `docs/diagrams/modelo_datos.svg`), retirando las versiones disjuntas mínimas/superiores.
  - [x] Actualización de la máquina de estados de usuario (`docs/UML/estados/maquina_estados_usuario.mmd` y `docs/diagrams/maquina_estados_usuario.svg`) reflejando los guards de estreno en películas y series con 0 episodios emitidos.
  - [x] Actualización del diagrama de arquitectura del recomendador (`docs/UML/recomendador/arquitectura_recomendador_hibrido.mmd` y `docs/diagrams/recomendador_hibrido_arquitectura.svg`) con el slider UX de 5 niveles, modulación RAG de votos, exención de entidades, guardrail de inanición y Reasoning Dispatcher con tolerancia a fallos multiclave.
  - [x] Diseño infográfico en formato SVG vectorial nativo de alto contraste y legibilidad humana en modo oscuro.
- [x] **Paso 11.11: Localización Completa de Modales de Autenticación (v1.7.3):**
  - [x] Localización de `AuthModal.tsx` mediante `useLanguage` de `@/context/LanguageContext` para soporte dinámico español e inglés.
  - [x] Traducción completa de títulos, subtítulos, validaciones, etiquetas (labels), placeholders, botones submit y alternancia login/registro.
  - [x] Verificación de suite de tests en frontend (`vitest`) y build de producción con Vite.

---

## Próximas Fases y Backlog (Post-Entrega):

### Próximas Fases Priorizadas:
- [ ] **Fase 12: Sistema de Notificaciones In-App y Ciclo de Vida Reactivo de Series:**
  - Panel de notificaciones en Header (campana) ante anuncios de renovación, cancelaciones y fechas de estreno.
  - Reactivación automática de series en estado `vista` a `siguiendo` cuando se estrene una nueva temporada en TMDB.
  - Preferencias de alertas configurables en `/settings`.
- [ ] **Fase 13: Traducción de Contenidos y Selector de Idioma (I18n de Catálogo):**
  - Ingesta de traducciones de títulos y sinopsis de películas y series desde TMDB.
  - Traducción de nombres de temporada (si difieren) y nombres/sinopsis de episodios.
  - Prioridad para Español Latinoamericano (`es-MX` / `es-419`) y Español España (`es-ES`).
  - Sistema de fallback en cascada: variante regional $\rightarrow$ español alternativo $\rightarrow$ inglés (`en-US`) $\rightarrow$ idioma original.
  - Selector de idioma preferido de contenidos en `/settings`.
- [ ] **Fase 14: Plataformas de Streaming y Disponibilidad Multirregión (Watch Providers):**
  - Integración de TMDB Watch Providers / JustWatch con tablas `plataformas` y `disponibilidad_streaming`.
  - Detección de región por perfil o IP y filtros por servicios de streaming activos en Catálogo.

### Backlog (Pendientes sin Priorizar):
- [ ] Carrusel "Upcoming / Próximamente" en Home para obras con estreno confirmado en los próximos 30-90 días.
- [ ] Ampliación del modelo de datos: reparto de series por temporada, título específico de temporada y sinopsis enriquecida de episodios.
- [ ] Herramientas avanzadas en Biblioteca (`/library`): ordenamiento multidimensional, filtros por tipo/género, buscador in-place y paginación para colecciones grandes.
- [ ] Autenticación ampliada: campo `email` al registrarse y login social con Google OAuth.
- [ ] Badge visual "Viendo Actualmente" (🔥) con ventana de días configurable en `/settings`.
- [ ] Diálogo de confirmación al desmarcar episodios intermedios de una serie.
- [ ] PWA offline caching con Service Workers avanzados para fichas y biblioteca.
- [ ] Compartir listas y perfiles públicos mediante OpenGraph cards.






