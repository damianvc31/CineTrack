# Arquitectura del Recomendador Inteligente (RAG Híbrido & Factor Sorpresa) — Fase 11

Este documento detalla la arquitectura, el flujo de datos, los modelos matemáticos y las decisiones de diseño del sistema de recomendaciones de CineTrack, consolidado en la **Fase 11** con un enfoque **Híbrido (Vectorial + SQL + Heurístico)**, orquestación de **Modelos de Razonamiento (Reasoning Models)**, **Resiliencia Multiclave** y **Modulación por Variedad / Factor Sorpresa**.

---

## 1. El Problema del Enfoque Vectorial Puro
La similitud semántica mediante vectores es excepcional para capturar el "concepto" o la "vibra" de una película (ej. buscar "tensión claustrofóbica" y encontrar *Alien*). Sin embargo, los vectores puros son deficientes procesando **restricciones lógicas duras**. 

Si un usuario pide: *"Películas de robos, pero NO quiero comedias"*, un modelo vectorial puro buscará textos semánticamente cercanos a la palabra "comedia" y terminará recomendando exactamente lo que el usuario quería evitar.

---

## 2. Solución: Flujo Híbrido en 5 Pasos

Para resolver esto de forma óptima en latencia, cuota y precisión, el Recomendador opera como un pipeline de 5 etapas:

```
[Prompt Usuario + Nivel Variedad] 
   ➔ 1. Validación y Sanitización (0ms / 0 llamadas)
   ➔ 2. Extracción Determinista de Filtros Duros (0ms / 0 llamadas)
   ➔ 3. Búsqueda Híbrida Modulada por Variedad: pgvector (Neon) ó Léxica (SQLite) (1 llamada embedding)
   ➔ 4. Grounding & Justificación con Cascada Multi-Nivel y Multi-Key (1 llamada LLM)
   ➔ 5. Hidratación de TitleCards & Respuesta UI
```

### Paso 1: Validación y Sanitización Inmediata
- **Objetivo:** Evitar llamadas costosas a bases de datos y APIs externas si el prompt es ilegítimo.
- **Mecanismo (`is_unintelligible_prompt`):** Filtra determinísticamente caracteres aleatorios, secuencias corruptas o teclado machacado (ej. strings sin vocales o repeticiones absurdas). Admite combinaciones alfanuméricas naturales ("80s", "sci-fi", "twists").
- **Salida temprana:** Si el prompt es ininteligible, el sistema retorna inmediatamente una respuesta de aclaración amigable (`clarification_needed`) con sugerencias predefinidas, **sin tocar la base de datos ni consumir APIs de IA**.

### Paso 2: Extracción Determinista de Intención y Restricciones Duras
- **Objetivo:** Separar la intención temática conceptual de las exclusiones lógicas estrictas.
- **Decisión de Diseño (Extracción Determinista vs LLM):** En lugar de intercalar una llamada previa a un LLM (que agregaría 1.5–2.5 segundos de latencia y duplicaría el consumo de cuota por minuto), este paso se resuelve de forma determinista mediante reglas léxicas de alta velocidad:
  1. **Negaciones Duras (`GENRE_NEGATION_MAP`):** Mapea frases como *"sin animación"*, *"cero terror"* o *"nada de romance"* directamente a cláusulas de exclusión SQL (`WHERE id NOT IN ...`). Esto garantiza un 100% de fiabilidad matemática sin alucinaciones de modelos de lenguaje.
  2. **Rangos Temporales y Décadas:** Mapea menciones como *"ochentas"*, *"80s"*, *"años 90"*, *"clásicos"* o *"estrenos"* a rangos de años sobre `fecha_estreno`.
  3. **Tipo de Título:** Detecta intenciones de series vs películas (`tipo == 'movie'` o `'tv'`).
  4. **Biblioteca de Vistas del Usuario:** Detecta si el usuario pide *"solo vistas"*, *"ya vistas"* o si deben excluirse por defecto sus títulos marcados como `'vista'`.
  5. **Setting Intent vs Origin Intent:** Distingue entre ambientación geográfica (ej: *"ambientada en Buenos Aires"*) y país de producción (ej: *"cine argentino"*).

