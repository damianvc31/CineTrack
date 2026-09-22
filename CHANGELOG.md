# CHANGELOG.md — Registro de Cambios: CineTrack

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [v1.0.0] - 2026-09-21
### Agregado & Despliegue a Producción (Hito Final)
- **Infraestructura Cloud Desacoplada de Costo Cero:**
  - **Base de Datos Gestionada (Neon.tech PostgreSQL 16 Serverless):**
    - Despliegue en AWS Ohio con pooling nativo PgBouncer y cifrado SSL obligatorio.
    - Script de migración masiva por lotes (`backend/app/jobs/export_to_postgres.py`) para transferir el catálogo completo de desarrollo (3.851 títulos, 525.972 episodios, 29.777 actores, 8.935 reseñas) en menos de 4 minutos, con re-sincronización de secuencias e integridad referencial.
    - Configuración asíncrona de base de datos (`session.py`) adaptada para connection poolers y tolerancia a suspensión serverless (`statement_cache_size=0`, `pool_pre_ping=True`, `pool_recycle=300`).
  - **Backend API (Render.com Web Service):**
    - Despliegue automatizado con Blueprint declarativo (`render.yaml`) y runtime fijado en Python 3.12.8 (`backend/.python-version`).
    - Health check `/health` reportando estado operacional y versión de producción `1.0.0`.
    - Normalizador de cadenas de conexión en `config.py` para conversión transparente de esquemas (`postgres://` a `postgresql+asyncpg://`, `sslmode=require` a `ssl=require`) y sanitización regex de parámetros no soportados (`channel_binding=require`).
    - Validador flexible de orígenes CORS (`assemble_cors_origins`) para soportar listas JSON o dominios separados por coma.
  - **Frontend SPA (Vercel):**
    - Despliegue desacoplado en el edge con React 19, TypeScript y Vite.
    - Reglas de reescritura client-side en `frontend/vercel.json` para garantizar enrutamiento SPA sin errores 404 al recargar el navegador.
  - **Automatización Desacoplada (GitHub Actions):**
    - Workflow diario `.github/workflows/daily_sync.yml` programado a las 03:00 UTC (00:00 hora de Argentina) para actualización de cartelera y cambios de catálogo vía `POST /api/v1/admin/sync/daily`.
    - Workflow mensual `.github/workflows/monthly_actor_photos.yml` programado el primer día de cada mes a las 04:00 UTC para ingesta periódica de fotos de actores vía `POST /api/v1/admin/sync/actor-photos`.
- **Mejoras y Resiliencia en Ingesta de Datos:**
  - **Ingesta Masiva y Priorizada de Fotos de Actores (`populate_actor_photos.py`):**
    - Priorización automática de actores con roles destacados en los títulos de mayor popularidad del catálogo.
    - Soporte para ejecución sin límite (`limit=0` o `null`) y exposición como endpoint administrativo HTTP `POST /api/v1/admin/sync/actor-photos`.
    - Sincronización masiva de 25.116 fotos oficiales de actores en el catálogo de producción.
  - **Ampliación de Longitud de Personajes de Elenco:**
    - Expansión de columna `personaje` en `titulos_elenco` a `String(500)` para alojar roles múltiples y acreditaciones complejas sin truncamiento.
- **Ajustes de Catálogo y Reglas de Negocio:**
  - Ampliación del pool de clásicos en Home (`HOME_CLASSICS_POOL_SIZE = 100`) y elevación del umbral mínimo de votos en Top Rated a 500 (`HOME_TOP_RATED_MIN_VOTES = 500`).
  - Acotamiento estricto de la sección *Top Rated* en el catálogo (`/catalog?section=top_rated`) a los 100 títulos mejor calificados históricos (`HOME_TOP_RATED_POOL_SIZE = 100`), ordenados por puntuación unificada descendente.
  - Saneamiento de `docs/CATALOG_SPECS.md` retirando la sección residual "Others" para mantener alineación total con la experiencia en producción.

## [v0.9.4] - 2026-09-18
### Corregido & Mejorado
- **Perfil de Usuario: Ventana Temporal en Estadísticas y Rediseño de Siguiendo:**
  - **Filtro de Rango Temporal en Estadísticas (`time_window`):**
    - Selector interactivo con opciones: *Histórico* (`all_time`), *Último mes* (`1m`), *Últimos 3 meses* (`3m`), *Últimos 6 meses* (`6m`), *Último año* (`1y`), *Últimos 5 años* (`5y`) y *Últimos 10 años* (`10y`).
    - Soporte en backend en `GET /api/v1/users/me/stats` con filtrado dinámico sobre `visto_el` y `agregado_el` para recalcular horas totales, promedio semanal, temporadas completadas, distribución de géneros y top títulos del periodo.
    - Actualización reactiva con indicador de carga y soporte de internacionalización completa en español e inglés.
    - Cobertura con test unitario específico en `backend/tests/test_users.py`.
  - **Rediseño de Tarjetas "Siguiendo" en Perfil:**
    - Reemplazo del recorte panorámico deformado por tarjetas horizontales con póster vertical en proporción original 2:3 (`aspect-[2/3]`), garantizando nitidez de imagen, jerarquía estética y lectura clara del progreso de episodios.
- **Detalle de Título: Avatares de Elenco con Iniciales Robustas (`ActorAvatar`):**
  - Componente modular `ActorAvatar` con función generadora de iniciales completas (ej. *"RDJ"* para Robert Downey Jr., o dos caracteres para nombres simples) ante fotos faltantes o errores de red (`onError`), eliminando rupturas de layout.
- **Recomendador con IA: Resiliencia, Validación Determinista y Control de Flujo:**
  - **Detección Determinista de Texto Ininteligible (Validador de Entrada Local):**
    - Intercepción temprana sin consumo de cuota de LLMs para texto basura, teclado machacado, tokens mezclados y dígitos aislados.
    - Preservación total de consultas naturales legítimas que contienen números (décadas como *"los 80"*, secuelas como *"iron man 3"*, conteos como *"últimos 3 años"*, calificaciones como *"+8.5 estrellas"* y presets de catálogo).
  - **Cancelación Inmediata de Búsqueda ("Frenar búsqueda"):**
    - Desconexión del cliente con `AbortController` en el navegador y propagación en backend vía `http_request.is_disconnected()` para abortar la cascada de IA de inmediato sin gastar tokens.
    - Sincronización instantánea de estado y limpieza del parámetro `?prompt=` en la URL para evitar re-ejecuciones espurias.
  - **Clarificación y Experiencia de Usuario:**
    - Mensaje diferenciado para el validador local cuando se solicita aclaración (*"Consulta validada localmente por CineTrack para solicitar aclaración sin consumir cuota de IA"*), eliminando la confusión con caídas de los servicios de IA en la nube.
    - Limpieza automática del prompt previo no comprendido al pedir aclaración y reemplazo en tiempo real del prompt superior a medida que el usuario escribe o envía su aclaración.
    - Desacoplamiento de estados en `RecommendationsPage.tsx` eliminando dependencias volátiles en `executeRecommendation` y previniendo bucles infinitos con `searchParams`.
  - **Aislamiento de Sesión:**
    - Limpieza total de recomendaciones cacheadas, prompt y aborto de peticiones al iniciar o cerrar sesión desde cualquier punto de la aplicación.

## [v0.9.3] - 2026-09-17
### Rendimiento & Resiliencia
- **Optimización de Cuota y Cascada Jerárquica Multi-Nivel entre Proveedores:**
  - **Jerarquía de Ejecución:** Ante una consulta, el recomendador evalúa en estricto orden de calidad:
    1. Modelo insignia del proveedor primario (ej. Gemini `gemini-3.6-flash`).
    2. Modelo insignia del proveedor secundario (ej. Groq `openai/gpt-oss-120b`).
    3. Modelos de respaldo del proveedor primario (`gemini-flash-lite-latest`, `gemini-3.5-flash-lite`, `gemini-3.8-flash`).
    4. Modelos de respaldo del proveedor secundario (`openai/gpt-oss-20b`, `groq/compound-mini`, `qwen/qwen3.8-27b`).
    5. Motor heurístico determinista local offline si todos los servicios en la nube estuviesen caídos.
  - **Reducción del 70% en el Payload de Candidatos:** Parámetro `RECOMMENDATION_CANDIDATES_LIMIT` (default 20, antes 45 títulos rígidos). Reduce el prompt de ~5.500 a ~1.500 tokens, cuadruplicando la capacidad de consultas por minuto y multiplicando por 4 el rendimiento de la cuota diaria.
  - **Fallo Rápido sin Demoras:** Detección inmediata de 429 para pasar al siguiente modelo/proveedor sin reintentos redundantes.
  - **Configuración Completa en Entorno:** Nuevas variables `GEMINI_FALLBACK_MODELS` y `GROQ_FALLBACK_MODELS` configurables en `config.py`, `.env` y `.env.example`.

