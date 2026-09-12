# CATALOG_SPECS.md — Especificaciones del Catálogo y Reglas de Negocio

Este documento define en detalle las reglas de negocio, criterios de curación, transiciones de estado y fórmulas de calificación de CineTrack, complementando las especificaciones iniciales del proyecto.

---

## 1. Secciones del Catálogo de Inicio (Home)

La pantalla principal (`GET /api/v1/home`) presenta colecciones curadas para descubrimiento de contenido, respetando el toggle global de tipo (`tipo=movie`, `tipo=tv` o `None` para catálogo unificado).

| Sección | Filtro / Ventana Temporal | Criterios de Calificación y Votos | Pool de Selección | Muestra en Home | Ordenamiento | Extensión "Ver más" |
|---|---|---|---|---|---|---|
| **New Releases** | Últimos 60 días (`fecha_estreno >= hoy - 60d`) | Sin mínimo | N/A (directo) | Top 10 | `fecha_estreno DESC, popularidad DESC` | Sí (`/titles?section=new_releases`) |
| **Trending** | Últimos 90 días (`fecha_estreno` o último episodio) | Sin mínimo | N/A (directo) | Top 10 | `popularidad DESC` | Sí (`/titles?section=trending`) |
| **Classics** | Antigüedad > 20 años (`fecha_estreno <= año_actual - 20`) | `rating >= 7.5` y $\ge 500$ votos | Top 50 más populares | Muestra aleatoria de 10 | `popularidad DESC` (en pool) | Sí (`/titles?section=classics`) |
| **Top Rated** | Todo el catálogo histórico | Votos $\ge 100$ | Top 100 con mayor rating | Muestra aleatoria de 10 | `rating_unificado DESC, votos DESC` | Sí (`/titles?section=top_rated`) |
| **By Genre** | Por cada género con $\ge 10$ títulos | Sin restricción | Top 100 del género | Muestra aleatoria de 10 por género | `popularidad DESC` | Sí (`/titles?genero=Nombre` o `genero_id=X`) |
| **Others** | Consolidado de géneros con $< 10$ títulos | Sin restricción | Top 100 géneros minoritarios | Muestra aleatoria de 10 | `popularidad DESC` | Sí (`/titles?section=others`) |

### 1.1. Reglas Específicas por Sección

1. **New Releases:**
   - Solo incluye estrenos absolutos dentro de la ventana de 60 días (`HOME_NEW_RELEASES_DAYS = 60`).
   - Para series, solo ingresan aquellas cuyo estreno de la **primera temporada** ocurrió dentro de la ventana (no ingresan por estrenar nueva temporada).
2. **Trending:**
   - Considera producciones con movimiento reciente en una ventana de 90 días (`HOME_TRENDING_DAYS = 90`).
   - Para series, ingresan si la fecha de estreno de la serie o la fecha de emisión de su **último episodio emitido** entra en la ventana de 90 días. Se ignora cualquier temporada placeholder que carezca de episodios.
3. **Classics:**
   - **Exclusivo de películas:** Si el usuario selecciona el toggle `tipo=tv`, la sección devuelve una lista vacía `[]`.
   - Requiere superar un umbral exigente de consagración: rating unificado $\ge 7.5$ (`HOME_CLASSICS_MIN_RATING`) y al menos 500 votos registrados (`HOME_CLASSICS_MIN_VOTES`).
   - De las 50 películas clásicas más populares, se selecciona una muestra aleatoria de 10 cada vez para dar dinamismo a la Home.
4. **Top Rated:**
   - Reemplaza el concepto de "Recomendados generales" previo al motor de IA.
   - Requiere un mínimo de 100 votos (`HOME_TOP_RATED_MIN_VOTES`) para evitar sesgos de obras con calificaciones perfectas pero un solo voto.
5. **By Genre y Carrusel "Others":**
   - Si un género tiene $\ge 10$ títulos en la base (`HOME_GENRE_MIN_TITLES_FOR_CAROUSEL`), se renderiza en su propio carrusel horizontal.
   - Los géneros de nicho que no alcanzan los 10 títulos no se descartan: se agrupan ordenados por popularidad en el carrusel de **Others**.