### Paso 3: Búsqueda Híbrida Modulada por Variedad (SQL + pgvector / SQLite)
- **Generación del Embedding:**
  Se invoca a la API de **Google Embeddings (`gemini-embedding-001`)** fijando `outputDimensionality: 768` para vectorizar la intención semántica del prompt.
- **Modulación por Variedad en el RAG:**
  Los umbrales de votos mínimos y filtros de calidad se ajustan dinámicamente según el nivel de variedad (`VERY_LOW`, `LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH`):
  - **Multiplicador de Votos:** Escala los umbrales base (`MIN_VOTES_THEMATIC=80`, `MIN_VOTES_FALLBACK=150`, `MIN_VOTES_VECTOR=25`) desde **1.8x** en `VERY_LOW` (exige alta popularidad masiva) hasta **0.3x** en `VERY_HIGH` (abre la puerta a obras de nicho poco conocidas).
  - **Filtro de Rating Estricto (`VERY_LOW`):** Exige `rating_unificado >= 7.5` para garantizar solo clásicos consagrados.
  - **Exención de Entidades Directas:** Si el usuario busca un director, actor o título específico (ej: *"películas dirigidas por Ricardo Darín"* o *"David Lynch"*), este filtro de rating se desactiva para evitar que obras singulares queden fuera.
  - **Guardrail de Inanición (Starvation Protection):** Si la cantidad de candidatos tras aplicar los filtros de variedad es inferior a 3, el sistema relaja automáticamente las restricciones para asegurar que nunca se devuelvan 0 recomendaciones.
- **Bifurcación por Dialecto de Base de Datos:**
  - **En PostgreSQL (Neon Dev / Producción):**
    Aplica una consulta dinámica en SQLAlchemy con índice HNSW (`vector_cosine_ops`), ordenando los candidatos por distancia coseno y combinándolos con búsquedas léxicas temáticas para un pool curado de **20 a 35 candidatos**.
  - **En SQLite Local (`.env.local` / Offline):**
    Detecta automáticamente que el dialecto no es PostgreSQL, omitiendo la vectorización y utilizando búsqueda temática léxica y ponderación por popularidad TMDB.

### Paso 4: Grounding y Justificación (Cascada Multi-Nivel, Multi-Key y Modelos de Razonamiento)
Con los candidatos preseleccionados, se invoca al LLM para seleccionar entre 2 y 5 títulos y redactar la justificación.

1. **Clasificación Dinámica de Modelos (`AI_REASONING_MODELS`):**
   A través de la variable de entorno `AI_REASONING_MODELS` (por defecto: `openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b`), el sistema clasifica dinámicamente qué modelos son de razonamiento:
   - **Modelos de Razonamiento:** Reciben `reasoning_effort` ("low", "medium", "high") y una temperatura calibrada en el rango 0.7–1.2 para armonizar con el esfuerzo cognitivo.
   - **Modelos Estándar (Gemini, Llama):** Reciben únicamente temperatura en el rango 0.1–0.9 sin el parámetro `reasoning_effort`, evitando errores HTTP 400.
2. **Directivas Semánticas Explícitas en el Prompt:**
   Para evitar que los modelos de razonamiento elijan siempre los títulos más populares por inercia, el prompt inyecta directivas de comportamiento claras:
   - `VERY_LOW`: Exige exclusivamente obras universalmente aclamadas y premiadas, vetando propuestas divisivas o de culto menor.
   - `VERY_HIGH`: Prohíbe explícitamente elegir títulos obvios o comerciales si hay alternativas fascinantes, ordenando buscar joyas ocultas, cine de autor o culto internacional.
3. **Cascada Jerárquica y Resiliencia Multiclave:**
   - **Nivel 1 (Modelos Insignia):**
     1. Gemini Insignia (`gemini-3.6-flash`): Prueba todas las API Keys configuradas (`GEMINI_API_KEY`) rotando ante 429/503.
     2. Groq Insignia (`openai/gpt-oss-120b`): Si Gemini falla en todas sus claves, prueba todas las API Keys de Groq (`GROQ_API_KEY`).
   - **Nivel 2 (Modelos de Respaldo / Fallbacks):**
     1. Fallbacks de Gemini: `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-flash-lite-latest` (iterando todas las claves).
     2. Fallbacks de Groq: `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` (iterando todas las claves).
   - **Nivel 3 (Fallback Heurístico Offline):**
     Si todos los proveedores externos fallan o hay corte total de internet, un motor determinístico local puntúa los candidatos por coincidencias de texto, afinidad de géneros y popularidad, garantizando una tasa de disponibilidad del **100%**.