## [v0.9.2] - 2026-09-17
### Corregido & Mejorado
- **Afinidad Semántica y Búsqueda Temática Bilingüe en el Recomendador con IA:**
  - **Mapeo Temático Bilingüe (`THEME_EXPANSION_MAP`):** Mapeo exhaustivo de conceptos en español a terminología en inglés para sinopsis de TMDB (`planes`, `atracos`, `robos`, `estafas`, `asesinos en serie`, `espionaje`, `venganza`, `conspiraciones`, `viajes temporales`, etc.).
  - **Búsqueda Temática Combinada de Máxima Prioridad:** Consulta SQL optimizada en `catalog_service.get_recommendation_candidates` que cruza géneros detectados con coincidencias semánticas en la sinopsis (`Genero.nombre.in_(...) AND Titulo.sinopsis.ilike(...)`), posicionando títulos temáticamente idóneos (*Heat*, *The Usual Suspects*, *Nine Queens*, *Reservoir Dogs*, *Lock Stock*) en la cabecera del pool de candidatos en lugar de relleno de alta nota no relacionado.
  - **Piso de Votos para Relleno General:** Elevación del umbral mínimo a 150 votos en el relleno por género para evitar anomalías con pocos votos en las recomendaciones.
  - **Prevención de Contaminación de Perfil:** Se evita forzar los géneros históricos del usuario cuando este realiza una búsqueda temática específica con términos explícitos.
  - **Soporte Offline en Motor Heurístico:** Integración de `THEME_EXPANSION_MAP` en `_fallback_heuristic` para que la selección local offline también priorice afinidad temática real.
  - **Soporte de `only_watched` sin términos explícitos:** Asegurado el rescate directo de títulos del historial del usuario ante consultas como *"Recomiéndame de las que ya vi"*.

## [v0.9.1] - 2026-09-17
### Agregado & Mejorado
- **Job de Expansión de Catálogo por Géneros (Criterio 1):**
  - Nuevo método `expand_catalog_by_genres` en `TMDBSyncService` que utiliza `/discover` de TMDB con filtros de calidad y géneros específicos o totales.
  - Parámetros configurables en `Settings` y `.env` / `.env.example`:
    - `TMDB_EXPAND_MIN_VOTE_COUNT`: umbral mínimo de votos (default 300).
    - `TMDB_EXPAND_MIN_VOTE_AVERAGE`: umbral mínimo de calificación promedio (default 7.0).
    - `TMDB_EXPAND_TITLES_PER_GENRE`: objetivo de títulos por género (default 50).
  - Interfaz de comandos CLI enriquecida en `backend/app/jobs/sync_tmdb.py`:
    - `--expand`: flag para ejecutar la expansión.
    - `--genre`: filtro por género puntual (nombre o ID de TMDB); si se omite, itera sobre todos los géneros.
    - `--media-type`: `both` (default), `movie` o `tv`.
    - `--min-vote-count`, `--min-vote-average`, `--target-per-genre`: overrides configurables por CLI.
  - Endpoint administrativo `POST /api/v1/admin/sync/expand` con ejecución asíncrona mediante `BackgroundTasks` y esquema validado `ExpandCatalogRequest`.
  - Cobertura de tests unitarios completa en `backend/tests/test_tmdb_sync.py` y `backend/tests/test_admin.py` (8 tests de admin y 17 de sync pasando).

## [v0.9.0] - 2026-09-16
### Agregado & Mejorado
- **Fase 6: Recomendador Inteligente con IA (Cierre de la Versión Mínima / MVP):**
  - **Motor Híbrido Resiliente con Doble Fallback:**
    - Integración de Google Gemini 2.0 Flash (`gemini-2.0-flash`) como motor primario por velocidad y capacidad de razonamiento.
    - Conmutación automática por error a Groq API (`llama-3.3-70b-versatile`) ante demoras o límites de tasa (HTTP 429).
    - Motor heurístico determinista local de respaldo que entra en acción ante ausencia de claves o fallos de red, asegurando una disponibilidad del 100%.
  - **Grounding Estricto sobre el Catálogo de CineTrack:**
    - Selección previa de un pool de 30 a 45 títulos candidatos en PostgreSQL evaluando coincidencias temáticas, géneros, décadas, calificaciones de la comunidad y fragmentos de reseñas locales.
    - El LLM opera con prohibición estricta de alucinación y devuelve únicamente IDs validados del pool con formato JSON estructurado.
  - **Política de Resolución y Manejo de Incertidumbre:**
    - Ante consultas amplias o genéricas (*"sorpréndeme"*, *"algo bueno"*), el recomendador resuelve con confianza destacando las obras mejor valoradas.
    - Ante consultas específicas o de nicho, prioriza la concordancia temática sobre la nota masiva.
    - Ante entradas incomprensibles o contradictorias, responde con `clarification_needed` y ofrece sugerencias interactivas (*chips* accionables con un clic).
  - **Endpoint Backend e Hidratación Completa:**
    - `POST /api/v1/recommendations` con validación Pydantic v2, soporte para usuarios invitados y autenticados (con personalización por favoritos y vistos), e hidratación de tarjetas `TitleCardResponse`.
  - **Interfaz de Usuario Dedicada (`RecommendationsPage.tsx`):**
    - Pantalla accesible desde `/recommendations` con estética cinemática carbón/púrpura.
    - Acceso rápido desde el botón con chispa ✨ en la barra de navegación y en el menú móvil.
    - Integración con el buscador de IA de la Home mediante parámetros de URL (`?prompt=...`).
    - Disparadores rápidos (*presets* temáticos) y filtro por tipo de contenido (*Todos*, *Películas*, *Series*).
    - Renderizado de tarjetas `TitleCard` con cápsula explicativa inferior de la IA (*"Por qué te la recomendamos"*).
  - **Cobertura y Tests Automatizados:**
    - 5 nuevos tests unitarios en `backend/tests/test_recommendations.py` validando flujo con Gemini, conmutación por error a Groq, fallback heurístico determinista, clarificación de incertidumbre y filtrado por tipo (65 tests totales en backend pasando).

## [v0.8.6] - 2026-09-16
### Agregado & Mejorado
- **Refinamiento Integral de Frontend, Interacciones y UX:**
  - **Interacción y Retención Post-Clic en Favorito y Watchlist:** Supresión de inversión inmediata (`justToggledFav`, `justToggledWl`). Al hacer clic para marcar, el botón se rellena con su color correspondiente y permanece activo sin desrellenarse mientras el cursor siga encima; la animación de desrellenado se reactiva únicamente al retirar y reingresar el cursor.
  - **Comportamiento Dinámico y Reactivo de "Vista / No vista":**
    - En reposo muestra `"No vista"` / `<EyeOff />` cuando el título no está visto, e invierte dinámicamente en hover a `"Vista"` / `<Eye />` en verde esmeralda.
    - Cuando ya está visto, en hover previsualiza el desmarcado mostrando `<EyeOff />` en verde esmeralda en armonía con el botón, pasando al estado neutral gris únicamente al desmarcar y retirar el cursor.
    - Ancho mínimo estable (`min-w-[124px] justify-center`) para eliminar parpadeos de borde (*layout jitter*) producidos por la variación de longitud del texto.
  - **Carga Silenciosa en "Mi Biblioteca" (`LibraryPage.tsx`):**
    - Desacoplamiento de `loadLibrary` con parámetro de segundo plano (`isBackground = true`), evitando desmontar la grilla ni disparar el spinner animado de pantalla completa al interactuar con las tarjetas.
  - **Tag de Filtro por Actor en Catálogo (`CatalogPage.tsx`):**
    - Al navegar desde el reparto principal de un título (`?actor=...`), el catálogo muestra su respectivo chip interactivo en la barra de filtros activos con icono `<User />`, permitiendo descartar el filtro individualmente con `X` o en conjunto con *"Limpiar filtros"*.
  - **Ampliación de la Barra de Búsqueda del Catálogo:**
    - Redimensionamiento responsivo (`sm:w-96 md:w-[420px] lg:w-[460px]`) y tipografía `text-xs sm:text-sm`, asegurando que el placeholder completo (*"Buscar títulos, actores, directores, guionistas..."*) entre con holgura sin recortarse.
  - **Banderas SVG Twemoji y Desglose de Géneros:**
    - Integración de `<CountryFlag />` en el dropdown de países y chips activos para renderizar banderas en Windows sin depender de fuentes con soporte de emojis regionales.
    - Desglose interactivo de duplas de género en la pantalla de detalle (`Sci-Fi & Fantasy` navega al catálogo con `Sci-Fi` y `Fantasy` combinados con operador `OR`).
  - **Tooltips y Calificación Directa:**
    - Visualización directa del conteo de votos en el badge superior del póster (`★ 8.4 (1.2k)`).
    - Clarificación de la calificación unificada como proveniente de la comunidad (TMDB + CineTrack) y tooltip del percentil de popularidad.
    - Corrección de tooltips en el botón visto en tarjetas según el estado real (`isWatched`).
    - Unificación del término *"puntaje"* (reemplazando *"nota"*).