### 1.2. Regla Transversal: Exclusión de Títulos Vistos
Cuando la petición incluye el token JWT de un usuario autenticado:
- Se omiten automáticamente de **todos los carruseles de Home** aquellos títulos que el usuario tenga marcados con `estado == 'vista'`.
- La Home funciona como una vitrina de descubrimiento y exploración continua, evitando recomendar obras ya consumidas.

---

## 2. Máquina de Estados de Título

Cada usuario mantiene un registro individual de interacción con cada título (`EstadoUsuarioTitulo`), estructurado en dos dimensiones independientes:

1. **Favorito (`favorito: bool`):** Marca booleana independiente del estado de consumo. Una obra puede ser favorita estando en watchlist, viéndose o ya vista.
2. **Estado de Seguimiento (`estado: str | null`):** Estado mutuamente excluyente:
   - `watchlist`: Título guardado para ver en el futuro.
   - `siguiendo`: Serie que se está viendo activamente.
   - `vista`: Película o serie completada.
   - `abandonada`: Serie descartada antes de finalizar.
   - `null`: Título sin seguimiento activo.

### 2.1. Transiciones Atómicas en Series
- Marcar cualquier episodio como visto (`POST /watch`) transiciona automáticamente la serie a `siguiendo` si no estaba en ese estado.
- Al marcar el **último episodio pendiente** de una serie, esta transiciona automáticamente a `vista`.
- Si se desmarca un episodio de una serie con estado `vista`, esta regresa automáticamente a `siguiendo`.

---

## 3. Calificación Ponderada Unificada

Para evitar la fricción de mostrar puntajes dispares, CineTrack calcula una calificación única ponderada:

$$\text{Rating Unificado} = \frac{(\text{vote\_average\_tmdb} \times \text{vote\_count\_tmdb}) + \sum_{i=1}^{N} \text{puntaje\_usuario}_i}{\text{vote\_count\_tmdb} + N}$$

- **Reseñas de TMDB:** Cualitativas. Se importan hasta 20 reseñas externas por obra (`TMDB_REVIEWS_PER_TITLE_LIMIT = 20`) para dar riqueza testimonial sin alterar la ponderación numérica (sus calificaciones ya forman parte del `vote_average_tmdb`).
- **Reseñas de CineTrack:** Cada usuario registrado puede emitir una reseña con puntaje de 1.0 a 10.0, recalculando de inmediato el rating consolidado en base de datos.

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

El proceso de sincronización periódica (`--daily` o `/admin/sync/daily`) mantiene el catálogo al día con mínimo consumo de cuota de API externa mediante cuatro reglas de negocio:

1. **Actualización Prioritaria de Series Seguidas:** Identifica todas las series que tengan al menos un usuario activo en estado `siguiendo`. Actualiza su estado de emisión (`Ended`, `Returning Series`, `Canceled`) y descarga atómicamente los nuevos episodios o temporadas recién emitidos.
2. **Detección Desatendida de Cambios vía `/changes`:** Consulta los endpoints `/tv/changes` y `/movie/changes` dentro de una ventana temporal móvil (`TMDB_CHANGES_HOURS_WINDOW`, default 48 horas) para detectar y actualizar cualquier serie o película existente en el catálogo local que haya sufrido modificaciones en TMDB, incluso si ningún usuario la sigue todavía.
3. **Ingesta Autónoma de Estrenos en Cartelera:** Detecta películas estrenadas en los últimos 15 días (`TMDB_DAILY_SYNC_DAYS_WINDOW = 15`) que superen un umbral de relevancia (`popularity >= 10.0`) y las incorpora al catálogo local.
4. **Recálculo de Percentiles:** Tras actualizar el catálogo, se recalcula la distribución estadística de popularidad (`popularidad_percentil`) para todos los títulos.

---

## 6. Enriquecimiento de Metadatos y Créditos de Elenco

Durante la importación o sincronización de cualquier título, se aplican reglas de filtrado y estructuración crediticia:

- **Dirección y Guion:** Se deduplican directores y creadores. Para guionistas se concatenan hasta un máximo de 3 autores principales (`TMDB_CREW_WRITERS_LIMIT = 3`).
- **Elenco Principal Jerarquizado:** Se limita el reparto a los 15 actores principales más relevantes (`TMDB_CAST_LIMIT = 15`), ordenados por la jerarquía crediticia oficial de TMDB (`orden`).
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


