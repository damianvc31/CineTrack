# Arquitectura del Recomendador Mínimo — CineTrack

Este documento detalla la arquitectura, flujo de datos, cascada de resiliencia y mecanismos de *grounding* del **Recomendador Mínimo por IA** de CineTrack, implementado en el branch `feature/recomendador-minimo`.

---

## 1. Diagrama de Arquitectura y Flujo de Datos

```mermaid
flowchart TD
    %% Estilos y Definiciones
    classDef client fill:#1f2937,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef api fill:#111827,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef service fill:#1e1e2e,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef db fill:#261b36,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef ai fill:#2d1a29,stroke:#ec4899,stroke-width:2px,color:#fff;
    classDef fallback fill:#371b1b,stroke:#ef4444,stroke-width:2px,color:#fff;

    subgraph CLIENTE["Capas Frontend (React + Vite + TypeScript)"]
        UI["RecommendationsPage / HomePage (Sidebar)"]:::client
        PRESETS["Presets Dinámicos Categorizados\n(Género, Directores, Actores, Épocas, Emociones, Revivir)"]:::client
        CACHE["Cache de Navegación (sessionStorage)"]:::client
        SYNC["Sincronización de Estados (Favorito / Visto / Watchlist)"]:::client
        
        UI --> PRESETS
        UI <--> CACHE
        UI <--> SYNC
    end

    subgraph BACKEND["Capa de Backend (FastAPI Asíncrono)"]
        ENDPOINT["POST /api/v1/recommendations\n(prompt, tipo_filtro, language)"]:::api
        AUTH["Inyección de Dependencias\n(get_db, get_optional_current_user)"]:::api
        
        ENDPOINT --> AUTH
    end

    subgraph CATALOG["Motor de Catálogo y Contexto (catalog_service)"]
        PARSER["Extractor de Intenciones & Filtros\n- Detección de géneros (GENRE_KEYWORD_MAP)\n- Épocas / Décadas (extract year)\n- Tipo (movie / tv / all)\n- Intención rewatch / only_watched"]:::service
        CTX_USER["get_user_recommendation_context\n- Géneros favoritos\n- Top valoradas y favoritos\n- Historial de visualizaciones"]:::service
        SQL_POOL["Selección Acotada de Candidatos SQL\n(Pool acotado de 30 a 45 títulos con vote_count >= 50)"]:::service
        HYDRATE["get_hydrated_recommendations\n(Enriquecimiento de TitleCardResponse completa)"]:::service

        PARSER --> SQL_POOL
        CTX_USER --> SQL_POOL
    end

    subgraph PERSISTENCIA["Persistencia (PostgreSQL / SQLite)"]
        DB_TITULOS[(titulos)]:::db
        DB_ESTADOS[(estados_usuario_titulos)]:::db
        DB_RESENAS[(resenas)]:::db
        DB_GENEROS[(generos & titulos_generos)]:::db

        SQL_POOL --> DB_TITULOS
        SQL_POOL --> DB_GENEROS
        CTX_USER --> DB_ESTADOS
        CTX_USER --> DB_RESENAS
        HYDRATE --> DB_TITULOS
        HYDRATE --> DB_ESTADOS
    end

    subgraph AI_ENGINE["Servicio Orquestador de IA (ai_recommender_service)"]
        PROMPT_BUILDER["Constructor de Prompt & Grounding Estricto\n- System Prompt (JSON estricto, idioma forzado)\n- Contexto de usuario\n- Pool cerrado de títulos con IDs reales"]:::service
        CASCADE{"Conmutación por Error\n(Resilience Cascade)"}:::service
        
        GEMINI["1. Primario: Google Gemini API\n(gemini-2.0-flash / gemini-3.6-flash)\nLlamada HTTP asíncrona (httpx)"]:::ai
        GROQ["2. Secundario: Groq API\n(llama-3.3-70b-versatile / gpt-oss-120b)\nFallback ante 429/500/timeout"]:::ai
        HEURISTIC["3. Respaldo Offline: Motor Heurístico Determinista\n(Ponderación local por popularidad y rating)"]:::fallback
        
        VALIDATOR["Validador & Sanitizador de Respuesta\n- Coerción JSON\n- Filtro: SOLO IDs del pool\n- Manejo de clarification_needed"]:::service

        PROMPT_BUILDER --> CASCADE
        CASCADE -- "API Key ok" --> GEMINI
        CASCADE -- "Falla o sin cuota" --> GROQ
        CASCADE -- "Falla Groq o sin keys" --> HEURISTIC
        
        GEMINI --> VALIDATOR
        GROQ --> VALIDATOR
        HEURISTIC --> VALIDATOR
    end

    %% Conexiones entre componentes
    UI -- "1. Request JSON" --> ENDPOINT
    ENDPOINT -- "2. Extraer candidatos y perfil" --> PARSER
    AUTH -.-> CTX_USER
    SQL_POOL -- "3. Candidatos (30-45 dicts)" --> PROMPT_BUILDER
    VALIDATOR -- "4. IDs recomendados + justificaciones" --> HYDRATE
    HYDRATE -- "5. Response estructurada (cards + reasons + metadata)" --> ENDPOINT
    ENDPOINT -- "6. Response JSON (RecommendationResponse)" --> UI
```