## [v0.8.5] - 2026-09-16
### Agregado & Mejorado
- **Refinamiento Integral de Home (`HomePage.tsx` y `catalog_service.py`):**
  - **Eliminación de Carruseles con Duplas de Series:** Se excluyeron del listado de carruseles de la Home las duplas híbridas de TMDB (`Action & Adventure`, `Sci-Fi & Fantasy`, `War & Politics`). En su lugar, los carruseles canónicos individuales (`Action`, `Adventure`, `Science Fiction`, `Fantasy`, `War`) expanden automáticamente sus consultas para consolidar películas y series de manera unificada y orgánica.
  - **Eliminación de la Sección "Más Descubrimientos" (`others`):** Se removió el carrusel de descubrimientos de la Home, su lógica de base de datos y su opción en el selector de filtros de `/catalog`, simplificando la interfaz y evitando títulos repetidos.
  - **Actualización Integral de Iconografía Vectorial (`lucide-react`):**
    - Tendencias: sustitución de `Flame` por `TrendingUp` 📈 (reservando el fuego exclusivamente para la métrica visual de popularidad).
    - Animación: composición artística superpuesta de paleta y pincel (`Palette` + `Paintbrush` 🎨🖌️).
    - Crimen: `PocketKnife` 🔪.
    - Documental: `CassetteTape` 📼.
    - Misterio: `Search` 🔍.
    - Suspenso: `Footprints` 👣.
    - Bélica: `Swords` ⚔️.
    - Western: `Sunset` 🏜️.
    - Infantil: `Baby` 👶.
    - Telenovelas: `Rose` 🌹.
    - Comedia: `Laugh` 😂.
    - Aventura: `Map` 🗺️.
    - Mapeo específico y estilizado para cada género del catálogo (`Users`, `ScrollText`, `Music`, `Heart`, `Rocket`, `Theater`, `Skull`, `Newspaper`, `Mic`, etc.).

## [v0.8.4] - 2026-09-16
### Agregado & Mejorado
- **Filtros Multiselección Avanzados en Catálogo (`/catalog`):**
  - **Filtro por País de Origen (`paises`):** Dropdown multiselección con lista dinámica de países con títulos en base de datos, conteos de disponibilidad y localización reactiva en el idioma de la interfaz mediante `Intl.DisplayNames`.
  - **Filtro por Idioma Original (`idiomas`):** Dropdown multiselección con lista dinámica de idiomas disponibles en el catálogo, conteos y nombres localizados.
  - **Multiselección de Géneros y Modo de Coincidencia (`generos` & `genre_op`):**
    - Soporte para seleccionar múltiples géneros simultáneamente.
    - Selector interactivo de lógica de coincidencia: **Cualquiera (OR)** (por defecto, muestra títulos que tengan al menos uno de los géneros seleccionados) o **Todos (AND)** (muestra únicamente títulos que contengan todos y cada uno de los géneros seleccionados).
  - **Normalización Canónica de Géneros TMDB:**
    - Se excluyeron del listado de selección las duplas híbridas de TMDB (`Action & Adventure`, `Sci-Fi & Fantasy`, `War & Politics`) que generaban confusión entre películas y series.
    - Expansión automática en backend: al seleccionar un género simple (ej. `Action`, `Sci-Fi` o `Fantasy`), el backend busca tanto la etiqueta de película como la correspondiente dupla de serie de televisión, logrando resultados coherentes en todo el catálogo.
  - **Componente Reutilizable `MultiSelectDropdown` (`MultiSelectDropdown.tsx`):**
    - Desplegable elegante con buscador interno en tiempo real para encontrar rápidamente países, idiomas o géneros.
    - Badges numéricos de selección, checkboxes visuales estilizados y botón de deselección rápida.
  - **Barra de Filtros Activos (Chips / Pills):**
    - Visualización de etiquetas removibles para cada filtro activo (término de búsqueda, tipo, sección, cada género con su indicador `(OR)` o `(AND)`, cada país y cada idioma).
    - Botón *"Limpiar todo"* para restablecer el catálogo a su vista base con un solo clic.
  - **Clarificación de Buscador Integral (Header y Catálogo):**
    - Actualización de placeholders en ambas barras de búsqueda (*"Buscar títulos, actores, directores, guionistas..."* / *"Search titles, actors, directors, writers..."*) clarificando la capacidad ya existente del motor de búsqueda de indexar títulos por nombre, actores, creadores, directores y guionistas. Actualizado en `ROADMAP.md` (cerrando la tarea correspondiente del backlog).
  - **Nuevos Endpoints en Backend (`/api/v1/titles`):**
    - `GET /api/v1/countries`: Devuelve la lista ordenada de códigos de país y conteo de títulos asociados en base de datos.
    - `GET /api/v1/languages`: Devuelve la lista de idiomas originales y cantidad de títulos.
    - Soporte de listas o strings separados por comas en `generos`, `paises` e `idiomas` en `GET /api/v1/titles`.
  - **Suite de Pruebas Automatizadas:**
    - Incorporación de 3 nuevos tests unitarios en `test_catalog.py` validando endpoints de metadatos, filtrado combinado y expansión canónica con switch `OR`/`AND`. Total 60 tests backend pasando al 100%.

## [v0.8.3] - 2026-09-16
### Agregado & Mejorado
- **Desacoplamiento de Series Seguidas en Sincronización Diaria (`tmdb_sync_service.py`):**
  - Se eliminó la restricción de que una serie deba estar seguida por algún usuario (`siguiendo`) para poder recibir actualizaciones. Ahora, cualquier serie del catálogo local se actualiza fielmente si TMDB reporta modificaciones en `/tv/changes` durante la ventana temporal configurada.
- **Parametrización Independiente de Ventanas de Tiempo (`sync_tmdb.py`, `admin.py`, `config.py`):**
  - Separación explícita de parámetros para evitar ambigüedades:
    - `changes_hours_window` (`--changes-hours`, default 48 hs): Ventana en horas hacia atrás para consultar cambios reportados por TMDB en series y películas locales (`/tv/changes` y `/movie/changes`). Soporta `0` para omitir completamente la consulta de cambios cuando solo se desean buscar nuevos estrenos.
    - `releases_days_window` (`--releases-days`, default 15 días): Ventana en días hacia atrás para descubrir nuevos estrenos calificados en cartelera de **películas y series** (`/discover/movie` y `/discover/tv`).
    - Soporte en CLI, API administrativa (`DailySyncRequest`) y variables de entorno (`TMDB_CHANGES_HOURS_WINDOW`, `TMDB_DAILY_SYNC_DAYS_WINDOW`).
- **Descubrimiento e Ingesta de Nuevas Series en Sincronización Diaria (`run_daily_sync`):**
  - Se extendió el paso de nuevos estrenos de la sincronización diaria para consultar tanto `/discover/movie` como `/discover/tv` durante la ventana de cartelera configurada.
  - Ahora las series que estrenan su primera temporada con popularidad $\ge$ 10.0 en los últimos $N$ días se descubren e ingestan automáticamente con todas sus temporadas y episodios.
  - La respuesta de sincronización diaria ahora devuelve detalladamente: `{"updated_series": X, "new_movies": Y, "new_series": Z}`.
- **Política y Filtrado de Títulos No Estrenados (`allow_unreleased`):**
  - Se introdujo el parámetro de control `allow_unreleased: bool = False` (por defecto `False`) en configuración (`TMDB_ALLOW_UNRELEASED`), `.env`, `.env.example`, CLI (`--allow-unreleased`), servicio (`TMDBSyncService`) y API administrativa (`/api/v1/admin/sync/*`).
  - **Películas:** Omitir guardado de películas con fecha de estreno futura (`fecha_estreno > today`) o sin fecha confirmada (`None`).
  - **Series:** Omitir guardado de series sin temporadas emitidas (`first_air_date > today` o con 0 temporadas con episodios estrenados).
  - **Descubrimiento:** Consulta a `/discover` con fecha tope de estreno (`primary_release_date.lte` / `first_air_date.lte` igual a la fecha de hoy).
