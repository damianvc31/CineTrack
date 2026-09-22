# CATALOG_SPECS.md — Especificaciones del Catálogo y Reglas de Negocio

Este documento define en detalle las reglas de negocio, criterios de curación, transiciones de estado y fórmulas de calificación de CineTrack, complementando las especificaciones iniciales del proyecto.

---

## 1. Secciones del Catálogo de Inicio (Home)

La pantalla principal (`GET /api/v1/home`) presenta colecciones curadas para descubrimiento de contenido, respetando el toggle global de tipo (`tipo=movie`, `tipo=tv` o `None` para catálogo unificado).

| Sección | Filtro / Ventana Temporal | Criterios de Calificación y Votos | Pool de Selección | Muestra en Home | Ordenamiento | Extensión "Ver más" |
|---|---|---|---|---|---|---|
| **New Releases** | Últimos 30 días (`fecha_estreno >= hoy - 30d`) | Sin mínimo | N/A (directo) | Top 10 | `fecha_estreno DESC, popularidad DESC` | Sí (`/titles?section=new_releases`) |
| **Trending** | Últimos 90 días (`fecha_estreno` o último episodio) | Percentil de popularidad $\ge 80\%$ (`popularidad_percentil >= 0.80`) | N/A (directo) | Top 10 | `popularidad DESC` | Sí (`/titles?section=trending`) |
| **Classics** | Antigüedad > 20 años (`fecha_estreno <= año_actual - 20`) | `rating >= 7.5` y $\ge 500$ votos | Top 100 más populares | Muestra aleatoria de 10 | `popularidad DESC` (en pool) | Sí (`/titles?section=classics`) |
| **Top Rated** | Todo el catálogo histórico | Votos $\ge 500$ (`HOME_TOP_RATED_MIN_VOTES`) | Top 100 con mayor rating | Muestra aleatoria de 10 | `rating_unificado DESC, votos DESC` | Sí (`/titles?section=top_rated`, acotado a los Top 100) |
| **By Genre** | Por cada género con $\ge 10$ títulos | Sin restricción | Top 100 del género | Muestra aleatoria de 10 por género | `popularidad DESC` | Sí (`/titles?genero=Nombre` o `genero_id=X`) |

### 1.1. Reglas Específicas por Sección

1. **New Releases:**
   - Solo incluye estrenos absolutos dentro de la ventana de 30 días (`HOME_NEW_RELEASES_DAYS = 30`).
   - Para series, solo ingresan aquellas cuyo estreno de la **primera temporada** ocurrió dentro de la ventana (no ingresan por estrenar nueva temporada).
2. **Trending:**
   - Considera producciones con movimiento reciente en una ventana de 90 días (`HOME_TRENDING_DAYS = 90`) y con un percentil de popularidad mínimo del 80% (`HOME_TRENDING_MIN_POPULARITY_PERCENTILE = 0.80`).
   - Para series, ingresan si la fecha de estreno de la serie o la fecha de emisión de su **último episodio emitido** entra en la ventana de 90 días. Se ignora cualquier temporada placeholder que carezca de episodios.
3. **Classics:**
   - **Exclusivo de películas:** Si el usuario selecciona el toggle `tipo=tv`, la sección devuelve una lista vacía `[]`.
   - Requiere superar un umbral exigente de consagración: rating unificado $\ge 7.5$ (`HOME_CLASSICS_MIN_RATING`) y al menos 500 votos registrados (`HOME_CLASSICS_MIN_VOTES`).
   - Del pool de las 100 películas clásicas más populares (`HOME_CLASSICS_POOL_SIZE = 100`), se selecciona una muestra aleatoria de 10 cada vez para dar dinamismo a la Home.
4. **Top Rated:**
   - Reemplaza el concepto de "Recomendados generales" previo al motor de IA.
   - Requiere un mínimo de 500 votos (`HOME_TOP_RATED_MIN_VOTES = 500`) para evitar sesgos de obras con calificaciones perfectas pero pocos votos.
   - En el catálogo (`/catalog?section=top_rated`), la sección está acotada estrictamente a los 100 títulos mejor puntuados del catálogo (`HOME_TOP_RATED_POOL_SIZE = 100`), ordenados por calificación unificada descendente.
5. **By Genre:**
   - Si un género tiene $\ge 10$ títulos en la base (`HOME_GENRE_MIN_TITLES_FOR_CAROUSEL`), se renderiza en su propio carrusel horizontal con una muestra de hasta 10 títulos del pool de los 100 más populares de dicho género.

