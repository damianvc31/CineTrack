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
- [x] **Fase 3 Complementaria: Progreso de Siguiendo, Orden Cronológico, Perfil y Settings (v0.8.0)**
  - Barra segmentada por temporada en Siguiendo (`SeasonProgressBar`) calculada sobre episodios estrenados y regla de regresión a la temporada incompleta más temprana.
  - Orden cronológico estricto (`fecha_favorito DESC`, `fecha_estado DESC`) en biblioteca y actualización de `fecha_estado` en episodios.
  - Perfil de usuario completo fiel a `user-profile.png`: edición in-place con lápiz (bio, país, ciudad, avatar URL), métricas clave (total horas, promedio semanal cine, temporadas completadas), Top 5 con formato `Nombre · N seasons | AAAA-AAAA`, puntaje personal verificado (`⭐ X.X`), y gráfico Donut SVG de géneros.
  - Pantalla dedicada de Configuración (`/settings`): cambio de contraseña seguro y selector de idioma de interfaz con traducción de géneros en frontend.
  - Suite de 53 tests en backend y pruebas en Vitest (100% pasando).
- [ ] **Fase 6: Recomendador Inteligente con IA Embebida**
  - Integración de API (Google Gemini / Groq / Ollama) con prompt estructurado y contexto de perfil.
  - Verificación y política de incertidumbre.

---

## Backlog (Pendientes para Versión Superior)

- [ ] Sistema de notificaciones activas por estrenos de nuevas temporadas.
- [ ] Badge "Viendo Actualmente" (🔥) en series con episodios recientes.
- [x] Panel de estadísticas avanzadas en el perfil (tiempo total, distribución de géneros, gráfico Donut SVG) *(Completado en v0.8.0)*.
- [x] Selector de idioma de interfaz y diccionario de géneros *(Completado en v0.8.0)*.
- [ ] Recomendador avanzado con function calling y búsqueda semántica vectorial (embeddings con pgvector).
- [ ] Buscador extendido con filtros por director, guionista y actor.
- [ ] Pantallas de extensión ("Ver más") con paginación para cada sección.
- [ ] Soporte multirregión para plataformas de streaming (JustWatch / TMDB Watch Providers).
- [ ] Posible refinamiento UX en desmarques de episodios: diálogo opcional para advertir al usuario o resetear progreso posterior al desmarcar un episodio intermedio.