- **Herramienta y Endpoint de Saneamiento de Catálogo (`cleanup_unreleased_titles`):**
  - Implementación de método de saneamiento que elimina títulos no estrenados y recalcula automáticamente percentiles de popularidad y ratings unificados.
  - Disponible vía CLI (`python -m app.jobs.sync_tmdb --cleanup-unreleased`) y endpoint administrativo (`POST /api/v1/admin/sync/cleanup-unreleased`).
  - Saneamiento ejecutado exitosamente en base de datos: 7 películas no estrenadas depuradas (5 con fechas futuras en 2026 y 2 sin fecha). 0 series afectadas (todas las 1003 series poseen al menos una temporada emitida).
- **Pruebas Exitosas de Sincronización Diaria en Desarrollo:**
  - Corrida inicial con ventana de cambios de 120 horas: 12 series locales actualizadas, 12 nuevas películas incorporadas.
  - Corrida con `--changes-hours 0` (omitiendo cambios ya aplicados) y ventana de 15 días: **26 nuevas series incorporadas** de cartelera reciente.
  - Estado final del catálogo: **1006 películas y 1029 series (2035 títulos en total, 0 títulos no estrenados)** con percentiles y ratings unificados recalculados.
- **Suite de Pruebas Automatizadas:**
  - Incorporación de tests unitarios para `allow_unreleased`, `new_series` y `cleanup_unreleased_titles` en `test_tmdb_sync.py`. 57 tests backend pasando al 100%.

## [v0.8.2] - 2026-09-12
### Corregido & Mejorado
- **Cálculo de Distribución de Géneros por Título Único (`catalog_service.py`):**
  - Se corrigió el cálculo de `genres_distribution` en estadísticas de usuario (`/users/me/stats`) para que compute **1 conteo por cada título único consumido** (películas vistas y series con episodios vistos o marcadas como vistas), en lugar de iterar por cada episodio individual de una serie. Esto evita que series de muchos episodios inflen artificialmente sus géneros en el gráfico Donut del perfil.
- **Alineación y Anclaje Central Fijo de Explorar y Búsqueda (`Header.tsx`):**
  - Se implementó un contenedor anclado al centro geométrico del header (`absolute left-1/2 -translate-x-1/2`) en desktop/tablet, fijando el botón *"Explore / Explorar"* y la barra de búsqueda exactamente en la misma coordenada horizontal en todas las rutas en que se muestran, eliminando los desplazamientos causados por las variaciones de ancho de los bloques laterales (logo TMDB a la izquierda y avatar/autenticación a la derecha).
  - Se mantiene la exclusión limpia del botón Explorar y del campo de búsqueda en la ruta `/catalog` (tanto en desktop como en mobile), permitiendo que la navegación en el catálogo opere sin redundancias con sus propios controles dedicados de filtrado y búsqueda.
- **Corrección de Colección y Filtro "More Discoveries / Más Descubrimientos" (`catalog_service.py` & `HomePage.tsx`):**
  - Se corrigió el filtrado de `section="others"` en el catálogo (`get_titles`) y en la página principal (`get_home_sections`) para que al consultar sin filtro de tipo (*All types* / Todos los tipos), se consoliden los títulos pertenecientes a géneros minoritarios por categoría (ej. series de géneros con menos de 10 series como *Western* —*Yellowstone*, *1883*, *1923*, *Cowboy Bebop*, etc.— y películas de géneros de nicho). Anteriormente, la suma combinada de películas y series elevaba el conteo total del género por encima de 10, provocando que la sección de descubrimientos quedara vacía (0 títulos) en *All types*.
  - Se tradujo y localizó reactivamente el título (`t('sectionOthers')`) y subtítulo del carrusel *"Más Descubrimientos"* en `HomePage.tsx`.

## [v0.8.1] - 2026-09-12
### Corregido & Mejorado
- **Restricción de Reseñas para Títulos No Vistos (`TitleDetailPage`):**
  - Se impide publicar una nueva reseña en películas o series que el usuario no haya marcado como vistas.
  - Mensaje amigable e informativo que indica que se debe marcar la película como vista o registrar al menos un episodio visto de la serie para poder dejar una reseña.
  - **Manejo de Caso Borde:** Si el usuario ya había escrito una reseña y posteriormente desmarca el título o episodios, la reseña se preserva intacta y puede ser consultada y editada sin restricciones. Si decide eliminarla, no podrá redactar una nueva a menos que vuelva a registrar progreso visto.
- **Corrección de Persistencia y Caché de Avatar de Usuario (`EditProfileModal` & `users.py`):**
  - **Eliminación del Error de URL Nativo de HTML5:** Se desvincula la ruta interna del servidor (`/api/v1/users/X/avatar`) del campo de texto de enlace directo, y se cambia el input a `type="text"`, evitando que el navegador bloquee el guardado del formulario con el mensaje nativo *"Please enter a URL"*.
  - **Corrección de Error "Tainted canvases may not be exported" al Re-encuadrar:** Al re-encuadrar un avatar previamente guardado en el servidor, `handleRecenter` descarga la imagen mediante `fetch` con modo CORS y la convierte a un `Data URL` local antes de montarla en el visor. De este modo, el elemento `<canvas>` nunca es marcado como contaminado (*tainted*) por el navegador y `toDataURL` se ejecuta sin bloqueos de seguridad. Se añadió además la cabecera `Access-Control-Allow-Origin: *` explícita en `GET /{user_id}/avatar` y el atributo `crossOrigin="anonymous"` en el visor interactivo.
  - **Sobrescritura Inmediata e Invalidación de Caché:** El endpoint de subida de avatar (`POST /api/v1/users/me/avatar`) incorpora un timestamp de versión (`?v=...`) y el endpoint de servicio binario (`GET /{user_id}/avatar`) aplica cabeceras estrictas `Cache-Control: no-cache, no-store, must-revalidate`, garantizando que cada nuevo recorte se refleje instantáneamente sin retener la imagen anterior en caché del navegador.
  - **Preservación de Avatar Binario en `PATCH /me`:** La actualización de perfil conserva el avatar binario local si no se ingresa una URL externa explícita, evitando que guardar datos de país, ciudad o bio elimine o sobreescriba accidentalmente la foto cargada.
- **Localización Exhaustiva al Español en Detalle de Título y Modal de Perfil:**
  - `TitleDetailPage`: Traducción completa reactiva de botones de acción (*"Favorito"*, *"Marcar Vista"* / *"Vista"*, *"Siguiendo"*, *"Abandonar Serie"*, *"Serie Abandonada"*, *"Reanudar / Seguir"*, *"Lista de seguimiento"*), tags (*"Película"*, *"Serie"*, *"Popularidad"*, *"votos"*), ficha técnica (*"Director"*, *"Creador"*, *"Guionista"*, *"País"*), badges de emisión (*"Finalizada"*, *"Cancelada"*, *"En Emisión"*, *"Renovada"*, *"Pendiente de Renovación"*), lista de episodios (*"Mostrar/Ocultar Episodios"*, *"Temporada Vista"*, *"Sin estrenar"*), formulario y tarjetas de reseñas.
  - `EditProfileModal`: Localización íntegra de encabezado, campos de formulario (*"Nombre de usuario (no se puede modificar)"*, *"País"*, *"Ciudad"*, *"Biografía / Sobre ti"*), botones (*"Subir de mi PC"*, *"Re-encuadrar"*, *"Volver a Default"*, *"Guardar Cambios"*) y mensajes de estado.

## [v0.8.0] - 2026-09-12
### Agregado & Mejorado
- **Barra de Progreso Segmentada por Temporada en Siguiendo (`SeasonProgressBar`):**
  - Segmentos visuales proporcionales por cada temporada con bordes redondeados y códigos de color según avance (`Completada`: dorado oscuro / `En progreso`: ámbar brillante / `Sin empezar`: carbón oscuro).
  - Regla estricta de cálculo sobre **episodios ya estrenados** (`fecha_estreno <= today`) para no penalizar el porcentaje por episodios futuros.
  - **Regla de Regresión a la Temporada Incompleta más Temprana:** Si se desmarca un episodio de una temporada previa, el texto de estado semántico retrocede a esa entrega (ej. `● S1 in progress` o `● S1 watchlist`) sin importar que existan temporadas posteriores vistas, garantizando precisión determinística.
  - Integración en tarjetas `TitleCard` (`LibraryPage` y `ProfilePage`).
- **Orden Cronológico Estricto en Biblioteca (`get_user_library`):**
  - Orden descendente por marca de tiempo: `favoritos` ordenados por `fecha_favorito DESC`; `watchlist`, `siguiendo` y `recientemente vistas` ordenados por `fecha_estado DESC`.
  - Actualización atómica de `fecha_estado` en `toggle_episode_watched` y `toggle_season_watched` para reposicionar la serie al tope de la lista al registrar progreso.