### 1.2. Regla Transversal: Preservación de Títulos en Home
- Los títulos ya vistos (`vista`) o en seguimiento (`siguiendo`) **se preservan en todos los carruseles de Home** con sus respectivos indicadores visuales y badges, evitando vaciar o desvirtuar las colecciones curadas (*Trending, New Releases, Classics, etc.*).
- Las tarjetas (`TitleCard`) renderizan el estado contextual del usuario autenticado de forma no intrusiva sin alterar la composición ni el orden curado de las secciones.

---

## 2. Máquina de Estados de Título

Cada usuario mantiene un registro individual de interacción con cada título (`EstadoUsuarioTitulo`), estructurado en dos dimensiones independientes:

1. **Favorito (`favorito: bool`):** Marca booleana independiente del estado de consumo. Una obra puede ser favorita estando en watchlist, viéndose o ya vista.
2. **Estado de Seguimiento (`estado: str | null`):** Estado mutuamente excluyente:
   - `watchlist`: Título guardado para ver en el futuro.
   - `siguiendo`: Serie que se está viendo activamente.
   - `vista`: Película o serie completada.
   - `abandonada`: Serie descartada antes de finalizar (estado derivado cuando `estado` es `null` en BD y `episodios_vistos > 0`).
   - `null`: Título sin seguimiento activo.

### 2.1. Transiciones Atómicas en Series
- Marcar cualquier episodio como visto (`POST /watch`) transiciona automáticamente la serie a `siguiendo` si no estaba en ese estado.
- Al marcar el **último episodio pendiente** de una serie, esta transiciona automáticamente a `vista`.
- Si se desmarca un episodio de una serie con estado `vista`, esta regresa automáticamente a `siguiendo`.
- **Abandono explícito (`POST /titles/{id}/unfollow`):** Si la serie se encuentra en `siguiendo`, pasa a `SinEstado` (`estado = null` en BD) conservando intactos todos los episodios vistos en `EpisodioVisto`, deduciéndose como abandonada.
- **Reanudación directa (`POST /titles/{id}/follow`):** Permite retomar una serie abandonada con episodios vistos previos, regresando directamente a `siguiendo` sin forzar la alteración del checklist de episodios.

---

## 3. Calificación Ponderada Unificada y Motor de Reseñas

Para evitar la fricción de mostrar puntajes dispares, CineTrack calcula una calificación única ponderada:

$$\text{Rating Unificado} = \frac{(\text{vote\_average\_tmdb} \times \text{vote\_count\_tmdb}) + \sum_{i=1}^{N} \text{puntaje\_usuario}_i}{\text{vote\_count\_tmdb} + N}$$

- **Reseñas de TMDB:** Cualitativas. Se importan hasta 20 reseñas externas por obra (`TMDB_REVIEWS_PER_TITLE_LIMIT = 20`) con insignia distintiva (*TMDB Review*) para dar riqueza testimonial sin alterar la ponderación numérica (sus calificaciones ya forman parte del `vote_average_tmdb`).
- **Reseñas de CineTrack y Escala Decimal en Saltos de 0.5:**
  - Los usuarios pueden calificar en una escala de **0.0 a 10.0 en múltiplos exactos de 0.5** (ej. 7.0, 7.5, 8.0, 8.5, etc.).
  - **Calificación Opcional:** El puntaje es opcional (`puntaje = None` / `-`). Si el usuario opta por emitir una reseña puramente textual, esta no ingresa en la fórmula de promedio ponderado, evitando penalizaciones o sesgos numéricos.
  - **Regla Estricta de 1 Reseña por Usuario:** Cada usuario solo puede emitir una única reseña por título. Si ya existe una, la interfaz presenta su propia reseña con opciones de edición in-place (lápiz) y eliminación segura (tacho de basura).
  - **Condición de Visualización:** Para redactar una nueva reseña, el título debe haber sido marcado previamente como visto (`vista`). Se preserva el derecho a editar o eliminar reseñas existentes en todo momento.
  - **Recálculo Atómico:** Toda inserción, actualización o eliminación (`DELETE /api/v1/titles/{id}/reviews`) dispara de forma atómica el recálculo de `rating_unificado` en la base de datos.

---

## 4. Ingesta Inicial del Catálogo

La población inicial del catálogo (`--initial` o `/admin/sync/initial`) está diseñada para balancear obras populares contemporáneas con clásicos históricos:

