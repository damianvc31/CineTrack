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
        SQL_POOL["Selección Acotada de Candidatos SQL\n(Pool acotado de 20 títulos con afinidad temática y votos >= 150)"]:::service
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
        CASCADE{"Cascada Jerárquica de 2 Niveles\n(Resilience Cascade)"}:::service
        
        FLAGSHIP["NIVEL 1: Modelos Insignia\n1º Primario (Gemini 3.6-flash)\n2º Secundario (Groq gpt-oss-120b)"]:::ai
        FALLBACK_MODELS["NIVEL 2: Modelos Respaldo Ligeros\n3º Primario (flash-lite-latest, 3.5-flash-lite, 3.8-flash)\n4º Secundario (gpt-oss-20b, compound-mini, qwen-27b)"]:::ai
        HEURISTIC["NIVEL 3: Respaldo Offline Local\nMotor Heurístico Determinista con afinidad temática"]:::fallback
        
        VALIDATOR["Validador & Sanitizador de Respuesta\n- Coerción JSON\n- Filtro: SOLO IDs del pool\n- Manejo de clarification_needed"]:::service

        PROMPT_BUILDER --> CASCADE
        CASCADE -- "Prioridad 1" --> FLAGSHIP
        CASCADE -- "Falla o cuota 429" --> FALLBACK_MODELS
        CASCADE -- "Falla nube o sin red" --> HEURISTIC
        
        FLAGSHIP --> VALIDATOR
        FALLBACK_MODELS --> VALIDATOR
        HEURISTIC --> VALIDATOR
    end

    %% Conexiones entre componentes
    UI -- "1. Request JSON" --> ENDPOINT
    ENDPOINT -- "2. Extraer candidatos y perfil" --> PARSER
    AUTH -.-> CTX_USER
    SQL_POOL -- "3. Candidatos (20 dicts)" --> PROMPT_BUILDER
    VALIDATOR -- "4. IDs recomendados + justificaciones" --> HYDRATE
    HYDRATE -- "5. Response estructurada (cards + reasons + metadata)" --> ENDPOINT
    ENDPOINT -- "6. Response JSON (RecommendationResponse)" --> UI
```

El archivo fuente `.mmd` independiente se encuentra en [docs/UML/recomendador/arquitectura_recomendador_minimo.mmd](docs/UML/recomendador/arquitectura_recomendador_minimo.mmd).

---

## 2. Principios de Diseño

### 2.1. Grounding Estricto sobre el Catálogo Local (Anti-Alucinación)
El LLM no opera en un espacio abierto sin restricciones; opera sobre un **pool cerrado de candidatos** preseleccionado en la base de datos relacional:
1. `catalog_service.get_recommendation_candidates` extrae como máximo **20 títulos relevantes** (`RECOMMENDATION_CANDIDATES_LIMIT = 20`, configurable) aplicando filtros de época, género y afinidad temática bilingüe (`THEME_EXPANSION_MAP`) con un piso de $\ge 150$ votos para relleno general. Esto recorta el prompt a ~1.500 tokens, cuadruplicando la capacidad de consultas por minuto.
2. Si el usuario realiza una búsqueda con conceptos explícitos (ej. *"películas de robos y atracos"*), se desacoplan sus géneros históricos del perfil para evitar sesgos o contaminación temáticos.
3. Se inyecta al modelo únicamente el ID, título, tipo, año, géneros, puntaje de comunidad, sinopsis y fragmento de reseña de esos candidatos.
4. El *System Prompt* y la capa de sanitización posterior (`sanitized_recs`) garantizan que el modelo solo pueda sugerir obras que figuren con su `title_id` en dicho pool.

### 2.2. Cascada de Resiliencia Jerárquica Multi-Nivel (v0.9.3)
Para maximizar la calidad de las recomendaciones y resistir los límites de tasa (HTTP 429) de las capas gratuitas:
- **Nivel 1 (Modelos Insignia / Flagship):**
  - 1º: Modelo principal del proveedor primario (ej. Gemini `gemini-3.6-flash`).
  - 2º: Modelo principal del proveedor secundario (ej. Groq `openai/gpt-oss-120b`).
  - Prioriza la máxima capacidad de análisis cinematográfico antes de recurrir a modelos compactos.
- **Nivel 2 (Modelos Alternativos Ligeros con Cuotas Independientes):**
  - 3º: Modelos de respaldo del primario (`gemini-flash-lite-latest`, `gemini-3.5-flash-lite`, `gemini-3.8-flash`).
  - 4º: Modelos de respaldo del secundario (`openai/gpt-oss-20b`, `groq/compound-mini`, `qwen/qwen3.8-27b`).
- **Nivel 3 (Modo Offline Local):**
  - 5º: Motor determinista en Python sin dependencias externas (`_fallback_heuristic`), enriquecido con el mapa temático bilingüe para responder siempre con recomendaciones de calidad ante cualquier contingencia.
- **Fail-Fast ante 429:** Detección instantánea de cuota agotada sin pausas de reintento innecesarias para conmutar de inmediato al siguiente escalón.

### 2.3. Sincronización Estricta de Idioma
- El frontend transmite explícitamente el idioma actual de la interfaz (`language: "es" | "en"`).
- Tanto el prompt de sistema como el prompt de usuario imponen la directiva crítica en mayúsculas para asegurar que el mensaje de apertura y cada una de las justificaciones (`reason`) se redacten en el idioma solicitado, independientemente de si el texto de búsqueda contiene nombres propios o títulos en inglés.
- El motor heurístico local implementa plantillas bilingües equivalentes.

### 2.4. Experiencia de Usuario y Persistencia
- **Caché de sesión (`sessionStorage`):** Al navegar hacia la ficha de detalle de un título recomendado y retroceder con el navegador, las recomendaciones y el prompt previo se conservan intactos sin forzar un nuevo llamado a la API.
- **Sincronización bidireccional:** Al alternar el estado de un título (favorito, visto, watchlist) desde la card o desde la página de detalle, el estado visual de la tarjeta recomendada se actualiza en tiempo real.
- **Diferenciación visual clara:** Cada tarjeta recomendada cuenta con badges explícitos de `Película` o `Serie de TV` y la justificación personalizada redactada por el asistente.