- **Pantalla Completa de Perfil de Usuario (`ProfilePage`) Fiel a `user-profile.png`:**
  - **Tarjeta de Identidad:** Avatar prominente (`w-32 h-32`), nombre de usuario, país, ciudad, biografía y botón de edición con lápiz.
  - **Modal de Edición de Perfil (`EditProfileModal`):** Permite actualizar biografía, país, ciudad y URL de avatar con vista previa instantánea. Nombre de usuario bloqueado (`read-only`).
  - **Métricas Destacadas (Números Dorados):** Total de horas vistas, promedio semanal de películas (`avg_movies_per_week`) y temporadas de series completadas (`seasons_completed_count`).
  - **Rankings Top 5:** Top 5 películas y series más vistas (con formato `Nombre · N seasons | AAAA-AAAA`), Top 5 por calificación propia con puntaje personal verificado (`⭐ X.X`) y Top 5 por popularidad corregido.
  - **Corrección de Métrica de Popularidad:** En lugar de exhibir la puntuación bruta no acotada de TMDB (`Titulo.popularidad` que causaba valores anómalos de 126% o 148%), ahora se utiliza rigurosamente el percentil poblacional normalizado (`Titulo.popularidad_percentil` normalizado al rango 0–100%), ordenando el ranking por percentil descendente para reflejar con precisión matemática el impacto del título en el catálogo (ej. Fauda 97%, Friends 95%, Landman 89%, MobLand 83%, The Godfather 77%).
  - **Gráfico Donut SVG de Géneros (`DonutGenreChart`):** Distribución proporcional de los géneros más consumidos con conteo central de títulos, leyenda interactiva y nombres traducidos reactivamente según el idioma activo.
  - **Sección Following y Listas Inferiores:** Fila completa dedicada a series en seguimiento con barras de progreso y pestañas inferiores para Favoritos, Watchlist y Vistos recientemente.
- **Sistema Global de Internacionalización y Localización Reactiva (`LanguageContext`):**
  - Creación de contexto global `LanguageProvider` y hook `useLanguage()` sincronizado bidireccionalmente con `localStorage`.
  - Diccionario integral `UI_STRINGS` en inglés y español que traduce dinámicamente cabecera, barra de búsqueda, navegación de cuenta desplegable, menú móvil, tabs de biblioteca, carruseles y panel lateral de Home, perfil de usuario y configuración, sin recargas de página ni modificaciones a la base de datos.
- **Pantalla Dedicada de Configuración (`/settings` - `SettingsPage`):**
  - Formulario seguro de cambio de contraseña con validación de contraseña actual y repetición de nueva clave (`POST /api/v1/users/me/change-password`).
  - Selector de preferencia de idioma de interfaz (English / Español) conectado reactivamente al contexto global y al diccionario de géneros (`genreTranslations.ts`).
- **Armonización Estética y UX Cinemática:**
  - `AuthModal` adaptado a paleta carbón/dorado con localización íntegra al inglés, soporte de modo inicial dinámico (`initialMode?: 'login' | 'register'`) y campos completos de perfil (país, ciudad, bio, avatar) durante el registro.
  - **Separación de Botones de Autenticación con Significado Propio:** Reemplazo de accesos ambiguos por dos botones diferenciados de **Log In** y **Sign Up / Create Account** (en cabecera desktop, menú móvil, panel lateral de Home y estados deslogueados de Library y Reviews), abriendo directamente el formulario correspondiente pero permitiendo la alternancia ágil entre inicio de sesión y registro dentro del modal.
  - Ampliación de avatares en Home (`w-14 h-14` / `w-16 h-16`), Header (`w-10 h-10`) y Perfil (`w-32 h-32`).
  - Menú desplegable de usuario y menú móvil con acceso directo a las 7 secciones clave de la biblioteca (Profile, Favorites, Watchlist, Watch History, Following, Reviews, Settings).
  - Notificaciones toast en inglés estricto en `ReviewsPage` y simplificación de etiqueta a "Favorites" en el panel lateral de Home.
- **Encuadre y Centrado Interactivo de Avatar desde la PC:**
  - Selector de archivo local desde la PC en `EditProfileModal` con soporte para formatos PNG, JPG y WebP.
  - Visor circular interactivo (200×200 px con aro dorado) con **arrastre con el mouse/touch**, escala de ajuste automático inicial (*contain*) y **slider de zoom-out y zoom-in (0.2x a 3.0x)** para alejar o acercar la toma con total libertad.
  - Botones de ajuste instantáneo: *"Ajustar Completa (1.0x)"*, *"Llenar Círculo"* y *"Centrar"*.
  - Renderizado en `<canvas>` a miniatura cuadrada de 256×256 px con fondo oscuro de respaldo (`#141414`), garantizando fidelidad matemática exacta al visor.
  - Botón y endpoint para **restablecer al avatar por defecto** (`DELETE /api/v1/users/me/avatar`), limpiando la foto personalizada y retornando al gradiente ámbar con la inicial del usuario.
  - Resolución canónica de avatares mediante `getAvatarUrl()` y proxy en `vite.config.ts`, previniendo que los avatares relativos generen círculos negros o errores 404. Fallback automático a la inicial ante cualquier fallo de carga.
- **Incorporación de Fotos de Actores y Sección Top Cast:**
  - Nueva columna `foto_url` en la tabla `actores` y schema `CastMemberResponse`.
  - Captura del `profile_path` oficial de TMDB (`https://image.tmdb.org/t/p/w185...`) en el servicio de sincronización (`tmdb_sync_service.py`).
  - Nuevo job asíncrono CLI `backend/app/jobs/populate_actor_photos.py` para consultar y enriquecer en lotes las fotos de los actores del catálogo local.
  - Sección visual **"Top Cast / Reparto Principal"** en `TitleDetailPage` con avatares circulares de actores, fotos oficiales, nombres, personajes y enlaces de filtrado hacia el catálogo.
  - **Reubicación:** El Reparto Principal se posiciona estratégicamente por encima de las Temporadas y Episodios en series, brindando acceso inmediato a los intérpretes antes de la lista detallada de entregas.
- **Localización Completa del Catálogo y Navegación "Explore / Explorar":**
  - Internacionalización reactiva de `CatalogPage` (`t()` y `translateGenreName()`): títulos, buscador, filtros por tipo, géneros dinámicos, secciones temáticas, opciones de ordenamiento, estado vacío y paginador.
  - Renombrado del botón y enlaces de navegación en cabecera desktop, móvil y páginas secundarias de "Catalog / Catálogo" a **"Explore / Explorar"**.
  - Localización de títulos de secciones secundarias en `TitleDetailPage` (Sinopsis, Temporadas y Episodios, botones de temporada, reseñas y alertas de éxito).
- **Supresión de Tooltips Nativos Blancos de Windows/Navegador:**
  - Sustitución de atributos `title="..."` por `aria-label="..."` en elementos con tooltips personalizados (`TitleCard`, Top 5 de `ProfilePage`, tarjetas de póster y cuadrícula de actores), evitando la superposición del tooltip rectangular blanco del sistema operativo.
  - Actualización del modelo UML de datos (`docs/UML/modelo_datos/uml_version_minima.mmd` y `uml_version_superior.mmd`).
- **Corrección de Layout y Animaciones en Gráfico Donut de Géneros (`DonutGenreChart`):**
  - Rediseño de la leyenda a una columna vertical limpia con truncado inteligente (`truncate`), evitando que los nombres compuestos en español colisionen o se superpongan con los conteos y porcentajes.
  - Conservación de animaciones fluidas con SVG: resaltado dinámico con *glow* al pasar el mouse por arcos o leyenda, atenuación de los demás sectores y centro dinámico interactivo con porcentaje, nombre completo y cantidad de títulos.
- **Tooltips Flotantes Instantáneos en Listas de Perfil:**
  - Inclusión de tooltips instantáneos (`group-hover/rank` y `group-hover/pcard`) en los rankings Top 5 (Popularidad, Calificación Promedio, Calificación Propia) y en las listas inferiores (Favoritos, Watchlist, Vistos Recientemente) para desplegar el título completo sin esperar el retardo del navegador.
- **Suite de Pruebas Automatizadas:** 54 tests en backend pasando (`pytest`) incluyendo prueba unitaria de subida y servicio de avatar (`test_upload_and_get_avatar`), y suite de frontend en Vitest en verde.

