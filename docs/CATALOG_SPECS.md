# CATALOG_SPECS.md — Especificaciones del Catálogo y Reglas de Negocio

Este documento define en detalle las reglas de negocio, criterios de curación, transiciones de estado y fórmulas de calificación de CineTrack, complementando las especificaciones iniciales del proyecto.

---

## 1. Secciones del Catálogo de Inicio (Home)

La pantalla principal (`GET /api/v1/home`) presenta colecciones curadas para descubrimiento de contenido, respetando el toggle global de tipo (`tipo=movie`, `tipo=tv` o `None` para catálogo unificado).

| Sección | Filtro / Ventana Temporal | Criterios de Calificación y Votos | Pool de Selección | Muestra en Home | Ordenamiento | Extensión "Ver más" |
|---|---|---|---|---|---|---|
| **New Releases** | Últimos 60 días (`fecha_estreno >= hoy - 60d`) | Sin mínimo | N/A (directo) | Top 10 | `fecha_estreno DESC, popularidad DESC` | Sí (`/titles?sort_by=newest`) |
| **Trending** | Últimos 90 días (`fecha_estreno` o última temporada) | Sin mínimo | N/A (directo) | Top 10 | `popularidad DESC` | No (fijo top 10) |
| **Classics** | Antigüedad > 20 años (`fecha_estreno <= año_actual - 20`) | `rating >= 7.5` y $\ge 500$ votos | Top 50 más populares | Muestra aleatoria de 10 | `popularidad DESC` (en pool) | Sí (`/titles?sort_by=classics`) |
| **Top Rated** | Todo el catálogo histórico | Votos $\ge 100$ | Top 100 con mayor rating | Muestra aleatoria de 10 | `rating_unificado DESC, votos DESC` | Sí (`/titles?sort_by=rating`) |
| **By Genre** | Por cada género con $\ge 10$ títulos | Sin restricción | Top 100 del género | Muestra aleatoria de 10 por género | `popularidad DESC` | Sí (`/titles?genero_id=X`) |
| **Others** | Consolidado de géneros con $< 10$ títulos | Sin restricción | Top 100 géneros minoritarios | Muestra aleatoria de 10 | `popularidad DESC` | Sí |

### 1.1. Reglas Específicas por Sección

1. **New Releases:**
   - Solo incluye estrenos absolutos dentro de la ventana de 60 días (`HOME_NEW_RELEASES_DAYS = 60`).
   - Para series, solo ingresan aquellas cuyo estreno de la **primera temporada** ocurrió dentro de la ventana (no ingresan por estrenar nueva temporada).
2. **Trending:**
   - Considera producciones con movimiento reciente en una ventana de 90 días (`HOME_TRENDING_DAYS = 90`).
   - Para series, ingresan si la fecha de estreno de la serie o la fecha de emisión de su **última temporada** entra en la ventana de 90 días.
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