El archivo fuente `.mmd` independiente se encuentra en [docs/UML/recomendador/arquitectura_recomendador_minimo.mmd](docs/UML/recomendador/arquitectura_recomendador_minimo.mmd).

---

## 2. Principios de Diseño

### 2.1. Grounding Estricto sobre el Catálogo Local (Anti-Alucinación)
El LLM no opera en un espacio abierto sin restricciones; opera sobre un **pool cerrado de candidatos** preseleccionado en la base de datos relacional:
1. `catalog_service.get_recommendation_candidates` extrae de 30 a 45 títulos relevantes según filtros de género, época (`extract('year', Titulo.fecha_estreno)`), tipo de obra y popularidad (`vote_count >= 50`).
2. Se inyecta al modelo únicamente el ID, título, tipo, año, géneros, puntaje de comunidad, sinopsis corta y fragmento de reseña comunitaria de esos candidatos.
3. El *System Prompt* y la capa de sanitización posterior (`sanitized_recs`) garantizan que el modelo solo pueda sugerir obras que figuren con su `title_id` en dicho pool.

### 2.2. Cascada de Resiliencia Multinivel (Offline-First Ready)
Para evitar que el usuario quede desatendido ante cortes de cuota o límites de tasa de los proveedores de nube:
- **Nivel 1 (Primario):** Google Gemini API (`gemini-2.0-flash` o configurable vía `GEMINI_MODEL`).
- **Nivel 2 (Secundario):** Groq API (`llama-3.3-70b-versatile` o `openai/gpt-oss-120b`). Se activa automáticamente ante códigos HTTP 429, 500, timeouts o excepciones de red.
- **Nivel 3 (Heurístico Local):** Motor determinista en Python sin dependencias de red. Si no hay API keys configuradas o ambas APIs fallan, puntúa los candidatos por afinidad de géneros y calificación unificada, devolviendo siempre una recomendación válida.

### 2.3. Sincronización Estricta de Idioma
- El frontend transmite explícitamente el idioma actual de la interfaz (`language: "es" | "en"`).
- Tanto el prompt de sistema como el prompt de usuario imponen la directiva crítica en mayúsculas para asegurar que el mensaje de apertura y cada una de las justificaciones (`reason`) se redacten en el idioma solicitado, independientemente de si el texto de búsqueda contiene nombres propios o títulos en inglés.
- El motor heurístico local implementa plantillas bilingües equivalentes.

### 2.4. Experiencia de Usuario y Persistencia
- **Caché de sesión (`sessionStorage`):** Al navegar hacia la ficha de detalle de un título recomendado y retroceder con el navegador, las recomendaciones y el prompt previo se conservan intactos sin forzar un nuevo llamado a la API.
- **Sincronización bidireccional:** Al alternar el estado de un título (favorito, visto, watchlist) desde la card o desde la página de detalle, el estado visual de la tarjeta recomendada se actualiza en tiempo real.
- **Diferenciación visual clara:** Cada tarjeta recomendada cuenta con badges explícitos de `Película` o `Serie de TV` y la justificación personalizada redactada por el asistente.