## [v0.7.4] - 2026-09-12
### Agregado & Mejorado
- **Sincronización de Temporadas Confirmadas (con o sin fecha):** `upsert_series` y el nuevo job `repopulate_seasons` ahora persisten temporadas futuras confirmadas en TMDB (incluso si tienen 0 episodios en TMDB al momento). Se procesaron las 1002 series del catálogo incorporando 180 nuevas temporadas confirmadas y actualizando 436 fechas de emisión.
- **Insignias Semánticas de Emisión en 6 Estados:** En la cabecera de `TitleDetailPage`, las series cuentan con un badge de estado de alta precisión:
  - 🟢 **Currently Airing:** Temporada en curso con episodios emitidos y próximos episodios (`Next ep on {date}`).
  - 🔵 **Renewed (con fecha):** Temporada confirmada con fecha futura programada (`Season {N} on {date}`).
  - 🟣 **Renewed (TBA / In Production):** Temporada confirmada por productora / TMDB sin fecha exacta de estreno cargada todavía (ej. *Landman Season 3*, *House of the Dragon Season 3*).
  - 🟡 **Pending Renewal (Between Seasons):** Series en pausa donde concluyeron los episodios actuales y no hay registro de renovación aún.
  - ⚪ **Ended:** Serie finalizada oficialmente.
  - 🔴 **Canceled:** Serie cancelada.
- **Regla Visual para Temporadas Futuras en Detalle:** Las temporadas sin fecha confirmada y sin episodios aún no saturan el selector de temporadas ni el acordeón; solo se exponen en los tabs/selectores aquellas temporadas que ya tienen episodios o una fecha de estreno certera.
- **Localización Completa al Inglés en UI:** Localización íntegra al idioma inglés de todos los textos, menús y acciones restantes en `TitleDetailPage`, tarjetas `TitleCard`, pie de página `Footer`, biblioteca `LibraryPage` y perfil `ProfilePage`.

## [v0.7.3] - 2026-09-12
### Agregado & Mejorado
- **Modelo de Estado 'Abandonada' Deducido (Invariante Zero-Redundancy):** Al presionar *Abandonar* (`POST /api/v1/titles/{id}/unfollow`), la serie pasa limpiamente a `SinEstado` (`estado = null` en BD) manteniendo intacto su historial de episodios vistos en `EpisodioVisto`. El estado de "abandonada" se deduce de manera pura y reactiva (`estado == null && episodios_vistos > 0`).
- **Nuevo Endpoint de Reanudación Directa (`POST /api/v1/titles/{id}/follow`):** Permite retomar de inmediato el seguimiento de una serie que tenga episodios vistos previos, transicionándola a `siguiendo` sin forzar la alteración del checklist de episodios.
- **Botón 'Reanudar / Follow' en Detalle:** En la pantalla de detalle (`TitleDetailPage`), las series con progreso pero sin seguimiento activo muestran la insignia `Serie Abandonada` junto al botón interactivo con ícono `Play` para reanudarlas con un solo clic.
- **Icono de Serie Abandonada en Tarjetas (`TitleCard`):** En las tarjetas de títulos (Home, Catálogo, etc.), las series abandonadas ocultan la acción de Watchlist y despliegan en su lugar un ícono distintivo (`X` roja con tooltip explicativo), manteniendo total consistencia visual y guiando al usuario a ingresar para reanudar.
- **Detección Estructural del Estado de Emisión de Series:** Sustitución de heurísticas rígidas por detección reactiva basada en el progreso real de la temporada: si una temporada tiene episodios ya emitidos y episodios futuros pendientes se clasifica como **Currently Airing** (con fecha del próximo episodio); si la temporada concluyó pero hay una nueva entrega en calendario se exhibe como **Renewed** (indicando temporada y fecha de estreno); si concluyó y aún no hay fecha cargada se muestra con precisión como **On Hiatus (Between Seasons)**, reservando **Ended** y **Canceled** para sus estados terminales correspondientes.
- **Internacionalización Completa al Inglés en UI:** Localización íntegra al idioma inglés de todos los textos, menús y acciones restantes en `TitleDetailPage` (botones de acción *Favorite, Watched / Mark Watched, Following, Drop Series, Dropped Series, Resume / Follow*, cabeceras de sección *Synopsis, Top Cast*, estados de temporada y emisión de episodios *Season Watched, Mark Entire Season, Unreleased, Air Date*), tarjetas `TitleCard`, pie de página `Footer`, biblioteca `LibraryPage` y perfil `ProfilePage`.
- **Suite de Pruebas Automatizadas:** 50 tests pasando en backend (`pytest`), cubriendo el ciclo completo de abandono, reanudación y validaciones de borde, y tests de frontend en `vitest` actualizados al inglés.
- **Actualización de Especificaciones de Catálogo (`CATALOG_SPECS.md`):** New Releases formalizado a los últimos 30 días y Trending con popularidad mínima de 80%.

