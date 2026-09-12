# CHANGELOG.md — Registro de Cambios: CineTrack

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [v0.8.1] - 2026-09-12
### Corregido & Mejorado
- **Restricción de Reseñas para Títulos No Vistos (`TitleDetailPage`):**
  - Se impide publicar una nueva reseña en películas o series que el usuario no haya marcado como vistas.
  - Mensaje amigable e informativo que indica que se debe marcar la película como vista o registrar al menos un episodio visto de la serie para poder dejar una reseña.
  - **Manejo de Caso Borde:** Si el usuario ya había escrito una reseña y posteriormente desmarca el título o episodios, la reseña se preserva intacta y puede ser consultada y editada sin restricciones. Si decide eliminarla, no podrá redactar una nueva a menos que vuelva a registrar progreso visto.
- **Corrección de Persistencia y Caché de Avatar de Usuario (`EditProfileModal` & `users.py`):**
  - **Eliminación del Error de URL Nativo de HTML5:** Se desvincula la ruta interna del servidor (`/api/v1/users/X/avatar`) del campo de texto de enlace directo, y se cambia el input a `type="text"`, evitando que el navegador bloquee el guardado del formulario con el mensaje nativo *"Please enter a URL"*.
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