- **Cuotas Objetivo:** Parametrizables vía configuración (`TMDB_INGEST_MOVIES_TARGET = 1000`, `TMDB_INGEST_SERIES_TARGET = 1000`).
- **Estrategias de Prioridad (`TMDB_INGEST_PRIORITY`):**
  - `popular_first` (predeterminada): Ingesta primero la mitad de la cuota (500 títulos) ordenados por popularidad descendente para garantizar cartelera actual, y completa la mitad restante con los títulos mejor calificados históricamente que superen el umbral de representatividad (`vote_count >= 100`).
  - `toprated_first`: Invierte la estrategia, priorizando las 500 obras maestras mejor calificadas y completando la cuota con títulos populares.
- **Idempotencia y Tolerancia a Fallos:** Si un título ya existe en la base (mismo `tmdb_id` y `tipo`), actualiza sus datos sin duplicar. Si un título puntual falla durante la importación, se ejecuta un rollback aislado de esa obra y el bucle continúa paginando hasta alcanzar la cuota objetivo requerida.

---

## 5. Sincronización Diaria y Detección de Cambios

El proceso de sincronización periódica (`--daily` o `/admin/sync/daily`) mantiene el catálogo al día de forma autónoma con mínimo consumo de cuota de API externa mediante tres reglas de negocio desacopladas del estado de los usuarios:

1. **Detección Desatendida de Cambios vía `/changes` de TMDB:** Consulta los endpoints `/tv/changes` y `/movie/changes` dentro de una ventana temporal móvil (`TMDB_CHANGES_HOURS_WINDOW`, default 48 horas / 2 días) para identificar modificaciones en metadatos, nuevos episodios, temporadas o cambios de estado de emisión (`Ended`, `Returning Series`, `Canceled`) en TMDB, actualizando atómicamente cualquier serie o película del catálogo local que haya variado.
2. **Ingesta Autónoma de Estrenos Recientes en Cartelera:** Detecta películas estrenadas en los últimos 15 días (`TMDB_DAILY_SYNC_DAYS_WINDOW = 15`) que superen un umbral de relevancia (`popularity >= 10.0`) y las incorpora automáticamente al catálogo local (respetando `allow_unreleased=False` por defecto).
3. **Recálculo Estadístico de Percentiles y Ratings:** Tras actualizar el catálogo, recalcula la distribución estadística de popularidad (`popularidad_percentil`) y los promedios ponderados (`rating_unificado`) para todos los títulos.

---

## 6. Enriquecimiento de Metadatos y Créditos de Elenco

Durante la importación o sincronización de cualquier título, se aplican reglas de filtrado y estructuración crediticia:

- **Dirección y Guion:** Se deduplican directores y creadores. Para guionistas se concatenan hasta un máximo de 3 autores principales (`TMDB_CREW_WRITERS_LIMIT = 3`).
- **Elenco Principal Jerarquizado con Fotos:** Se limita el reparto a los 15 actores principales más relevantes (`TMDB_CAST_LIMIT = 15`), ordenados por la jerarquía crediticia oficial de TMDB (`orden`).
- **Fotografía de Actores (Top Cast):** Cada actor persiste su imagen oficial de TMDB (`foto_url`, resolución `w185`) en el modelo `Actor`. Para títulos ya ingestados, el job administrativo `populate_actor_photos` descarga y vincula las fotos faltantes de forma asíncrona con control de tasa de TMDB. En la UI, se renderiza la sección "Top Cast" con avatares circulares y nombres de personajes por encima de las temporadas en series y debajo de la sinopsis en películas.
- **Atributos de Personaje:** En la relación N:M (`titulos_elenco`) se persiste explícitamente el nombre del papel interpretado (`personaje`) y su número de orden para renderizar fichas de reparto fidedignas en la UI.
- **Jerarquía Episódica:** En series de televisión se importan todas las temporadas y episodios regulares, persistiendo números de episodio, fecha de emisión exacta (`air_date`) y sinopsis individual.
- **Omisión de Temporadas Vacías:** Únicamente se persisten temporadas que contengan al menos un episodio emitido o programado. Las temporadas placeholder de TMDB con 0 episodios son omitidas automáticamente para evitar ruido visual en la UI, acordeones vacíos e inflación artificial del conteo de temporadas de la serie.
- **Persistencia de Fecha de Temporada:** Cada temporada guarda su fecha de estreno oficial o la fecha del primer episodio emitido, alimentando con exactitud los cálculos cronológicos.

