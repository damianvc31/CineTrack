# ROADMAP.md — CineTrack

> **Nota de Historial:** Las fases 1 a 11 (scaffolding inicial, modelos relacionales, autenticación JWT, sincronización TMDB, reseñas, perfil de usuario, despliegue a producción en Neon/Render/Vercel, RAG híbrido vectorial con pgvector, arquitectura keep-alive, invariantes de estreno, control de variedad con Reasoning Dispatcher e i18n inicial) están **100% completadas y verificadas**. El detalle histórico de cada versión y tarea se encuentra en [TASK_PLAN.md](TASK_PLAN.md) y [CHANGELOG.md](CHANGELOG.md). Este archivo define exclusivamente la evolución futura del producto tras la entrega final.

---

## 1. Bloque Inmediato: Deuda Técnica, Calidad y Seguridad *(Quick Wins)*
*Mejoras puntuales de ingeniería surgidas de la evaluación de fin de curso para blindar el backend.*

- [ ] **Quality Gate en CI (GitHub Actions):**
  - Crear `.github/workflows/ci.yml` para ejecutar automáticamente la suite completa de pruebas (`pytest` en backend, `npm test` y `npm run build` en frontend) ante cada *push* o *pull request* hacia la rama `main`.
- [ ] **Fail-Closed de Seguridad en Arranque (`config.py`):**
  - Modificar la validación de inicio para lanzar un `RuntimeError` y abortar la ejecución si el entorno es `production` y las claves secretas (`SECRET_KEY`, `ADMIN_API_KEY`) corresponden a los valores por defecto de desarrollo.
- [ ] **Reporte Formal de Cobertura (`pytest-cov`):**
  - Incorporar `pytest-cov`, configurar exclusiones formales y generar reportes reproducibles (terminal y HTML) con métricas de líneas y ramas evaluadas.
- [ ] **Rate Limiting en Autenticación:**
  - Proteger el endpoint de inicio de sesión (`/api/v1/auth/login`) contra ataques de fuerza bruta utilizando `slowapi` (límite configurable, ej. 5 intentos por minuto por IP).
- [ ] **Estandarización de Verbos HTTP de Mantenimiento (`DELETE`):**
  - Migrar las rutas administrativas de purga y borrado destructivo de `POST` a `DELETE`, respetando la semántica REST estricta.
- [ ] **Endpoints Granulares de Limpieza de Base de Datos:**
  - Crear rutas administrativas seguras (`DELETE`) para purgas selectivas e independientes:
    - Reseteo de estados de usuario (limpieza de tracking sin eliminar usuarios).
    - Purga de reseñas (filtrable por: solo TMDB, solo locales de usuarios, o ambas).
    - Purga de usuarios de prueba (con opción de excluir administradores).
    - Verificación y consolidación del endpoint existente de vaciado de títulos.
- [ ] **Persistencia y Exportación de Logs de Jobs:**
  - Escribir el resultado detallado de cada ejecución de sincronización en archivos de texto/logs auditables en disco, evitando que la información se pierda si el proceso en memoria reinicia.

---

## 2. Bloque de Optimización Operativa: Sincronización TMDB (Daily & Weekly)
*Ajustes para maximizar la eficiencia y optimizar el uso de cuota de red y tiempos de cómputo.*

- [ ] **Auditoría de la Sincronización Semanal (`weekly_deep_sync`) vs `/changes`:**
  - Evaluar si la llamada al endpoint `/changes` en la pasada semanal aporta valor real frente a la pasada rápida de métricas de todos los títulos, o si genera tráfico y tiempo redundante.
- [ ] **Sintonía Fina de la Sincronización Diaria (`daily_sync`):**
  - **Pre-refresh de métricas:** Actualizar estatus, votos y popularidad antes de visitar series activas.
  - **Acotamiento de Series Activas:** Filtrar estrictamente para consultar solo series en estado `Returning Series`.
  - **Ventanas Temporales Diferenciadas:** Separar el parámetro de ventana de días de títulos no estrenados (`unreleased_days_window`) respecto al de nuevos estrenos (`releases_days_window`).
  - **Desglose en Reportes:** Discriminar con claridad en los logs y resúmenes la cantidad de títulos *unreleased* ingresados vs. los *new releases* reales.

---

## 3. Bloque Recomendador IA: Filtros Duros y Semántica
*Mayor control determinista sobre las recomendaciones antes de invocar al LLM.*

- [ ] **Filtros Duros de Duración y Formato:**
  - Detección determinista de duración para películas (ej: *"menos de 90 minutos"*, *"largas de más de 2h 30m"*).
  - Detección de longitud para series y temporadas (ej: *"miniseries de 1 temporada"*, *"series cortas de menos de 10 capítulos"*).