### Paso 5: Hidratación de TitleCards y Respuesta UI
- El endpoint toma los IDs de los títulos recomendados por el LLM, los hidrata con la metadata completa desde la base de datos (posters, directores, rating unificado, votos) y los devuelve a la interfaz junto a los metadatos `provider_used` y `model_used` para auditoría y trazabilidad.

---

## 3. Matriz de Modulación por Variedad (Slider Factor Sorpresa)

| Nivel UI | Clave Enum | Multiplicador Votos RAG | Filtro Rating RAG | Temp Reasoning | Reasoning Effort | Temp Standard | Enfoque Semántico |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Clásica** | `VERY_LOW` | 1.8x | $\ge 7.5$ obligatorio | 0.7 | low | 0.1 | Apuestas seguras, obras consagradas y premiadas. |
| **Moderada** | `LOW` | 1.4x | Sin corte duro | 0.8 | low | 0.3 | Obras consolidadas con sólida reputación crítica. |
| **Balanceada** | `MEDIUM` | 1.0x | Sin corte duro | 1.0 | medium | 0.5 | Equilibrio entre títulos célebres y afines interesantes. |
| **Exploratoria**| `HIGH` | 0.6x | Sin corte duro | 1.1 | medium | 0.7 | Búsqueda amplia más allá de lo evidente; propuestas indie. |
| **Creativa** | `VERY_HIGH` | 0.3x | Sin corte duro | 1.2 | high | 0.9 | Máximo factor sorpresa; joyas ocultas, cine de autor y culto. |

---

## 4. Persistencia e Interacción con el Perfil de Usuario

- **Columna en Base de Datos:** Campo `preferencia_variedad_ia` en la tabla `usuarios` (Alembic `0007_user_variety_preference.py`).
- **Configuración Global por Entorno:** `AI_RECOMMENDER_DEFAULT_VARIETY=MEDIUM` en archivos `.env` y Render para usuarios invitados o sin preferencia explícita.
- **Interfaz de Usuario:**
  - **Ajustes (`SettingsPage.tsx`):** Slider continuo de 5 puntos con guías fijas (*Clásica* en el extremo izquierdo, *Balanceada (Recomendado)* fija en el centro, y *Creativa* en el extremo derecho) y tarjeta descriptiva dinámica.
  - **Recomendador (`RecommendationsPage.tsx`):** Selector rápido en barra superior con badge visual en las tarjetas de recomendación indicando el nivel activo.
- **Interacción con Historial:**
  - **Exclusión Automática:** Por defecto, los 49+ títulos vistos se excluyen del pool de candidatos para priorizar descubrimiento.
  - **Inclusión Mixta (`allow_rewatch`):** Si el prompt contiene frases como *"puedes incluir vistas"*, combina armónicamente obras no vistas para descubrir con obras vistas para revivir.
  - **Exclusivo de Vistas (`only_watched`):** Si el prompt contiene frases como *"solo de las que ya vi"*, filtra candidatos exclusivamente entre sus obras vistas.

---

## 5. Costos, Cuotas y Operatoria de Infraestructura

- **Motor Vectorial:** Extensión nativa `pgvector` sobre Neon Serverless Postgres (`CREATE EXTENSION vector`), con índice HNSW (`vector_cosine_ops`) sobre 3.945 títulos.
- **Cuota de Embeddings:**
  - Google AI Studio Free Tier impone un límite de **1.000 embeddings/día por clave** y **15 requests/minuto**.
  - Los scripts de sincronización (`sync_embeddings.py`) implementan una cadencia de 4.0 segundos y enfriamiento automático de 20s para no disparar errores 429.
- **Desacoplamiento para Desarrollo Local:**
  - La base de datos local SQLite opera 100% desacoplada: tanto el recomendador como los jobs diarios de TMDB ignoran las operaciones vectoriales cuando detectan `sqlite`, permitiendo trabajar offline sin gastar cuotas de APIs externas.
