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
- [x] **Fase 6: Recomendador Inteligente con IA Embebida (v0.9.0 - v0.9.4)**
  - Integración híbrida de IA: Google Gemini 2.0/3.6 Flash primario con fallback a Groq API y motor heurístico local determinista.
  - Cascada jerárquica multi-modelo de 2 niveles entre proveedores priorizando modelos insignia (v0.9.3).
  - Optimización de cuota con reducción del 70% en el payload de candidatos (v0.9.3).
  - Afinación semántica bilingüe (`THEME_EXPANSION_MAP`) y búsqueda temática cruzada en SQL (v0.9.2).
  - Filtro de rango temporal en estadísticas de perfil, tarjetas de seguimiento con póster vertical 2:3, avatares de actores con iniciales completas, validación determinista de entradas ininteligibles, cancelación instantánea de peticiones en vuelo y flujo de repregunta interactivo (v0.9.4).
  - Endpoint `POST /api/v1/recommendations` con hidratación completa de `TitleCard`.
  - Pantalla dedicada `/recommendations` (`RecommendationsPage.tsx`), filtros temáticos y suite de 71 tests en backend.
- [ ] **Fase 7: Despliegue a Producción y Entrega Final (v1.0.0)**
  - Arquitectura PaaS cloud de costo cero (Render Web Service + Vercel Edge + Neon PostgreSQL).
  - Script de migración y volcado del catálogo de desarrollo (`cinetrack.db`) a la base de datos PostgreSQL remota.
  - Sincronización diaria automatizada mediante GitHub Actions (`.github/workflows/daily_sync.yml`).
  - Verificación funcional integral y documentación de entrega académica.

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
- [x] **Expansión selectiva del catálogo mediante jobs dirigidos (Criterio 1):** *(Completado en v0.9.1)*
  - Job CLI `python -m app.jobs.sync_tmdb --expand` con filtro por género (individual o masivo), tipo de medio (`both`, `movie`, `tv`) y umbrales configurables de votos (`min_vote_count`) y calificación (`min_vote_average`) sin duplicar títulos existentes ni rehacer la ingesta inicial completa.
- [ ] **Recomendador avanzado (Post-Entrega):**
  - Evolución del recomendador hacia búsqueda semántica vectorial mediante embeddings (`fastembed` en CPU o Google Text-Embedding API) y `pgvector` en PostgreSQL. Se prescinde formalmente de *function calling* por inviabilidad técnica en producción (latencia acumulada de 5-8s y rápido agotamiento de cuotas TPM en capas gratuitas), adoptando un patrón RAG híbrido de un solo turno.
- [ ] Posible refinamiento UX en desmarques de episodios: diálogo opcional para advertir al usuario o resetear progreso posterior al desmarcar un episodio intermedio.
