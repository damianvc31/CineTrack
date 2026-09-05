# ROADMAP.md — CineTrack

## Próximas Fases (Hitos Planeados)

### Versión Mínima (Hito Académico)
- [x] **Fase 1: Arquitectura y Scaffolding Inicial**
  - Evaluación crítica de arquitectura aprobada.
  - Estructura base de backend (`FastAPI`) y frontend (`Vite + React + TS`).
  - Configuración de runners de tests (`pytest`, `vitest`) con smoke tests en verde.
- [ ] **Fase 2: Persistencia y Modelo Relacional**
  - Modelos SQLAlchemy 2.0 (Usuarios, Títulos, Temporadas, Episodios, Estados, Reseñas).
  - Configuración de Alembic y migración inicial.
- [ ] **Fase 3: Autenticación y Motor de Estados de Título**
  - Registro y login con hash `bcrypt`/`argon2` y tokens JWT.
  - Lógica de estados: Favorito independiente, transiciones Watchlist/Siguiendo/Vista/Abandonar.
  - Suite de tests unitarios exhaustivos para la máquina de estados.
- [ ] **Fase 4: Integración TMDB y Sincronización**
  - Cliente asíncrono con `httpx` y control de cuota.
  - Importación inicial de catálogo acotado (~200 títulos variados).
  - Cálculo de percentiles de popularidad (`PERCENT_RANK`).
  - Mocks de TMDB para tests sin consumo de cuota real.
- [ ] **Fase 5: Frontend UI (Consumo de API Real)**
  - Home con secciones (Trending, Estrenos, Clásicos, Recomendados, Géneros) y toggle Películas/Series/Todos.
  - Detalle de Película y Serie con temporadas, episodios y selector interactivo de estados.
  - Perfil de usuario con secciones por estado (Favoritos, Watchlist, Siguiendo, Vista, Reseñas).
- [ ] **Fase 6: Recomendador Inteligente con IA Embebida**
  - Integración de API (Google Gemini / Groq) con prompt estructurado y contexto de perfil.
  - Verificación y política de incertidumbre.

---

## Backlog (Pendientes para Versión Superior)

- [ ] Sistema de notificaciones activas por estrenos de nuevas temporadas.
- [ ] Badge "Viendo Actualmente" (🔥) en series con episodios recientes.
- [ ] Panel de estadísticas avanzadas en el perfil (tiempo total, distribución de géneros, gráficos).
- [ ] Recomendador avanzado con function calling y búsqueda semántica vectorial (embeddings con pgvector).
- [ ] Buscador extendido con filtros por director, guionista y actor.
- [ ] Pantallas de extensión ("Ver más") con paginación para cada sección.
- [ ] Soporte multirregión para plataformas de streaming (JustWatch / TMDB Watch Providers).
- [ ] Selector independiente de idioma de interfaz y contenido.