---

## 7. Importación Manual por JSON con Búsqueda Inteligente

El catálogo permite la incorporación manual de obras mediante archivos JSON estructurados (`--import-json <path>` o `/admin/sync/import-json`):

- **Plantillas Estándar:** La estructura de entrada sigue los contratos definidos en `docs/templates/template_pelicula.json` y `template_serie.json`.
- **Resolución Inteligente de Identificador:** Si el registro JSON omite el `id_tmdb`, el importador ejecuta una búsqueda por título y año en TMDB para descubrir y vincular el ID canónico oficial.
- **Rechazo de Obras Huérfanas:** Si un título no cuenta con `id_tmdb` y no puede ser resuelto en TMDB, se rechaza con un error explícito. Esto previene la existencia de registros huérfanos que no puedan beneficiarse de la sincronización diaria, imágenes o metadatos de episodios.

---

## 8. Explorador de Catálogo y Parámetros de Consulta (`GET /api/v1/titles`)

El endpoint de listado paginado separa de forma ortogonal el filtro de colección, los filtros de metadatos y el criterio de ordenamiento:

| Parámetro | Tipo | Descripción | Opciones / Ejemplos |
|---|---|---|---|
| `section` | string | Filtro por colección curada de la Home | `new_releases`, `trending`, `classics`, `top_rated`, `others` |
| `tipo` | string | Discriminador de tipo de obra | `movie`, `tv` |
| `genero` | string | Filtrado por nombre de género (case-insensitive) | `Drama`, `Fantasy`, `Action`, `Comedy` |
| `genero_id` | int | Filtrado por ID numérico de género | `18`, `14`, `28` |
| `actor` | string | Filtrado por nombre de actor del elenco | `DiCaprio`, `Tom Cruise`, `Bryan Cranston` |
| `actor_id` | int | Filtrado por ID numérico de actor | `1`, `150` |
| `q` | string | Búsqueda abierta por texto | Coincidencias en título, director, guionista y elenco |
| `sort_by` | string | Criterio puro de ordenamiento | `popularity` *(default)*, `rating`, `release_date`, `title` |
| `order` | string | Dirección del orden | `desc` *(default)*, `asc` |
| `page` / `page_size` | int | Paginación estándar | Default `page=1`, `page_size=20` (máx 100) |

- **Badge de Popularidad:** Todas las respuestas de tarjetas (`TitleCardResponse`) exponen el campo `popularidad_percentil: float` (0.0 a 1.0) para que la interfaz pueda renderizar directamente el indicador visual de tendencia (🔥 xx%).

---

## 9. Expansión Selectiva del Catálogo por Géneros (Criterio 1: `--expand`)

Para garantizar balance temático y profundidad en géneros específicos sin realizar una ingesta masiva ciega, el sistema provee el job CLI `--expand` y el endpoint administrativo `/api/v1/admin/sync/expand`:

- **Mecanismo de Descubrimiento:** Utiliza los endpoints `/discover/movie` y `/discover/tv` de TMDB aplicando filtros combinados de calidad:
  - Umbral mínimo de votos: `TMDB_EXPAND_MIN_VOTE_COUNT = 300` (configurable).
  - Calificación promedio mínima: `TMDB_EXPAND_MIN_VOTE_AVERAGE = 7.0` (configurable).
  - Objetivo por género: `TMDB_EXPAND_TARGET_PER_GENRE = 50` (configurable, calculando dinámicamente las páginas necesarias).
  - Restricción de obras estrenadas: Por defecto (`allow_unreleased=False`), filtra únicamente producciones que ya hayan tenido estreno comercial real (`primary_release_date.lte` y `first_air_date.lte` a la fecha actual).
- **Idempotencia Absoluta:** Obras ya presentes en el catálogo son ignoradas sin consumir llamadas de créditos ni duplicar registros, avanzando en la paginación hasta cumplir la cuota objetivo de títulos nuevos.
- **Saneamiento de Obras No Estrenadas (`--cleanup-unreleased`):** Elimina películas con fecha de estreno futura y series que carezcan de temporadas estrenadas en emisión, recalculando percentiles para mantener el catálogo limpio.

---

> *Para las especificaciones técnicas, grounding estricto y cascada jerárquica de resiliencia del Asistente de Recomendaciones con IA, consultar [docs/ARQUITECTURA_RECOMENDADOR.md](ARQUITECTURA_RECOMENDADOR.md).*