- [ ] **Enriquecimiento Semántico con Keywords de TMDB *(Backlog IA)*:**
  - Incorporar palabras clave temáticas de TMDB al texto a vectorizar para mejorar la coincidencia semántica en búsquedas de nicho sin disparar costos de inferencia.

---

## 4. Bloque UX, Interacción y Frontend
*Mejoras visuales y de interacción para usuarios invitados y frecuentes.*

- [ ] **Selector de Idioma en el Header (Público y Autenticado):**
  - Trasladar el selector de idioma (UI y futuro catálogo) desde *Settings* directamente a la barra de navegación superior (Header).
  - **Persistencia Híbrida:** 
    - *Invitados / No logueados:* Persistencia inmediata en `localStorage` del navegador.
    - *Usuarios autenticados:* Sincronización bidireccional con el campo de preferencias en la base de datos para recordar la elección entre distintos dispositivos.
- [ ] **Protección UX contra Desmarques Accidentales:**
  - Diálogo modal de advertencia antes de desmarcar temporadas o episodios completos marcados previamente como vistos.
- [ ] **Filtros Avanzados en Explorador de Catálogo (`/explore`):**
  - Filtros rápidos por estado de producción mediante badges (*In Production*, *Coming Soon*, *Pending Renewal*, *Ended*, etc.).
- [ ] **Herramientas Avanzadas en Mi Biblioteca (`/library`):**
  - Ordenamiento multidimensional (por fecha de agregado, calificación propia, rating TMDB, fecha de estreno).
  - Buscador *in-place* dentro de las listas personales.
  - Filtros combinados por tipo (películas / series) y géneros.
  - Paginación o virtualización optimizada para la sección de "Vistos" cuando acumula cientos de obras.
- [ ] **Badge Visual "Viendo Actualmente" (🔥):**
  - Distintivo visual en series dentro de `Siguiendo` con episodios vistos en los últimos 7 o 14 días (ventana configurable desde `/settings`).

---

## 5. Grandes Fases Funcionales del Producto *(Evolución)*

### Fase 12: Sistema de Notificaciones In-App y Ciclo de Vida Reactivo
- [ ] **Campana de Alertas en Header:** Panel flotante con notificaciones no leídas y leídas.
- [ ] **Alertas Relevantes:** Aviso de estreno de nuevos episodios de series en seguimiento, anuncios de renovación y cancelaciones.
- [ ] **Reactivación Automática:** Transición automática de serie completada (`vista`) a `Siguiendo` cuando TMDB estrene una nueva temporada.
- [ ] **Preferencias:** Configuración granular de qué tipos de alertas desea recibir el usuario.

### Fase 13: Traducción de Contenidos y Expansión Multilingüe
- [ ] **Ingesta Multilingüe desde TMDB:** Soporte para títulos, sinopsis, nombres de temporadas/episodios y personajes.
- [ ] **Cascada Resiliente:** `es-MX` (Latinoamérica) → `es-ES` (España) → `en-US` (Inglés) → Idioma original de la obra.
- [ ] **Soporte Multi-idioma Extendido *(Largo Plazo)*:** Arquitectura preparada para incorporar idiomas adicionales más allá del español e inglés (ej: Portugués `pt-BR`, Francés `fr-FR`, Italiano `it-IT`).

### Fase 14: JustWatch y Disponibilidad de Streaming (Watch Providers)
- [ ] **Integración TMDB Watch Providers:** Persistencia de plataformas (Netflix, Prime, Max, Disney+, etc.) por país y tipo de acceso (*flatrate*, alquiler, compra).
- [ ] **Detección Automática de Región:** Geolocalización o preferencia de país en perfil.
- [ ] **Filtros de Disponibilidad:** Explorar catálogo filtrando exclusivamente por las plataformas que el usuario tiene contratadas.

### Fase 15: Catálogo Extendido y Enriquecimiento de Series
- [ ] **Expansión por Metadatos:** Ingesta orientada por director, actores principales, país de origen o décadas.
- [ ] **Metadatos Granulares:** Elenco de series diferenciado por temporada, nombres propios de temporadas y sinopsis detallada por capítulo.

---

## 6. Bloque Avanzado y Visión de Negocio *(Largo Plazo)*
- [ ] **Autenticación Ampliada & Email:** Campo de email obligatorio/opcional, recuperación de contraseña y Google OAuth (SSO) + notificaciones por correo electrónico.
- [ ] **Optimización Mobile Web:** Rediseño responsivo de la distribución de componentes en la Home para navegadores en smartphones.
- [ ] **Estrategia de Base de Datos Dev:** Mantener SQLite local; evaluar PostgreSQL en Docker local únicamente si se requiere paridad estricta con `pgvector` sin consumir cuota de Neon.
- [ ] **Escala de Negocio:** Aplicación móvil dedicada (React Native / PWA nativa) y potenciales modelos de monetización/publicidad.
