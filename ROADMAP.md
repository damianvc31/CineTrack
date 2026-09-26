# ROADMAP.md — CineTrack

> **Nota de Historial:** Las fases 1 a 11 (scaffolding inicial, modelos relacionales, autenticación JWT, sincronización TMDB, reseñas, perfil de usuario, despliegue a producción en Neon/Render/Vercel, RAG híbrido vectorial con pgvector, arquitectura keep-alive, invariantes de estreno y control de variedad con Reasoning Dispatcher) están **100% completadas y verificadas**. El detalle histórico de cada versión y tarea se encuentra en [TASK_PLAN.md](TASK_PLAN.md) y [CHANGELOG.md](CHANGELOG.md). Este archivo define exclusivamente la evolución futura del producto.

---

## 1. Próximas Fases (Hitos Planeados)

### Fase 12: Sistema de Notificaciones In-App y Ciclo de Vida Reactivo de Series
- [ ] **Centro de Notificaciones en la Interfaz (Campana en Header):**
  - Panel flotante y persistente con alertas de actividad relevante para el usuario.
  - Notificaciones inmediatas ante cambios de status en series seguidas o en watchlist (ej. *"Severance ha sido renovada para la Temporada 3"* o *"The Penguin fijó fecha de estreno de su próximo episodio"*).
- [ ] **Reactivación Automática de Series Vistas a "Siguiendo":**
  - Transición automática de estado cuando una serie que el usuario marcó como `vista` (100% completada) estrena una nueva temporada en TMDB, devolviéndola al carrusel activo de `Siguiendo` con el indicador de progreso correspondiente.
- [ ] **Configuración Granular de Alertas por Usuario:**
  - Preferencias en `/settings` para activar/desactivar notificaciones por tipo (estrenos de episodios, anuncios de renovación, cancelaciones).

---

### Fase 13: Traducción de Contenidos y Selector de Idioma (I18n de Catálogo)
- [ ] **Ingesta y Persistencia de Traducciones Multilingües desde TMDB:**
  - Consulta a `/movie/{id}/translations` y `/tv/{id}/translations` para almacenar títulos y sinopsis en múltiples variantes lingüísticas.
  - Cobertura idéntica para temporadas (nombre de temporada si difiere del estándar, sinopsis) y episodios (nombre y sinopsis traducidos).
- [ ] **Prioridad de Variantes en Español:**
  - Soporte prioritario para **Español Latinoamericano (`es-MX` / `es-419`)** y **Español España (`es-ES`)**, con posibilidad de habilitar idiomas adicionales en el futuro.
- [ ] **Sistema Resiliente de Fallbacks en Cascada:**
  - Si una obra carece de traducción en la variante regional elegida (ej. `es-MX`), el sistema desciende fluidamente a la otra variante hispana (`es-ES`).
  - Si no existe traducción en español, recae en el texto en inglés (`en-US`).
  - Si no existe en inglés, se exhibe el título y sinopsis en el idioma original de la producción.
- [ ] **Selector Interactivo de Idioma de Contenido:**
  - Control en `/settings` para elegir el idioma preferido de los títulos y sinopsis del catálogo (independiente del idioma de los textos de la interfaz UI o sincronizable con él).

---

### Fase 14: Plataformas de Streaming y Disponibilidad Multirregión (Watch Providers)
- [ ] **Integración de TMDB Watch Providers / JustWatch API:**
  - Consulta y persistencia de proveedores de streaming (Netflix, Prime Video, Max, Disney+, Apple TV+, etc.) por título y país.
  - Tablas relacionales en base de datos: `plataformas` (id, nombre, logo_url) y `disponibilidad_streaming` (titulo_id, plataforma_id, pais, tipo_acceso: flatrate, buy, rent).
- [ ] **Detección Automática de Región:**
  - Presentación de opciones de streaming personalizadas según el país configurado en el perfil del usuario (o geolocalización por IP en invitados).
- [ ] **Filtrado por Plataforma en Catálogo:**
  - Selector de servicios de suscripción activos del usuario para explorar únicamente títulos disponibles en sus plataformas contratadas.

---

## 2. Backlog (Pendientes sin Priorizar)

- [ ] **Carrusel "Upcoming / Próximamente" en Home:**
  - Carrusel horizontal dedicado en la página principal para explorar visualmente películas y series muy esperadas con fecha de estreno confirmada en los próximos 30 a 90 días.
- [ ] **Ampliación del Modelo de Datos (Metadatos Granulares de Series):**
  - Elenco de series segmentado por temporada (distinción de actores principales o recurrentes por entrega).
  - Título propio de temporada cuando cuente con denominación temática específica (ej. *True Detective: Night Country*, *Fargo: Year 5*).
  - Sinopsis enriquecida de episodios individuales.
- [ ] **Herramientas Avanzadas en Sección Biblioteca (`/library`):**
  - Ordenamiento multidimensional (por fecha de agregado, rating propio, rating TMDB, fecha de estreno o alfabético).
  - Filtros rápidos por tipo (películas / series) y géneros dentro de cada pestaña de la biblioteca personal.
  - Buscador in-place para localizar rápidamente obras dentro de listas extensas.
  - Paginación o carga virtualizada optimizada para colecciones con cientos o miles de títulos.
- [ ] **Autenticación Ampliada & Notificaciones Externas:**
  - Campo `email` obligatorio o sugerido al registrarse para envío de notificaciones y recuperación segura de cuenta.
  - Inicio de sesión social mediante Google OAuth (Single Sign-On).
- [ ] **Badge Visual "Viendo Actualmente" (🔥):**
  - Indicador destacado en series en curso dentro de `Siguiendo` con episodios vistos en los últimos 7 o 14 días (ventana configurable por el usuario desde `/settings`).
- [ ] **Diálogo de Confirmación en Desmarques Intermedios de Episodios:**
  - Modal de confirmación al desmarcar un episodio intermedio de una serie: opción de desmarcar únicamente ese episodio o resetear también los episodios posteriores.
- [ ] **Soporte PWA Offline Avanzado con Service Workers:**
  - Carga en caché local de biblioteca y fichas de títulos previamente visitadas para consulta fluida en movilidad sin conexión a internet.
- [ ] **Compartir Listas y Perfiles Públicos:**
  - Enlaces públicos compartibles para el perfil de usuario y listas curadas con vista de solo lectura y metadatos OpenGraph (Twitter/WhatsApp preview cards).
