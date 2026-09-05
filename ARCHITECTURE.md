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
- Las películas aprovechan campos específicos (como `duracion`).
- Las series se relacionan 1:N con `temporadas` y a su vez 1:N con `episodios`.
- **Beneficio:** Elimina `JOINs` costosos en las pantallas principales y de exploración ("Todos", "Trending", "Estrenos") donde se presentan películas y series de forma unificada.

### 2.2. Esquema Relacional Principal
1. **`usuarios`**: Autenticación mínima (login/password con hash `bcrypt`/`argon2`), perfil (país, ciudad, biografía, avatar, fecha_registro).
2. **`titulos`**: Catálogo de películas y series con metadatos técnicos y de TMDB.
3. **`generos`** & **`titulos_generos`**: Clasificación N:M (un título pertenece a múltiples géneros).
4. **`actores`** & **`titulos_elenco`**: Reparto principal N:M.
5. **`temporadas`** & **`episodios`**: Jerarquía episódica de series con duraciones por episodio y fechas de emisión.
6. **`estados_usuario_titulos`**: Estado granular por usuario (`favorito` booleano independiente, y `estado` mutuamente excluyente: `watchlist`, `siguiendo`, `vista`, o `null`), con sus respectivas marcas temporales para ordenamiento.
7. **`episodios_vistos`**: Historial atómico de episodios vistos por usuario y fecha.
8. **`resenas`**: Reseñas y puntajes. Diseñado con autor polimórfico: `usuario_id` (FK nullable a `usuarios`) o `autor_tmdb` (texto) con identificador externo `tmdb_review_id` para deduplicación.

### 2.3. Almacenamiento de Avatares
- **Versión Mínima:** Selección de avatares predeterminados locales (identicons/SVGs) o URLs externas. Subida de avatares guardando una miniatura optimizada directamente en la base de datos (`BYTEA` / Base64 limitada a <300 KB), evitando la pérdida de archivos en filesystems efímeros de hosting PaaS.

---

## 3. Integración Externa y Procesos en Background

1. **TMDB API:**
   - Consumo vía `httpx` asíncrono con control de rate limits.
   - Sincronización masiva inicial estructurada como script modular (`python -m app.jobs.sync_tmdb`).
   - Sincronización diaria: refresco de popularidad/percentiles, actualización de `status`/`next_episode_to_air` y absorción incremental de nuevas reseñas hasta el tope configurado.
   - Sincronización reactiva: al momento del login del usuario, transición automática de series en `Vista` hacia `Siguiendo` si se detecta nueva temporada confirmada.
2. **Recomendador de IA Embebido:**
   - Desacoplado de los hubs del entorno de desarrollo.
   - **Versión Mínima:** Recomendador simple sin function calling (implementado como última pieza del flujo núcleo según `spec.md`). Conexión vía API a modelo gratuito/eficiente (Google Gemini API / Groq API) con un prompt directo estructurado que combina el texto del usuario con sus preferencias de perfil (favoritos, vistos, reseñas) y puntajes de comunidad.
   - **Versión Superior:** Evolución planificada a *function calling* estructurado (herramientas de búsqueda exacta + similitud semántica con embeddings vectoriales), con la arquitectura de FastAPI ya preparada para soportar ambas modalidades.

---

## 4. Estructura del Repositorio

```
/ (raíz del proyecto)
├── docs/                   # UMLs, wireframes y especificaciones visuales
├── backend/                # API FastAPI, modelos SQLAlchemy, servicios
│   ├── app/
│   │   ├── api/            # Routers (v1)
│   │   ├── core/           # Configuración, JWT, variables de entorno
│   │   ├── db/             # Conexión DB, sesión async, Base
│   │   ├── models/         # Modelos de dominio ORM
│   │   ├── schemas/        # Esquemas Pydantic v2
│   │   ├── services/       # Lógica de estados, TMDB, recomendador IA
│   │   └── main.py         # Entrypoint de FastAPI
│   ├── tests/              # Suite de pruebas Pytest
│   └── alembic/            # Migraciones de esquema
├── frontend/               # SPA React + Vite + TypeScript
│   ├── src/
│   │   ├── components/     # Componentes reutilizables
│   │   ├── pages/          # Vistas (Home, Detalle, Perfil)
│   │   ├── services/       # Conexión con API backend
│   │   └── App.tsx
│   └── tests/              # Suite de pruebas Vitest
├── TASK_PLAN.md            # Plan de tareas activo y estado de avance
├── ARCHITECTURE.md         # Este documento
├── CHANGELOG.md            # Registro de cambios por versión/tag
├── ROADMAP.md              # Backlog y próximas fases
└── README.md               # Guía de instalación, ejecución y variables
```
