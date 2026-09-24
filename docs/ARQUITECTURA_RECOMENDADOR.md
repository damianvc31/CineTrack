# Arquitectura del Recomendador Inteligente (RAG Híbrido) - Fase 8

Este documento detalla la arquitectura, el flujo de datos y las decisiones de diseño del sistema de recomendaciones de CineTrack, implementado en la Fase 8 hacia un enfoque **Híbrido (Vectorial + SQL)** para solucionar las deficiencias semánticas y de filtrado negativo del recomendador inicial.

---

## 1. El Problema del Enfoque Vectorial Puro
La similitud semántica mediante vectores es excepcional para capturar el "concepto" o la "vibra" de una película (ej. buscar "tensión claustrofóbica" y encontrar *Alien*). Sin embargo, los vectores puros son deficientes procesando **restricciones lógicas duras**. 

Si un usuario pide: *"Películas de robos, pero NO quiero comedias"*, un modelo vectorial puro buscará textos semánticamente cercanos a la palabra "comedia" y terminará recomendando exactamente lo que el usuario quería evitar.

---

## 2. Solución: Flujo Híbrido en 5 Pasos

Para resolver esto de forma óptima en latencia, cuota y precisión, el Recomendador opera como un pipeline de 5 etapas:

```
[Prompt Usuario] 
   ➔ 1. Validación y Sanitización (0ms / 0 llamadas)
   ➔ 2. Extracción Determinista de Filtros Duros (0ms / 0 llamadas)
   ➔ 3. Búsqueda Híbrida: pgvector (Neon) ó Léxica (SQLite) (1 llamada embedding)
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
- **Ventaja Técnica:** Ejecución instantánea (**0 milisegundos**) y cero consumo de cuota de API.

### Paso 3: Búsqueda Híbrida (SQL + pgvector / SQLite)
- **Generación del Embedding:**
  Se invoca a la API de **Google Embeddings (`gemini-embedding-001`)** fijando `outputDimensionality: 768` para vectorizar la intención semántica del prompt.
- **Bifurcación por Dialecto de Base de Datos:**
  - **En PostgreSQL (Neon Dev / Producción):**
    Aplica una consulta dinámica en SQLAlchemy que primero ejecuta las restricciones duras del `WHERE` (géneros excluidos, películas vistas, décadas, tipo), y luego ordena los candidatos por **distancia coseno** con el índice HNSW:
    ```sql
    SELECT titulos.*, (titulos.embedding <=> user_vector) AS distancia
    FROM titulos
    WHERE titulos.tipo = 'movie'
      AND titulos.fecha_estreno BETWEEN '1980-01-01' AND '1989-12-31'
      AND titulos.id NOT IN (SELECT titulo_id FROM titulos_generos WHERE genero_id = :animacion_id)
      AND titulos.id NOT IN (SELECT titulo_id FROM estados_usuarios_titulos WHERE usuario_id = :uid AND estado = 'vista')
    ORDER BY titulos.embedding <=> user_vector ASC
    LIMIT 30;
    ```
    Se combina con una búsqueda temática léxica complementaria (sinopsis, géneros detectados, director) para consolidar un **pool curado de ~35 candidatos**.
  - **En SQLite Local (`.env.local` / Offline):**
    Detecta automáticamente que el dialecto no es PostgreSQL. **Omite el 100% de la vectorización** (cero consumo de cuota) y utiliza búsqueda temática léxica y ponderación por popularidad TMDB.

### Paso 4: Grounding y Justificación (Cascada Multi-Nivel y Multi-Key)
Con los ~35 candidatos preseleccionados, se invoca al modelo de lenguaje para seleccionar entre 2 y 5 títulos definitivos y redactar la justificación en lenguaje natural.

Para garantizar máxima resiliencia ante límites de cuota (HTTP 429), la orquestación sigue este orden jerárquico estricto:

1. **Nivel 1: Modelos Insignia Principales**
   - **Google Gemini Principal (`gemini-3.6-flash`):**
     - Evalúa la primera clave (`GEMINI_API_KEY[0]`).
     - Si recibe 429 o saturación, rota de inmediato a la segunda clave (`GEMINI_API_KEY[1]`).
   - **Groq Cloud Principal (`openai/gpt-oss-120b`):**
     - Si Gemini agota sus claves en el modelo insignia, pasa al modelo insignia de Groq.
     - Rota entre las claves configuradas en `GROQ_API_KEY` ante rate limits.
2. **Nivel 2: Modelos de Respaldo Ligeros (Fallbacks)**
   - Si los dos modelos líderes están saturados, se desciende al Nivel 2:
   - **Fallbacks de Gemini (con multi-clave):** `gemini-flash-lite-latest` ➔ `gemini-3.5-flash-lite` ➔ `gemini-3.8-flash`.
   - **Fallbacks de Groq (con multi-clave):** `openai/gpt-oss-20b` ➔ `groq/compound-mini` ➔ `qwen/qwen3.8-27b`.
3. **Nivel 3: Fallback Heurístico Offline (Garantía 100%)**
   - Si no hay conexión o todos los proveedores externos fallan, un algoritmo matemático determinístico local puntúa los candidatos por coincidencias de texto, afinidad de géneros y popularidad, devolviendo recomendaciones válidas y estructuradas sin fallar nunca.

### Paso 5: Hidratación de TitleCards y Respuesta UI
- El endpoint toma los IDs de los títulos recomendados por el LLM, los hidrata con la metadata completa desde la base de datos (posters, directores, rating unificado, votos) y los devuelve a la interfaz junto al metadato `model_used` para auditoría y trazabilidad.

---

## 3. Composición de los Embeddings

Para que el modelo vectorial no se contamine con "ruido" estadístico, los vectores pre-calculados de cada título se construyen usando **únicamente metadatos conceptuales fuertes**:

**✅ Datos Incluidos en el Vector Base:**
- Título
- Géneros
- Sinopsis principal
- Director o Creadores de TV (aporta peso estilístico)

**❌ Datos Excluidos (y justificación):**
- **Sinopsis de temporadas/episodios:** Diluyen el concepto de la serie con micro-tramas puntuales.
- **Elenco principal:** Engaña al modelo. Si Adam Sandler está en el vector, sus comedias (*Click*) y dramas (*Uncut Gems*) quedarían pegados matemáticamente arruinando la precisión de género. (La búsqueda por actores se filtra vía cláusula SQL exacta).
- **Reseñas:** Altamente subjetivas. Hablan de aspectos técnicos (CGI, ritmo, dirección de cámara) y no del concepto temático u ontológico de la obra.

---

## 4. Manejo de Idioma y Ambigüedad

- **Barrera Multilingüe:** Los prompts en español no requieren traducción. El modelo `gemini-embedding-001` es nativamente multilingüe y mapea conceptos (ej. "películas de robos" y "heist movies") al mismo espacio vectorial con distancia nula.
- **Ambigüedad y Conversación (Clarification Needed):** Si el usuario ingresa un prompt extremadamente vago (ej. *"recomiéndame algo bueno"*), el LLM detecta la falta de intención específica y devuelve `status="clarification_needed"` con preguntas interactivas y sugerencias contrastantes (ej. *"¿Prefieres acción trepidante o un drama para reflexionar?"*) para iniciar un flujo conversacional guiado.

---

## 5. Costos, Cuotas y Operatoria de Infraestructura

- **Motor Vectorial:** Extensión nativa `pgvector` sobre Neon Serverless Postgres (`CREATE EXTENSION vector`), con índice HNSW (`vector_cosine_ops`) sobre 3.864 títulos.
- **Cuota de Embeddings:**
  - Google AI Studio Free Tier impone un límite de **1.000 embeddings/día por clave** y **15 requests/minuto**.
  - Los scripts de sincronización (`sync_embeddings.py`) implementan una cadencia de 4.0 segundos y enfriamiento automático de 20s para no disparar errores 429.
  - Las claves que agotan su cuota diaria (`PerDay`) son desactivadas dinámicamente de la rotación activa para permitir que las claves secundarias continúen.
- **Desacoplamiento para Desarrollo Local:**
  - La base de datos local SQLite opera 100% desacoplada: tanto el recomendador como los jobs diarios de TMDB ignoran las operaciones vectoriales cuando detectan `sqlite`, permitiendo trabajar offline sin gastar cuotas de APIs externas.
