# ROADMAP.md — CineTrack

## Próximas Fases (Hitos Planeados)

### Versión Mínima (Hito Académico)
- [x] **Fase 1: Arquitectura y Scaffolding Inicial**
  - Evaluación crítica de arquitectura aprobada.
  - Estructura base de backend (`FastAPI`) y frontend (`Vite + React + TS`).
  - Configuración de runners de tests (`pytest`, `vitest`) con smoke tests en verde.
- [x] **Fase 2: Persistencia y Modelo Relacional**
  - Modelos SQLAlchemy 2.0 (Usuarios, Títulos, Temporadas, Episodios, Estados, Reseñas).
  - Configuración de Alembic y migración inicial `0001_initial_schema.py`.
  - Suite de tests de integridad y relaciones en verde (7 tests).
- [x] **Fase 3: Autenticación y Motor de Estados de Título**
  - Registro y login con hash `bcrypt` y tokens JWT con `AUTH_SECRET_KEY`.
  - Lógica de estados: Favorito independiente, transiciones Watchlist/Siguiendo/Vista/Abandonar.
  - Suite de tests unitarios exhaustivos para auth y máquina de estados en verde (16 tests totales).
- [x] **Fase 4: Integración TMDB y Sincronización**
  - Cliente asíncrono con `httpx` (Bearer auth, semáforo y reintentos).
  - Ingesta inicial parametrizable (populares y top-rated con switch de prioridad).
  - Sincronización periódica/diaria e importación manual por JSON con plantillas y búsqueda inteligente.
  - Cálculo de percentiles de popularidad (`PERCENT_RANK`).
  - Mocks y suite automatizada de tests de integración con cero consumo de cuota (23 tests pasando).
- [x] **Fase 5: Frontend UI y Motor Integral de Reseñas (v0.6.0 - v0.7.0)**
  - Home en 3 columnas (Asistente IA, catálogo curado central y panel personal del usuario).
  - Look & feel cinematográfico dorado/carbón (`#0d0d0d`, `#141414`, `#262626`, `#f59e0b`).
  - Explorador y catálogo con filtros multidimensionales (`/catalog`).
  - Detalle de título (`/titles/:id`) con temporadas, episodios y selector interactivo de estados.
  - Soporte de banderas de país, nombres completos e idiomas originales con `Intl.DisplayNames`.
  - Motor Integral de Reseñas: 1 reseña por usuario con edición y borrado in-place, validación de saltos de 0.5, calificación opcional, visualización unificada (TMDB + local) y pantalla dedicada `/reviews`.
  - Mi Biblioteca (`/library`) y Perfil de usuario (`/profile`).
  - Suite de 49 tests en backend y pruebas en Vitest (100% pasando).
- [x] **Fase 3 & 5 Complementarias: Progreso, Perfil, Fotos de Actores, Reseñas y Localización (v0.8.0 - v0.8.1)**
  - Barra segmentada por temporada en Siguiendo (`SeasonProgressBar`) calculada sobre episodios estrenados y regla de regresión a la temporada incompleta más temprana.
  - Orden cronológico estricto (`fecha_favorito DESC`, `fecha_estado DESC`) en biblioteca y actualización de `fecha_estado` en episodios.
  - Perfil de usuario completo: edición con lápiz (bio, país, ciudad, avatar), métricas clave (total horas, promedio semanal cine, temporadas completadas), Top 5 con percentil normalizado, y gráfico Donut SVG de géneros con animaciones y tooltips interactivos.
  - Encuadre interactivo de avatar desde la PC: zoom-out/in (0.2x a 3.0x), arrastre, canvas 256×256 px, persistencia binaria con cache-busting, prevención de *tainted canvas* vía conversión a Data URL local, botón para restablecer a default y soporte para URLs externas sin validaciones bloqueantes.
  - Ingesta de fotos oficiales de actores y sección Top Cast en detalle de títulos, ubicada por encima de las temporadas en series.
  - Restricción de reseñas para títulos no vistos (con preservación de edición para reseñas existentes).
  - Localización reactiva completa al español en toda la interfaz (menú, catálogo "Explore", detalle de títulos, temporadas, reseñas y configuración).
  - Pantalla dedicada de Configuración (`/settings`): cambio de contraseña seguro y selector de idioma de interfaz.
  - Suite de 54 tests en backend y pruebas en Vitest (100% pasando).
- [ ] **Fase 6: Recomendador Inteligente con IA Embebida**
  - Integración de API (Google Gemini / Groq / Ollama) con prompt estructurado y contexto de perfil.
  - Verificación y política de incertidumbre.

---

## Backlog (Pendientes para Versión Superior)

- [x] Repaso e iconografía personalizada de géneros cinematográficos *(Completado en v0.8.5)*.
- [x] Buscador integral por título, director, guionista y actor *(Completado en v0.8.4)*.
- [x] Pantallas de extensión ("Ver más") con paginación para cada sección *(Completado: enlaces en carruseles de Home conectados a `/catalog` con filtros de sección/género y paginación completa)*.
- [x] Panel de estadísticas avanzadas en el perfil (tiempo total, distribución de géneros, gráfico Donut SVG) *(Completado en v0.8.0)*.
- [x] Selector de idioma de interfaz y diccionario de géneros *(Completado en v0.8.0 - v0.8.1)*.
- [x] Ingesta de fotos de actores y sección Top Cast *(Completado en v0.8.0 - v0.8.1)*.
- [x] Carga de avatar desde archivo local con centrado y zoom *(Completado en v0.8.0 - v0.8.1)*.
- [ ] **Sistema de notificaciones activas por panel in-app:**
  - Avisos informativos por cambio de status de series en cualquier lista del usuario (renovación con/sin fecha, cancelación, finalización, hiatus entre temporadas o reboots sin alterar el estado del usuario).
  - Alertas automáticas cuando una serie en estado "Vista" estrena nueva temporada/episodios, pasando automáticamente a "Siguiendo".
- [ ] **Badge visual "Viendo Actualmente" (🔥):**
  - Indicador en series de "Siguiendo" con episodios recientes, con ventana de días configurable por cada usuario desde su pantalla de Configuración (`/settings`).
- [ ] **Soporte multirregión para plataformas de streaming:**
  - Integración de JustWatch / TMDB Watch Providers según el país del usuario, requiriendo tabla relacional propia.
- [ ] **Selector de idioma para el contenido (Títulos y Sinopsis):**
  - Tabla de traducciones multilingüe conectada a TMDB, con regla de fallback al inglés/idioma original para contenidos o idiomas faltantes.
- [ ] **Expansión selectiva del catálogo mediante jobs dirigidos:**
  - Comando o endpoint administrativo para ingestar títulos con filtros específicos (ej. cine argentino, series de $\ge 5$ temporadas, etc.) sin rehacer la ingesta inicial completa.
- [ ] **Recomendador avanzado:**
  - Evolución del recomendador con function calling y búsqueda semántica vectorial (embeddings con pgvector).
- [ ] Posible refinamiento UX en desmarques de episodios: diálogo opcional para advertir al usuario o resetear progreso posterior al desmarcar un episodio intermedio.