## [v0.7.2] - 2026-09-12
### Agregado & Mejorado
- **Inclusión de Series en Progreso y Abandonadas en Reseñas Pendientes:** Se expandió el filtro de `GET /api/v1/users/me/unreviewed-watched` para incluir series con estado `siguiendo` (con al menos un episodio visto) o `abandonada`, permitiendo que el usuario pueda evaluar y reseñar series que comenzó a ver aunque no las haya concluido en su totalidad.
- **Insignias de Estado en Reseñas Pendientes:** En la pestaña *"Pending Reviews"* de [ReviewsPage](file:///d:/Documentos/Cursos/UTN_E-Learning_IA-para-Programadores/Proyectos/CineTrack/frontend/src/pages/ReviewsPage.tsx), se identifican claramente los títulos con badges contextuales (`Watching`, `Completed`, `Dropped`).
- **Prueba Unitaria Automatizada:** Incorporación de paso de verificación en `backend/tests/test_reviews.py` que comprueba que marcar un solo episodio de una serie la habilita inmediatamente en el listado de pendientes de reseña.

## [v0.7.1] - 2026-09-12
### Corregido & Mejorado
- **Ocultamiento de Watchlist en Películas Vistas:** El botón de Watchlist ahora se oculta de forma coherente cuando una película ya está marcada como `vista` (tanto en la ficha de detalle [TitleDetailPage](file:///d:/Documentos/Cursos/UTN_E-Learning_IA-para-Programadores/Proyectos/CineTrack/frontend/src/pages/TitleDetailPage.tsx) como en las tarjetas [TitleCard](file:///d:/Documentos/Cursos/UTN_E-Learning_IA-para-Programadores/Proyectos/CineTrack/frontend/src/components/common/TitleCard.tsx)).
- **Scroll Automático al Inicio en Detalle:** Al navegar hacia la ficha de cualquier título, el scroll de la ventana se reposiciona inmediatamente arriba del todo (`window.scrollTo({ top: 0, behavior: 'instant' })`).
- **Ajuste Tipográfico en Tarjetas:** Optimización del ancho flexible (`min-w-0 flex-1`) y tamaño de fuente (`text-[10px] tracking-tight`) en el metadato de año y temporadas para que rangos largos (ej. `5 seasons | 2008-2013`) entren fluidamente junto a la bandera sin truncarse prematuramente.
- **Colapso Rápido de Episodios:** Botón toggle *"Hide Episodes / Show Episodes"* en la cabecera de temporadas de series, permitiendo plegar la lista de episodios para saltar directamente a la sección de reseñas y comentarios sin scrollear extensamente.

## [v0.7.0] - 2026-09-12
### Agregado
- **Motor Integral de Reseñas y Calificaciones (Fase 2):**
  - **Regla de 1 Reseña por Usuario por Título:** Si el usuario autenticado ya escribió una reseña para un título, en la pantalla de detalle (`TitleDetailPage`) se muestra su reseña destacada con botones para editar (lápiz) o eliminar (tacho de basura), impidiendo crear múltiples reseñas duplicadas.
  - **Calificación Decimal en Saltos de 0.5 (0.0 a 10.0):** Validador Pydantic estricto en `ReviewCreate` que solo permite múltiplos de 0.5 (`0.0, 0.5, 1.0, ..., 10.0`) para calificaciones de CineTrack. Las notas nativas de TMDB se importan y muestran tal cual, sin forzarlas ni bloquearlas.
  - **Puntaje Opcional (`puntaje = None`):** Checkbox interactivo en el formulario que permite dejar únicamente una reseña textual sin calificar. Las reseñas sin puntaje no interfieren ni alteran el promedio ponderado del `rating_unificado`.
  - **Endpoint de Eliminación y Recálculo:** Nuevo endpoint `DELETE /api/v1/titles/{title_id}/reviews` que borra la reseña propia y recalcula atómicamente el `rating_unificado` del título.
  - **Endpoints de Reseñas de Usuario:**
    - `GET /api/v1/users/me/reviews`: Lista paginada con metadatos del título (nombre, póster, tipo, año) y reseña del usuario.
    - `GET /api/v1/users/me/unreviewed-watched`: Lista de títulos marcados como vistos (`vista`) que aún no cuentan con reseña del usuario.
  - **Pantalla Dedicada `/reviews` (`ReviewsPage`):**
    - Pestaña *"My Reviews"*: Administración centralizada de todas las reseñas redactadas por el usuario, con soporte de edición inline, eliminación y paginación.
    - Pestaña *"Pending Reviews"*: Catálogo de títulos vistos pendientes de reseña con redactor rápido e instantáneo in-place.
  - **Distingo Visual de Fuentes:** Insignia oficial `TMDB Review` en bordes dorados para reseñas importadas de The Movie Database, y avatar con iniciales para opiniones de la comunidad CineTrack.
  - **Control de Paginación Progresiva:** Botón "Load more reviews" para títulos con un alto volumen de reseñas públicas.
  - **Pruebas Automatizadas:** 3 tests dedicados en `backend/tests/test_reviews.py` cubriendo validación de saltos de 0.5, upsert, eliminación con recálculo de rating unificado, reseñas sin puntaje y títulos pendientes de reseña (49 tests totales pasando en verde en backend, suite de frontend en Vitest pasando).

## [v0.6.0] - 2026-09-12
### Agregado
- **Alineación Visual y Estructural con Wireframes de Figma AI (`home-logged.png`, `series-detail.png`):**
  - Paleta cinematográfica en negro carbón puro (`#0d0d0d`), paneles y superficies en `#141414` con bordes `#262626`, y acentos cálidos dorado/ámbar (`#f59e0b` / `#eab308`).
  - Distribución de Home en 3 columnas: columna izquierda con widget interactivo de Asistente IA (sticky en desktop), columna central con selector rápido y carruseles curados, y columna derecha con panel personal de accesos rápidos del usuario.
  - Unificación completa de la interfaz de usuario al idioma inglés (*Trending Now, New Releases, Classics, Top Rated, AI Assistant, Explore, Favorites & Lists, Watchlist, Watch History, Following, Reviews, Settings, Sign Out*).
  - Banderita de país en todas las tarjetas (`TitleCard`) y en la ficha de detalle (`TitleDetailPage`) con componente `<CountryFlag />` (imagen nítida y fallback automático a emoji unicode).
  - Nombres completos de país (ej. `United States`, `Argentina`) e idioma original (ej. `English`, `Español`) en la ficha técnica generados mediante `Intl.DisplayNames`.
  - Manejo seguro de datos nulos y duración de 0 minutos, mostrando guión (`-`) en películas y episodios en lugar de imprimir un 0 numérico literal.
  - Botón de limpieza rápida `X` en todos los inputs de búsqueda (Header y `/catalog`).
  - Logotipo oficial de CineTrack (claqueta cinematográfica negra y dorada) como favicon del navegador y en el encabezado global.
  - Selector de temporadas híbrido en detalle de series: pestañas individuales si hay $\le 5$ temporadas y combobox desplegable estilizado si supera las 5 temporadas.
  - Configuración normalizada en backend: `HOME_TRENDING_MIN_POPULARITY_PERCENTILE = 0.80` (con fallback a top 10) y `HOME_NEW_RELEASES_DAYS = 30` en `config.py`, `.env` y `.env.example`.
  - Preservación de títulos vistos en las secciones de Home para evitar que usuarios activos vacíen o desvirtúen los carruseles.
  - Corrección de subquery para sección `others` en `catalog_service.py` filtrando por `tipo` de producción.
- **Atribución oficial obligatoria de TMDB (Términos de Uso, Cláusula 3):**
  - Monograma vectorial `Alt short (blue)` en SVG con degradé corporativo (`#90cea1` -> `#01b4e4`) ubicado en `Header` y `Footer`.
  - Píldora *"Powered by TMDB"* con enlace en barra superior.
  - Leyenda legal requerida en Footer: *"This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB."*
- **Soporte Mobile & PWA:**
  - `manifest.json` y meta tags para instalación directa en teléfonos (`standalone`, `theme-color: #0d0d0d`).
  - Diseño 100% responsive con breakpoints fluidos desde 360px hasta 4K.
- **Pruebas Automatizadas:**
  - Suite de 46 pruebas en backend (`pytest`) y tests unitarios de frontend en `vitest` (100% pasando).

## [v0.5.4] - 2026-09-12
### Agregado
- Exposición de `popularidad_percentil` en los esquemas `TitleCardResponse` y `TitleDetailResponse` para alimentar el badge visual de popularidad (🔥 xx%) en las tarjetas de la UI.
- Separación ortogonal de parámetros en `GET /api/v1/titles`:
  - `section`: Filtro de colección curada (`new_releases`, `trending`, `classics`, `top_rated`, `others`).
  - `sort_by`: Criterio puro de ordenamiento (`popularity`, `rating`, `release_date`, `title`).
  - `order`: Dirección del ordenamiento (`desc` por defecto, `asc`).
- Soporte para filtrado por nombres en texto (strings) además de IDs:
  - `genero`: Nombre de género insensible a mayúsculas (ej. `Drama`, `Fantasy`, `Comedy`).
  - `actor`: Nombre de actor del elenco (ej. `DiCaprio`, `Tom Cruise`).
  - `actor_id`: Identificador numérico de actor para navegación directa desde fichas de reparto.
- Búsqueda abierta por texto (`q`) extendida para buscar coincidencias tanto en título, director y guionista como en actores del elenco.

### Modificado
- Robustez en cálculo de Trending para series: ahora evalúa la fecha de emisión del último episodio real emitido (`MAX(Episodio.fecha_estreno)`), evitando falsos positivos con temporadas futuras sin episodios.
- Persistencia de `fecha_estreno` en el modelo `Temporada` durante la sincronización TMDB y backfill en base de datos (`cinetrack.db`) para 7.481 temporadas.
- Depuración de 181 temporadas vacías (placeholders sin episodios emitidos) en catálogo local y regla de omisión automática en `upsert_series`.

## [v0.5.3] - 2026-09-12
### Modificado
- Restricción de unicidad de TMDB convertida a clave candidata compuesta: `UNIQUE (tmdb_id, tipo)` en la tabla `titulos`, permitiendo que películas y series con el mismo identificador de TMDB (ej. *The Lord of the Rings: The Two Towers* y *Doctor Who*, ambas ID 121) coexistan sin colisiones.
- Migración de base de datos Alembic `0004_composite_tmdb_id_tipo.py`.
- Test unitario automatizado `test_pelicula_y_serie_mismo_tmdb_id` en `test_models.py` (suite total ampliada a 45 tests, 100% pasando en verde en < 5s).

## [v0.5.2] - 2026-09-12
### Agregado
- Endpoint administrativo de vaciado `DELETE /api/v1/admin/catalog?confirm=true` y opción CLI `python -m app.jobs.sync_tmdb --clear` con limpieza en cascada (títulos, temporadas, episodios, reseñas, estados y actores huérfanos) preservando usuarios y catálogo de géneros.

## [v0.5.1] - 2026-09-12
### Modificado
- Migración de columnas de año a fechas exactas (`Date`): `fecha_estreno` y `fecha_fin` en el modelo `Titulo` (manteniendo propiedades `@property anio_estreno` y `@property anio_fin` con setters para compatibilidad completa).
- Migración de base de datos Alembic `0003_dates_and_home_specs.py`.
- Refactorización de la lógica del catálogo de inicio (`/api/v1/home`):
  - **New Releases:** títulos estrenados en los últimos 60 días (configurable).
  - **Trending:** títulos de los últimos 90 días por popularidad, considerando la fecha de la última temporada para series de TV.
  - **Classics:** exclusivamente películas con más de 20 años de antigüedad, rating $\ge 7.5$ y $\ge 500$ votos; muestra aleatoria de un pool de 50 títulos (omitido cuando se filtra por `tipo=tv`).
  - **Top Rated:** muestra aleatoria de las mejores calificadas con al menos 100 votos (pool de 100).
  - **By Genre y Others:** carruseles individuales para géneros con $\ge 10$ títulos; géneros minoritarios con $< 10$ títulos agrupados en la sección `others`.
  - **Exclusión de Vistos:** omisión automática de títulos marcados con estado `vista` para usuarios autenticados en todas las secciones exploratorias de Home.
- Documentación en `README.md`: sección de comandos de migraciones Alembic (`upgrade`, `current`, `history`, `revision`, `downgrade`).
- Optimización de pruebas en `test_admin.py`: mock de `BackgroundTasks.add_task` previniendo disparos de workers reales a TMDB durante pruebas de API; la suite completa de 42 tests corre en menos de 5 segundos.

## [v0.5.0] - 2026-09-12
### Agregado
- Endpoints de Catálogo y Home (`/api/v1/home`, `/api/v1/titles`, `/api/v1/titles/{id}`, `/api/v1/genres`) con soporte para filtros por tipo, género, búsqueda por texto, ordenamiento y paginación.
- Endpoints de Reseñas (`GET /api/v1/titles/{id}/reviews` y `POST /api/v1/titles/{id}/reviews`) con creación de reseñas de usuario y recálculo automático de `rating_unificado`.
- Endpoints de Perfil y Biblioteca (`GET /api/v1/users/me/library` y `GET /api/v1/users/me/stats`) con cálculo de horas vistas, distribución de géneros y rankings Top 5 según wireframes.
- Esquemas Pydantic v2 en `backend/app/schemas/catalog.py` y capa de servicios `backend/app/services/catalog_service.py`.
- Suite ampliada a 40 tests unitarios e integración (100% pasando en verde).

## [v0.4.3] - 2026-09-11
### Agregado
- Router administrativo `/api/v1/admin/sync` para ejecutar jobs en segundo plano con `BackgroundTasks` de FastAPI (`HTTP 202 Accepted`): `/initial`, `/daily`, `/genres`, `/percentiles`, `/reviews`, `/import-tmdb` e `/import-json`, con soporte completo para todos los parámetros de configuración.
- Autenticación dual administrativa: soporte para JWT de usuario administrador (`es_admin=True`) y cabecera `X-Admin-Key` validada contra `ADMIN_API_KEY`.
- Columna indexada y persistida `rating_unificado` en modelo `Titulo` con recálculo automático ponderado de TMDB y reseñas locales (`recalculate_unified_ratings`).
- Enriquecimiento de la tabla asociativa `titulos_elenco` con columnas `personaje` y `orden`, vinculada mediante el modelo relacional `TituloElenco`.
- Parametrización en configuración de la ventana horaria para cambios en TMDB (`TMDB_CHANGES_HOURS_WINDOW`, default 48 horas) y configuración `TMDB_LANGUAGE` (default `en-US`).
- Endpoints semánticos para tracking de series y temporadas:
  - `POST /titles/{title_id}/seasons/{season_number}/episodes/{episode_number}/watch`: marcar/desmarcar episodio por numeración semántica (ej. S01E02).
  - `POST /seasons/{season_id}/watch` y `POST /titles/{title_id}/seasons/{season_number}/watch`: marcar/desmarcar temporada completa en lote con recálculo automático del estado de la serie.
- Migración Alembic `0002_technical_adjustments.py` y suite de tests ampliada a 35 tests automatizados (100% pasando en verde).
- Actualización de diagramas UML en `docs/UML/modelo_datos/`.

## [v0.4.2] - 2026-09-05
### Agregado
- Integración proactiva de los endpoints `/tv/changes` y `/movie/changes` en `run_daily_sync`: detección automática de series con nuevos episodios o cambio de estado emitidos en las últimas 48h (incluso si ningún usuario las sigue aún) y actualización de películas del catálogo local con mínimo consumo de cuota de API.
- Especificación formal y matemática de la fórmula de calificación unificada en `README.md` y `ARCHITECTURE.md`.
- Test unitario de integración `test_daily_sync_updates_untracked_titles_from_changes` comprobando la actualización autónoma de títulos locales no seguidos mediante `/changes`.

## [v0.4.1] - 2026-09-05
### Agregado
- Sincronización de reseñas externas de TMDB con límite configurable (`TMDB_REVIEWS_PER_TITLE_LIMIT = 20`) por título en `TMDBSyncService.sync_reviews_for_title` y `sync_all_missing_reviews`.
- Comando CLI dedicado `python -m app.jobs.sync_tmdb --reviews` para backfill y actualización desatendida de reseñas.
- Definición de política de autor polimórfico en reseñas de TMDB (exclusivamente contexto descriptivo sin alterar votos agregados de TMDB).

## [v0.4.0] - 2026-09-05
### Agregado
- Cliente asíncrono para la API de TMDB (`TMDBClient`) en `backend/app/services/tmdb_client.py` con `httpx`, autenticación Bearer Token v4 / api_key v3, semáforo de concurrencia y reintentos exponenciales.
- Servicio de ingesta y sincronización (`TMDBSyncService`) en `backend/app/services/tmdb_sync_service.py`:
  - Sincronización idempotente del catálogo de géneros (películas y series).
  - Ingesta inicial parametrizable con cuotas configurables (`TMDB_INGEST_MOVIES_TARGET`, `TMDB_INGEST_SERIES_TARGET`, defaults 1000 títulos).
  - Switch configurable de estrategia de ingesta: `popular_first` (tendencias primero y resto top-rated) o `toprated_first` (clásicos históricos primero y resto tendencias).
  - Enriquecimiento de directores, guionistas (hasta 3) y elenco (hasta 15 actores principales ordenados por créditos).
  - Ingesta estructurada de temporadas y episodios para series con mapeo de `anio_fin` desde `last_air_date` para producciones finalizadas o canceladas.
  - Sincronización diaria: refresco de series en seguimiento (`siguiendo`), absorción de nuevos episodios e ingesta de estrenos calificados dentro de una ventana de 15 días con popularidad >= 10.0.
  - Soporte de importación manual mediante JSON (`docs/templates/`) con resolución inteligente obligatoria de ID de TMDB por título/año (rechazando títulos huérfanos sin respaldo en la API para garantizar sincronización futura).
  - Motor de recálculo de percentiles de popularidad con ventana analítica SQL `PERCENT_RANK()` y fallback en memoria.
- Interfaz CLI ejecutable en `backend/app/jobs/sync_tmdb.py` para correr tareas manuales o cron jobs (`--genres`, `--initial`, `--priority`, `--daily`, `--percentiles`, `--reviews`, `--import-json`, `--import-tmdb-id`).
- Plantillas JSON de muestra documentadas en `docs/templates/template_pelicula.json` y `docs/templates/template_serie.json`.
- Fixtures sintéticas y suite de pruebas unitarias/integración con mocks en `backend/tests/test_tmdb_sync.py` (8 tests de TMDB, 24/24 tests pasando en verde en backend con cero gasto de cuota de API).

## [v0.3.0] - 2026-09-05
### Agregado
- Módulo de seguridad con hashing de contraseñas (`bcrypt`) y tokens JWT (`pyjwt`) firmado con `AUTH_SECRET_KEY` en `backend/app/core/security.py`.
- Endpoints de autenticación en `backend/app/api/v1/auth.py` (`POST /register`, `POST /login`, `GET /me`) y dependencia de seguridad `get_current_user`.
- Esquemas Pydantic v2 para autenticación y estados en `backend/app/schemas/`.
- Motor transaccional de estados de título en `backend/app/services/state_service.py` con soporte completo de transiciones para películas y series:
  - Toggle de Favorito (ortogonal).
  - Watchlist con bloqueo estricto (400) si el título está en Vista o Siguiendo.
  - Visto con limpieza de episodios asociados al desmarcar serie completa.
  - Abandonar serie (❌) conservando episodios vistos.
  - Seguimiento granular por episodio con recálculo automático de estado de serie y bloqueo de episodios futuros.
- Endpoints de estados en `backend/app/api/v1/states.py` (`/titles/{id}/favorite`, `/titles/{id}/watchlist`, `/titles/{id}/watched`, `/titles/{id}/unfollow`, `/titles/{id}/user-state`, `/episodes/{id}/watch`).
- Suite exhaustiva de pruebas en `backend/tests/test_auth.py` y `backend/tests/test_state_machine.py` (16 tests totales en verde).

## [v0.2.0] - 2026-09-05
### Agregado
- Modelos relacionales declarativos con SQLAlchemy 2.0 async en `backend/app/models/` (`Usuario`, `Titulo`, `Genero`, `Actor`, `Temporada`, `Episodio`, `EstadoUsuarioTitulo`, `EpisodioVisto`, `Resena`).
- Infraestructura de conexión y sesión asíncrona en `backend/app/db/` (`base.py`, `session.py`).
- Configuración de migraciones asíncronas con Alembic y primera migración de esquema `0001_initial_schema.py`.
- Suite exhaustiva de pruebas de modelos e integridad referencial en `backend/tests/test_models.py` (7 tests en verde).
- Integración de fixture de base de datos aislada en memoria con SQLite async (`aiosqlite`) para testing automatizado sin dependencias externas activas.

## [v0.1.0] - 2026-09-05
### Agregado
- Evaluación crítica de arquitectura aprobada y consolidada en `ARCHITECTURE.md`.
- Scaffolding base del backend con FastAPI (`backend/`).
- Suite de pruebas del backend con Pytest y smoke test inicial de salud en verde.
- Scaffolding base del frontend con Vite + React + TypeScript + Tailwind CSS (`frontend/`).
- Suite de pruebas del frontend con Vitest y smoke test inicial en verde.
- Documentación viva del proyecto (`README.md`, `TASK_PLAN.md`, `ROADMAP.md`).
