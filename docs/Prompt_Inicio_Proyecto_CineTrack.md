# Prompt de Inicio de Proyecto — App de Seguimiento de Cine y Series

## Misión Principal

Quiero desarrollar una aplicación web de seguimiento de cine y series estilo "TV Time" con arquitectura de 3 capas (Presentación, Lógica y Persistencia). El objetivo es permitir a los usuarios gestionar su biblioteca multimedia y recibir recomendaciones personalizadas basadas en IA.

## Funcionalidades Clave

### 1. Multi-usuario con login mínimo
Usuario + contraseña (hash), sin verificación de email ni recuperación de clave — el objetivo es persistencia real entre dispositivos, no un sistema de seguridad completo. Auth es un requisito no funcional liviano, no el foco central de la app.

> Nota: si en el futuro se evalúa comercializar la app, este esquema de login probablemente deba reemplazarse por algo más robusto (verificación de email, recuperación de clave, quizás OAuth) — no es la prioridad de esta etapa.

**Datos de perfil del usuario** (más allá de usuario/contraseña):
- **Ubicación:** país y ciudad como campos separados — no solo para mostrar en el perfil, sirve para regionalizar qué plataformas de streaming mostrarle a cada usuario (punto 10, versión superior).
- **Descripción breve** (bio de texto libre).
- **Fecha de registro:** no configurable por el usuario, se guarda automáticamente al crear la cuenta y se muestra en el perfil ("Miembro desde...").
- **Avatar:** el usuario puede subir uno desde su dispositivo. Si no sube ninguno, usar un default genérico. **Pregunta abierta para la Fase 1 — cómo almacenarlo:** a diferencia de las portadas de TMDB (que ya vienen alojadas externamente), acá sí hay un archivo real que alguien tiene que guardar. Opciones con trade-offs distintos:
  - Un servicio de almacenamiento de objetos externo (ej. S3, Cloudinary) — la opción "correcta" en términos de arquitectura, pero suma una dependencia externa más al proyecto.
  - Guardarlo como archivo estático en el propio servidor — más simple, pero **ojo con el filesystem efímero de Render en sus planes gratuitos/económicos**: los archivos pueden perderse en cada redeploy si no se usa un volumen persistente específicamente configurado para eso.
  - Guardarlo directo en la base de datos como binario — generalmente desaconsejado en general (ver la discusión de por qué, más abajo en carga de datos), pero dado que son archivos chicos y de bajo tráfico (una foto de perfil, no un catálogo entero), podría ser una simplificación aceptable para el alcance de este proyecto. Ninguna de las tres es la respuesta obligada — es una decisión a tomar con criterio en la Fase 1, no algo ya resuelto acá.

### 2. Página principal / exploración
Mostrar a cualquier usuario (logueado o no) una selección de títulos con portada, título y año — en películas, el año simple de estreno; en series, el mismo formato usado en los rankings de estadísticas: "N seasons | AAAA-AAAA" (cantidad de temporadas + rango de años, no solo el año de la primera) — organizados en secciones — **máximo 10 títulos por sección**, con un encabezado clickeable que lleva a una pantalla dedicada listando el catálogo completo de esa sección si el usuario quiere ver más (**excepto Trending**, ver abajo):

- **"Estrenos recientes":** todos los títulos de los últimos 3 meses, ordenados del más reciente al menos reciente. **Sin muestreo aleatorio** — se muestran los 10 más recientes en la pantalla principal, y el resto (si hay más de 10 en la ventana) se ve al extender.
- **"Trending":** títulos de los últimos 6 meses, ordenados de más a menos popular dentro de esa ventana. **Siempre un top 10 fijo, sin pantalla de extensión** — a diferencia de las demás secciones, acá no hay "ver más".
- **"Clásicos" (solo películas):** títulos de más de 20 años de antigüedad. No aplica a series — en el toggle "Series" esta sección no aparece; en "Todos", solo trae películas, ya que una serie de +20 años no es comparable de la misma forma que una película clásica. De un pool de las 50 películas más populares dentro de esa categoría, se muestra una selección aleatoria de 10 en la pantalla principal (rotan entre visitas), y las 50 completas se ven al extender.
- **"Recomendados"** (por puntaje/promedio general, **no** personalizado — eso es aparte, ver punto 8): de un pool de las ~100 películas/series de mejor **puntaje** del catálogo, una selección aleatoria de 10 — varía entre una visita y otra.
- **Por género** (comedia, terror, acción, aventura, documentales, etc.): mismo mecanismo de muestreo que Recomendados, pero el pool se arma por **popularidad**, no por puntaje — de los ~100 títulos más populares de ese género, una selección aleatoria de 10. Como un título puede tener varios géneros a la vez (ver nota técnica del punto 6), es normal y esperado que el mismo título aparezca en más de una sección de género simultáneamente — no es un error a evitar.

Con un toggle de 3 opciones: **"Películas"**, **"Series"**, o **"Todos"** (mezcla ambos tipos en las mismas secciones, salvo Clásicos que es solo películas).

**Regla de reemplazo para evitar huecos:** si alguno de los títulos seleccionados para una sección ya está marcado como **Vista** por el usuario logueado, se reemplaza por el siguiente candidato válido del mismo pool y criterio de esa sección (el resto del top 100/50 para Recomendados/Género/Clásicos, o el siguiente en la ventana de tiempo/orden para Estrenos/Trending), para completar los 10 en vez de mostrar una sección incompleta. Si el pool no alcanza para completar 10 (caso extremo), se muestran los que haya.

**Buscador:** además de buscar por nombre, permitir filtrar por director, guionista y actor/actriz del reparto (similar al buscador de Netflix, sin incluir género). Técnicamente viable sin infraestructura extra — reutiliza la relación de elenco/director que el detalle de película/serie ya necesita (punto 6 y 7), no son datos nuevos a conseguir. Sirve tanto para descubrir contenido nuevo como para localizar rápido títulos que el usuario ya vio.

**Por qué género queda afuera del buscador directo:** los géneros se guardan en la base en el idioma que TMDB los provea (probablemente inglés), sin traducción propia — a diferencia de nombre de título, no tenemos una tabla de traducciones de género por idioma. Buscar por género en español requeriría traducir el término antes de filtrar, lo cual ya es exactamente el trabajo que hace el recomendador (punto 8) vía function calling — no tiene sentido duplicar esa lógica en el buscador simple. Si el usuario quiere navegar por género, usa la pantalla dedicada de ese género (ver arriba) o le pide al recomendador directamente.

**El buscador debe funcionar en cualquier idioma disponible para cada título, no solo en el idioma actual de la interfaz** — si el sitio está en español pero el usuario conoce el título en inglés, debe poder encontrarlo igual. Esto implica indexar para búsqueda todas las traducciones de nombre que TMDB tenga por título, no solo la del idioma seleccionado.

**Datos e interacciones rápidas por título (sin entrar al detalle):**
- Promedio de puntaje combinado + cantidad de votos (ver cómo se compone en el punto 6), y popularidad — **visibles para cualquier usuario, logueado o no**
- Puntaje propio del usuario, si ya calificó ese título — **solo usuarios logueados**
- Los íconos de estado del punto 4: ♥ Favorita, 🔖 Watchlist, 👁 Vista/No vista — **solo usuarios logueados**, mismas reglas de transición ahí definidas, editables directamente desde acá sin entrar al detalle. En series, se suma ❌ Abandonar cuando el título está en "Siguiendo".

**Regla de exclusión:** los títulos que el usuario ya tiene marcados como **Vista** no deben aparecer en ninguna de estas **secciones de exploración** (Estrenos, Trending, Clásicos, Recomendados, por género). Los que están en **Siguiendo**, en **Watchlist**, o sin ningún estado activo (dejó de seguirla) sí siguen apareciendo ahí — recordatorios útiles de que existen y de que podría querer retomarlos.

**La exclusión no aplica al buscador:** si el usuario busca explícitamente un título ya visto, sí debe aparecer en los resultados — con su puntaje propio (si calificó) y la marca de visto visibles, igual que cualquier otro resultado. Es la vía prevista para carga inicial de un usuario nuevo (marcar cosas que ya vio antes de usar la app) y para cualquier otra búsqueda puntual. Ese mismo título, con la misma información, también está disponible en la sección "Vista" del perfil (ver punto 3).

**El ícono del ojo tiene comportamiento distinto según el contexto donde aparece:** en las secciones de exploración, tocarlo para marcar como Vista hace que el título se excluya de esa vista al instante — desaparece de ahí y se reemplaza por otro (ver "Regla de reemplazo" más arriba), ya que Vista no se muestra en exploración. En cambio, en el buscador (exento de esa exclusión), un título ya visto muestra el ojo en su variante tachada (👁‍🗨) — permitiendo "desmarcarlo" directo desde ahí, sin tener que entrar al detalle.

### 3. Secciones del perfil del usuario

El perfil organiza los títulos del usuario en secciones, cada una correspondiente a uno de los estados/flags del punto 4:

- **Favoritos:** todos los títulos marcados con ♥, sin importar su estado de Watchlist/Siguiendo/Vista.
- **Watchlist:** títulos marcados con 🔖, que el usuario todavía no empezó a ver.
- **Siguiendo:** series marcadas automáticamente con ▶️ al ver al menos un episodio, a medio ver — **ordenadas por episodio visto más reciente primero** (no por cuándo entraron a este estado, ver nota técnica del punto 4). Incluye el badge visual 🔥 de actividad reciente si se prioriza esa versión superior — en ese caso, el orden no cambia, solo se suma el filtro/resaltado extra sobre el mismo criterio. Desde acá el usuario puede tocar ❌ para abandonar una serie que ya no quiere continuar.
- **Vista:** títulos marcados con 👁, completados. Es la sección donde aparecen los títulos que el buscador de la pantalla principal permite encontrar (ver regla de exclusión más arriba) — muestra puntaje propio y marca de visto igual que en el buscador.
- **Reseñas:** listado de las reseñas que el usuario escribió, con su puntaje asociado, independientemente de en qué sección esté el título ahora. Desde acá también se puede **agregar una reseña nueva**, eligiendo entre los títulos elegibles que todavía no reseñó — el criterio de elegibilidad depende del tipo: en películas, estar en Vista (punto 6); en series, haber visto al menos un episodio (punto 7).
- **Estadísticas** (versión superior, no esencial): panel con métricas agregadas sobre lo que el usuario vio —
  - Tiempo total visto en películas (horas y minutos)
  - Tiempo total visto en series (horas y minutos) — calculado sumando la duración de los episodios efectivamente marcados como vistos, no la de la serie completa (por eso la duración vive en `Episodio`, no en `Serie` — ver nota en el diagrama)
  - Cantidad de películas vistas
  - Cantidad de series vistas
  - Promedio de películas vistas por semana (desde la fecha de registro, o desde la primera película marcada como vista)
  - **Top 5 títulos** (mezclando películas y series, sin separar) por promedio de puntaje de la comunidad
  - **Top 5 títulos** (mezclando películas y series, sin separar) por popularidad
  - **Top 5 títulos** (mezclando películas y series, sin separar) por **puntaje propio del usuario** — reutiliza el mismo campo `puntaje` de `Reseña` que ya existe, no es un dato nuevo, solo una consulta distinta ordenando por eso en vez del promedio combinado. Si el usuario tiene menos de 5 títulos puntuados, la lista simplemente muestra menos.
  - Para series en cualquiera de los tres rankings, mostrar también la cantidad de temporadas y el rango de años (ej. "10 seasons | 2010-2020") — no es un campo nuevo, se deriva del año mínimo y máximo entre las `fechaEstreno` de sus temporadas (punto 4). Para una serie todavía en emisión, el año más reciente sería el de la última temporada confirmada, no necesariamente "hasta hoy".
  - Gráfico de torta con la distribución de géneros vistos por el usuario — como un título puede tener varios géneros a la vez (punto 6), cada visualización de un título suma a todos sus géneros, no a uno solo
  
  Se calculan al vuelo por defecto (a diferencia del promedio de puntaje del punto 6, acá el alcance de la consulta es solo lo que un usuario vio, no todo el catálogo — no hay necesidad de cachear salvo que se mida un problema real de rendimiento).

Desde cualquiera de estas 6 secciones, el usuario puede entrar al detalle completo de un título tocándolo, igual que desde la pantalla principal.

Todas arrancan vacías para un usuario nuevo — es esperable, no un error de diseño.

### 4. Estados de un título en el perfil del usuario

Cada título tiene un **favorito independiente** más, en series, **3 estados mutuamente excluyentes**. En películas, al no tener episodios, solo aplican dos de los tres (Watchlist / Vista).

**Fechas a registrar (para poder ordenar listas por más reciente primero):** cuándo se marcó como favorito, y cuándo cambió por última vez el estado (Watchlist/Siguiendo/Vista) — son dos fechas independientes, ya que favorito y estado son cosas independientes entre sí.

**Ojo con usar `fechaEstado` para ordenar "Siguiendo" — no sirve para eso.** Ese campo solo cambia cuando el *estado* cambia (ej. al pasar de Watchlist a Siguiendo), no cada vez que se ve un episodio nuevo dentro de ese mismo estado — quedaría pegado en la fecha del primer episodio, no reflejaría la actividad real. Para ordenar **"Siguiendo"** por más reciente, usar el **`MAX(fechaVisto)` de `EpisodioVisto`** para cada título — es el mismo dato que ya usa el badge "Viendo Actualmente" (punto 4), reutilizado acá para el orden. `fechaEstado` sí sirve tal cual para ordenar **Watchlist** y **Vista**, donde no hay una sub-actividad continua que lo vuelva obsoleto.

> **Nota de diseño:** los 3 estados son mutuamente excluyentes a propósito — desacoplarlos (permitiendo combinaciones libres) generaría casos sin significado claro (ej. ¿qué implicaría "Vista" + "Siguiendo" a la vez?) sin un beneficio evidente a cambio.

**Iconografía — 3 botones interactivos + 1 acción condicional:**

| Ícono | Acción | Aplica a |
|---|---|---|
| ♥ (lleno/vacío) | Marcar/desmarcar favorita — independiente de todo | Películas y series |
| 👁 / 👁‍🗨 (tachado) | Marcar/desmarcar **toda la serie** como vista de una — al desmarcar, se desmarcan todos los episodios juntos también | Películas y series |
| 🔖 (lleno/vacío) | Agregar/quitar de **Watchlist** — muestra ▶️ bloqueado en su lugar si el título está en Siguiendo (ver detalle abajo) | Películas y series |
| ❌ (rojo) | **Abandonar serie** — solo visible en el detalle de la serie o en la sección "Siguiendo" del perfil, y solo si la serie está actualmente en "Siguiendo" | Solo series |

**"Siguiendo" no tiene botón propio — es un estado 100% automático.** El usuario nunca lo activa a mano: entra a "Siguiendo" solo cuando se marca un episodio individual como visto (desde el detalle de la serie), sin pasar por ningún ícono dedicado. Como marcador visual de la sección (no un botón, no interactuable), usar **▶️** (play — representa "en curso").

**El ícono 🔖 se bloquea cuando no tiene sentido agregar a Watchlist** — pasa en dos casos, aplica tanto a películas como a series, y en **cualquier lugar donde el ícono aparezca** (tarjetas de exploración en la pantalla principal incluidas, no solo el detalle):
- **Serie en Siguiendo:** en vez del bookmark vacío o lleno, ese espacio muestra **▶️ bloqueado, no interactuable** — evita confundir al usuario mientras la serie ya se está viendo activamente. **Abandonar (❌) no está disponible desde la tarjeta de exploración** — solo existe en el detalle de la serie o en la sección Siguiendo del perfil (ver tabla de iconografía, punto 4); desde Home, el ▶️ es puramente informativo. Para volver a Watchlist desde Siguiendo, el usuario debe primero entrar al detalle y tocar ❌ (Abandonar) — recién ahí el ícono vuelve a mostrar el bookmark interactivo (el progreso de episodios se mantiene igual, ver regla de abajo).
- **Título en Vista (película o serie):** no tiene sentido agregar a Watchlist algo que ya se vio por completo — el ícono queda bloqueado/oculto en ese estado también. La única forma de volver a poder agregarlo a Watchlist es desmarcarlo primero con el ojo tachado (👁, volviendo a "sin estado"), nunca directamente desde Vista.

**Sobre "Viendo Actualmente" (badge, versión superior, no esencial):** no es un estado propio — es un indicador visual **calculado** sobre series que ya están en "Siguiendo", activo si la fecha del último episodio visto está dentro de una ventana de tiempo configurable (ej. últimos 7 días), con ícono 🔥 (alternativa: 👀 — ojos, aunque **comparte base visual con 👁 de "Vista"**, riesgo de confundirse en un ícono chico sobre una miniatura; 🔥 es la opción más segura visualmente). Permite, dentro de la sección "Siguiendo" del perfil, distinguir de un vistazo el subconjunto de series que el usuario está viendo activamente en este momento. Sin actividad reciente, el título sigue en "Siguiendo" normalmente, solo sin el ícono del badge.

Término **"Watchlist"** en inglés a propósito (exceptuar de la traducción del selector de idioma de contenido — punto 11); si no es técnicamente posible, "Lista de visionado" en español.

**Reglas de transición (series):**
- Tocar el bookmark quita directamente de **Watchlist**, volviendo a "sin estado" — la acción más simple, sin pasar por ningún episodio ni por Abandonar.
- Tocar el ojo marca/desmarca **la serie entera** (todos los episodios de todas las temporadas) de una — funciona desde cualquier estado previo (Watchlist, Siguiendo, o sin ninguno de los tres activos). Marcar como vista **excluye** de Watchlist automáticamente.
- Marcar un episodio individual (no toda la serie) desde el detalle: pasa de Watchlist (si estaba) o de "sin estado" a **Siguiendo** automáticamente — sin que el usuario haya tocado ningún botón de "Siguiendo". Al completar todos los episodios disponibles, pasa a **Vista**.
- Desmarcar un episodio ya visto en una serie "Vista" la devuelve a **Siguiendo** — comportamiento no esperado en el uso normal, pero debe soportarse para permitir deshacer un error del usuario.
- **Caso borde:** si una serie está en "Siguiendo" con un solo episodio visto, y el usuario desmarca justo ese episodio (quedando en cero), el estado cae automáticamente a **sin estado activo** — es una consecuencia directa de que "Siguiendo" se deriva de tener al menos un episodio visto, no una acción manual como Abandonar.
- **Abandonar Serie (❌):** quita únicamente el estado activo "Siguiendo" — **no borra ningún episodio marcado como visto**, solo deja de contarla como "en seguimiento". Deja de notificarse sobre nuevas temporadas para ese título hasta que el usuario vuelva a marcar un episodio como visto o la ponga en Watchlist.
- Volver a poner en **Watchlist**, o marcar un episodio nuevo directamente, una serie sin estado activo — en cualquiera de los dos caminos, **el progreso de episodios vistos se conserva** si lo había. El progreso solo cambia si el usuario desmarca episodios puntuales por su cuenta, nunca automáticamente por un cambio de estado.
- **La única forma real de "empezar de cero" es desmarcar la serie entera con el ojo** (👁 tachado) — eso sí borra el progreso de todos los episodios de una — pensado para quien quiere volver a ver una serie desde el principio, no como efecto secundario de otra acción.

**Regla de series según su estado de renovación en TMDB (`status`):**

- **`Ended` / `Canceled` (confirmada como finalizada):** al marcarla como vista, se queda así de forma permanente, igual que una película.
- **`Returning Series` / `In Production` (confirmada su continuidad):** al marcarla como vista, es *temporal* — apenas se confirme fecha de estreno de la próxima temporada (`next_episode_to_air` con fecha), **vuelve automáticamente a Siguiendo, sin excepción**. Este cambio de estado ocurre igual en la versión mínima — lo que se difiere a la versión superior es únicamente la notificación al usuario avisándole (ver punto 5), no el cambio de estado en sí.
- **Sin confirmación de renovación:** tratarla como vista hasta nuevo aviso, con la misma lógica de arriba.

> **Nota técnica — recálculo automático:** el estado de una serie puede cambiar sin que el usuario haga nada (por sincronización con TMDB, no solo por acción del usuario). El diseño de datos debe contemplar esto, no asumir que el estado es puramente manual.

> **Nota técnica:** el sistema necesita conservar el detalle de episodios vistos de una serie sin estado activo (por si el usuario la retoma), y la acción del ojo (marcar/desmarcar la serie entera) requiere escribir el estado de cada episodio individual por dentro, no es un solo campo a nivel serie.

### 4.1. Sincronización con TMDB

- **Carga inicial:** poblar la base con los archivos de exportación diaria de TMDB (ver punto 9).
- **Sincronización periódica (ej. una vez por día):** agregar títulos nuevos, actualizar el `status`/`next_episode_to_air` de las series ya existentes, y **agregar las temporadas/episodios nuevos que correspondan** a series ya cargadas en la base. **Además, refrescar `popularity`/`vote_average`/`vote_count` de todo el catálogo existente, no solo de los títulos nuevos** — reutiliza el mismo llamado al detalle del título que ya se hace para lo anterior, sin costo adicional real. Es necesario porque un título viejo puede volverse tendencia sin que haya nada "nuevo" que sincronizar en él (un relanzamiento, una noticia, etc.) — sin este refresco, la sección "Trending" (punto 2) mostraría datos de popularidad desactualizados. **También, para títulos cuya cantidad de reseñas guardadas todavía no llegó al tope configurable (punto 9), intentar importar más** — evita que un estreno recién cargado quede con reseñas vacías para siempre.
- **Sincronización por usuario, al loguearse:** comparar el estado guardado de cada título en seguimiento del usuario contra el estado actualizado de la base, y aplicar las transiciones automáticas que correspondan (ej. Vista → Siguiendo si se confirmó nueva temporada) en ese momento, no en tiempo real permanente.

### 5. Notificaciones
Avisar al usuario cuando una serie tenga una fecha de estreno confirmada para su próxima temporada/episodio (`next_episode_to_air` de TMDB), si el usuario tiene **alguna relación activa con ese título** — favorito, Watchlist, Siguiendo, o Vista (simplificación deliberada: incluir Watchlist también, no solo a quien ya la empezó). Esto es más amplio que la regla de **cambio de estado automático** (punto 4), que sigue aplicando solo a títulos en Vista — la notificación es un aviso informativo, no implica que el título cambie de estado para todos los que la reciben.

### 6. Detalle de película — Soporte de puntuaciones y reseñas externas y de usuarios
Información técnica (elenco principal, director, guionista, duración, **géneros**, país), **sinopsis**, **popularidad** (campo `popularity` de TMDB), promedio de puntajes, listado de reseñas. El usuario puede:
- Marcar como favorita (♥, independiente del resto)
- Mover entre **Watchlist** (🔖) y **Vista** (👁)
- Escribir su propia reseña y/o puntaje — **solo permitido si está marcada como Vista** (en películas no hay estado intermedio, ver excepción en detalle de serie). **Puede editarla después** (texto y/o puntaje) — no es de una sola vez, se guarda sobre la misma reseña existente, no crea una nueva.

**Nota técnica — géneros múltiples:** TMDB devuelve varios géneros por título (campo `genres`, una lista, no un valor único) — un título con Drama y Thriller a la vez es el caso normal, no la excepción. El modelo de datos debe reflejar esto como relación muchos a muchos entre Título y Género, no como un campo de texto único.

**Cómo se compone el "promedio de puntaje":** se muestra un **único número combinado**, no dos por separado. Se calcula con una fórmula ponderada: `(vote_average × vote_count + Σ puntajes de reseñas propias de usuarios de la app) ÷ (vote_count + cantidad de reseñas propias)` — sumando únicamente reseñas con usuario real de la app, ya que las importadas de TMDB ya están contempladas dentro de `vote_average`/`vote_count`. Junto al promedio, mostrar también la **cantidad total de votos** que lo componen (`vote_count` de TMDB + cantidad de reseñas propias de usuarios). Por defecto se calcula al vuelo; si el rendimiento lo justifica, se puede cachear (con el cuidado de recalcular en cada alta/baja/edición de reseña, para no repetir el patrón de "valor guardado que se desincroniza").

**Aclaración importante — `vote_average`/`vote_count` están desacoplados de qué reseñas de texto se importen:** estos dos campos vienen del **detalle general del título** en TMDB (el mismo llamado que ya trae `status`, `next_episode_to_air`, etc.), **no** del endpoint de reseñas. Siempre están disponibles completos, sin importar el tope que se defina para cuántas reseñas de texto importar (punto 9) — nunca hubo una relación de dependencia entre ambas cosas, aunque la redacción anterior de este documento podía sugerirlo.

### 7. Detalle de serie — Soporte de puntuaciones y reseñas externas y de usuarios
Mismo contenido que película (incluye **popularidad**), **excepto duración** — una serie no tiene una duración propia, cada episodio tiene la suya (se muestra en el detalle de cada temporada, no a nivel serie). Además, el detalle temporada por temporada con sus episodios — incluyendo **sinopsis de cada temporada** y su **fecha de estreno completa (mes y año, no solo año)**. El usuario puede:
- Marcar como favorita (♥, independiente del resto), agregar/quitar de **Watchlist** (🔖), marcar/desmarcar toda la serie como **Vista** (👁) — ver reglas de transición en el punto 4
- Entrar a "Siguiendo" es automático al marcar un episodio individual como visto, sin ningún botón dedicado — y desde acá se puede tocar ❌ para **abandonar** la serie si está en ese estado
- Marcar episodios de forma granular (un episodio individual, una temporada completa, o la serie entera)
- **Excepción a la regla de reseñas:** a diferencia de película (donde reseñar exige estar en Vista), en series el criterio es **haber visto al menos un episodio** — no importa el estado actual (Siguiendo, Vista, o sin ningún estado activo tras dejar de seguir con progreso previo), mientras haya algún episodio marcado como visto. Watchlist queda excluido porque ahí, por definición, no vio nada todavía; y un título sin estado activo que tampoco tenga ningún episodio visto (nunca se tocó) tampoco debería permitir reseña, aunque técnicamente no esté en Watchlist. Igual que en película, **la reseña se puede editar después** de escrita.

**Fecha de estreno por episodio (solo si es futura):** en temporadas donde los episodios se estrenan uno por semana en vez de todos juntos, mostrar la `fechaEstreno` de cada episodio individual **únicamente cuando todavía no se estrenó** — un episodio ya emitido no necesita mostrar su fecha, ya está disponible. De paso, un episodio con fecha futura no debería poder marcarse como visto todavía (no existe la posibilidad real de haberlo visto).

**Mensaje de estado de la serie (para cualquier usuario, no depende de su estado con el título):** mostrar en el detalle según el campo `status` de TMDB (el mismo que ya usa la máquina de estados del punto 4 — no es un dato nuevo a sincronizar):

| `status` de TMDB | Mensaje en el detalle |
|---|---|
| `Canceled` | "Cancelada" |
| `Ended` | "Finalizada" |
| `Returning Series` / `In Production`, con `next_episode_to_air` con fecha | "Renovada — nueva temporada el DD/MM" |
| `Returning Series` / `In Production`, sin fecha confirmada todavía | "Renovada — fecha de estreno por confirmar" |
| Cualquier otro caso / sin información clara | No mostrar ningún mensaje (mejor nada que un mensaje engañoso) |

Es pasivo y de bajo costo (reutiliza datos que ya se sincronizan para el punto 4) — no depende de la versión superior, a diferencia de la notificación activa del punto 5.

### 8. Recomendador inteligente por IA
El usuario escribe un prompt libre y el sistema devuelve una recomendación basada en:
- El prompt del usuario
- Sus preferencias de perfil (favoritos, vistos, mejor puntuados/reseñados por él)
- Los puntajes generales de la comunidad

Ejemplos de prompts, con distinto nivel de especificidad:
- *"Recomendame algo triste"* / *"Quiero una serie para reírme"* — el prompt define un tono/emoción, hay que cruzarlo con el perfil para elegir algo que además le guste al usuario en particular.
- *"Una película romántica"* / *"Dame una película de Sylvester Stallone"* — el prompt define género/actor, pero la elección final dentro de esa categoría debe seguir considerando el gusto personal del usuario, no ser solo un filtro.
- *"Recomendame la mejor película estrenada en el último mes"* — el prompt especifica poco (solo recencia), y aunque suene a "traeme la de mejor puntaje de la comunidad sin más", **igual debe ponderarse el perfil del usuario** — no recomendar ciegamente lo más aclamado si no coincide con sus gustos históricos.

En ningún caso el prompt debe hacer que se ignore por completo el perfil del usuario, aunque el peso relativo entre los tres factores pueda variar según qué tan específico sea el pedido.

Es deseable (no obligatorio en esta fase) que el peso relativo de estos tres factores sea configurable por el usuario.

**Política de incertidumbre:** el recomendador debe poder responder *"no encontré información suficiente para recomendar algo con confianza"* en vez de forzar siempre una recomendación — específicamente cuando el prompt es poco interpretable (demasiado vago o ambiguo) **y/o** el perfil del usuario está vacío (sin favoritos, sin reseñas, sin puntajes propios), ya sea uno de los dos casos o ambos juntos. **Esto no aplica a pedidos objetivos y ordenables directamente del catálogo** (ej. "la más popular", "la mejor puntuada") — ahí no hace falta juicio de IA para responder, es una consulta directa que el usuario podría resolver mirando el catálogo/rankings él mismo; negarse a responder ahí no tendría sentido.

**Pregunta abierta para la Fase 1, con sugerencia fuerte:** se recomienda resolver esto con **function calling** en un solo llamado (no dos etapas desconectadas) — el modelo de chat principal recibe herramientas disponibles (ej. `buscar_por_filtros_exactos(actor, género, año...)` para hechos concretos, y `buscar_por_similitud_semantica(texto)` para prompts vagos/emocionales que no mapean a ninguna columna), y decide él mismo cuál invocar según el prompt del usuario — incluso puede combinar ambas si el pedido mezcla lo exacto con lo vago (ej. "una película triste de los 90"). Esto evita separar "entender el prompt" de "elegir la recomendación" en dos pasos de IA desconectados.

**Nota sobre género en el recomendador (aplica a la versión superior):** dado que los géneros están guardados en la base en el idioma original de TMDB (ver punto 2), si el usuario le pide al recomendador algo por género en español (ej. "una comedia"), el modelo debe traducir ese término al idioma en que está guardado en la base **antes** de armar el filtro SQL — es parte de lo que resuelve el function calling, no un paso aparte. **En la versión mínima este problema no existe** — al operar directamente en inglés (punto 11), el usuario ya escribe "comedy" y coincide de forma literal con el catálogo, sin necesitar ninguna traducción.

El modelo de embeddings solo entra en juego **dentro** de la herramienta de similitud semántica (calcula el vector del prompt y compara contra los vectores precalculados de cada título) — nunca decide nada por sí mismo, es una utilidad que la IA principal invoca cuando lo necesita.

Nota importante: la IA de este recomendador (embebida en el producto final, corriendo en el backend desplegado) **no tiene ninguna relación con los hubs configurados en `AGENTS.md`** — esos son para el desarrollo asistido por agente, un contexto de uso completamente distinto. Para el recomendador, proponé en la Fase 1 un proveedor de IA gratuito y competente para la tarea (idealmente con soporte de function calling), evaluado de forma independiente.

### 9. Carga de datos
Base de datos de películas/series poblada desde TMDB (usar los archivos de exportación diaria para la carga masiva inicial, no recorrer `/search` título por título), filtrando por un criterio de calidad/popularidad razonable (campos `vote_average` y `popularity` de TMDB) para priorizar contenido relevante por sobre cobertura total. Como respaldo, soportar carga manual vía archivo JSON para títulos puntuales que TMDB no tenga.

**Nota técnica:** los archivos de exportación son livianos (solo ID y datos básicos) — elenco, traducciones y otros datos ricos requieren un llamado adicional por título (se pueden combinar varios en una sola llamada con `append_to_response`). La carga inicial implica ese paso extra, no es un solo archivo que trae todo de una vez.

**Nota técnica — tope de reseñas de TMDB importadas por título (parámetro configurable, no un número fijo):** el endpoint de reseñas de TMDB viene paginado — no hay forma de traer todas en una sola llamada. El costo real de importar más páginas no es de almacenamiento (unas filas de texto de más no pesan nada en la base) sino de **tiempo de sincronización**: cada página extra es un llamado más por título, multiplicado por todo el catálogo en el job diario. TMDB no expone ningún campo de "utilidad" o votos por reseña — no hay forma de traer "las más útiles", solo las que devuelva la API. Definir el tope como parámetro ajustable (arrancar conservador, ej. 1-2 páginas) y afinarlo con datos reales de volumen típico una vez en desarrollo, no de antemano sin esa información.

**Sobre la actualización de reseñas — importación progresiva hasta el tope, no estrictamente única:** se importan al cargar el título por primera vez, y **se sigue intentando traer más en cada sincronización diaria (punto 4.1) mientras la cantidad guardada para ese título no haya llegado al tope configurable** — esto evita que un estreno recién cargado quede con reseñas vacías para siempre, ya que TMDB recién acumula reseñas después del estreno. La condición para reintentar es local (comparar cantidad guardada vs. tope, sin necesidad de llamar a TMDB primero) — los títulos que ya alcanzaron el tope se autolimitan solos, sin generar ningún llamado de más. Deduplicar por el ID propio de cada reseña al reintentar.

**Nota técnica — popularidad como percentil, no número crudo:** el campo `popularity` de TMDB es un valor abierto y sin techo fijo (no una escala 1-100), poco presentable tal cual en pantalla. Conviene calcular un **percentil** (posición relativa de 1 a 100 dentro del propio catálogo de la app, no el de TMDB completo) — es una operación estándar de SQL con funciones de ventana (`PERCENT_RANK()` o similar), no algo exótico. No hace falta calcularlo en cada request: se recalcula como parte del mismo job de sincronización diaria (punto 4.1), guardando el percentil ya calculado junto al resto de los datos del título.

**Sobre las portadas:** TMDB no entrega el archivo de imagen — entrega un campo de texto corto (`poster_path`) que combinado con la URL base de su CDN arma la dirección completa de la imagen. Alcanza con guardar ese texto/URL como un campo más de `Título`, sin manejar binarios ni almacenamiento de imágenes propio — el navegador del usuario carga la imagen directo desde TMDB. Para los títulos cargados manualmente vía JSON (que no tienen esta fuente), hay dos caminos simples dado el volumen bajo esperado: que el JSON provea directamente una URL de una imagen ya alojada en otro lado, o guardar esas pocas imágenes como archivos estáticos dentro del propio proyecto.

**Atribución obligatoria a TMDB:** es una condición real de uso de su API gratuita, no una decisión estética — la documentación oficial de TMDB pide explícitamente atribuir la fuente de cualquier imagen o dato usado. Incluir el logo/texto oficial de atribución de forma visible en la interfaz (ej. junto al nombre de la app en el header). TMDB provee los logos oficiales para este uso en su documentación.

### 10. Plataformas de streaming
Incluir en el detalle de película y serie (secciones 5 y 6) dónde se puede ver cada título — TMDB tiene un endpoint de Watch Providers, alimentado por JustWatch, **con datos genuinamente separados por país** (no un catálogo único global). La propuesta de arquitectura debe contemplar cómo se determina la región del usuario (selección manual, o algún default razonable) para filtrar la respuesta correctamente.

### 11. Idioma — dos selectores independientes (deseable, no esencial)

**En la versión mínima, sin selector de idioma, la app opera directamente en inglés** (interfaz y contenido) — coincide con el idioma en que TMDB guarda los géneros y la mayoría de sus datos, evitando de entrada el problema de tener que traducir términos del usuario antes de buscar (ver nota en el punto 8). No hace falta ningún mecanismo de traducción mientras no exista el selector — se resuelve por alcance, no por código adicional.

**Selector de idioma del sitio:** traduce menús, labels, botones y todo texto propio de la interfaz (inglés, español España/Latam, italiano, francés, portugués). Esto es un problema de internacionalización de software estándar — completamente independiente de TMDB, se resuelve con archivos de traducción por idioma para cada string de la interfaz. Técnicamente viable sin riesgo, es trabajo de desarrollo, no una limitación de datos.

**Selector de idioma del contenido:** independiente del anterior, define en qué idioma se muestran los datos de películas/series (título, sinopsis). Dos opciones:
- **Original:** cada título se muestra en su idioma original (`original_language` de TMDB) — **excepto** si ese idioma usa un alfabeto no latino (ej. japonés, coreano, chino, ruso, árabe), en cuyo caso se considera "original" al inglés, no al alfabeto no latino.
- **Un idioma elegido** (de los mismos 5 mencionados arriba): todos los títulos se traducen a ese idioma, con **fallback por título individual** al original (según la regla de arriba) si a ese título puntual le falta la traducción — nunca un fallback de todo el sitio.

**Nota:** el idioma original de cada título debe quedar guardado como dato propio (no algo a recalcular después), porque hace falta para decidir si ese título necesita traducción o no, según el idioma que el usuario eligió — aplicando siempre la regla del alfabeto no latino de arriba antes de comparar.

**El buscador (punto 2) debe funcionar en cualquier idioma disponible para cada título** (solo por nombre — género no se busca directo, ver justificación en el punto 2), sin importar el idioma de contenido seleccionado — un usuario con el sitio en español debe poder encontrar un título por su nombre en inglés igual, si lo conoce así.

## Objetivos: Versión Mínima vs. Versión Superior

Dado el plazo del curso (~1 mes y medio), las funcionalidades de arriba se dividen en dos niveles. La arquitectura base (3 capas, el favorito + 3 estados de título con recálculo automático por sincronización, y el uso de IA embebida) se mantiene en ambos niveles — lo que cambia es la sofisticación y la cantidad de funcionalidades secundarias.

### Flujo núcleo (lo que hace que valga la pena construir esto)

Usuario se registra → explora el catálogo → marca Favorito/Watchlist/Vista → sigue una serie marcando episodios → escribe (y puede editar) sus reseñas → recibe una recomendación. Cada pieza de la versión mínima existe para sostener este flujo — nada más, nada menos.

**Orden de implementación sugerido — el recomendador va al final, no al principio:** aunque sea la funcionalidad más "vistosa" de IA, depende de tener datos reales de reseñas y estados para recomendar con criterio real, no solo con datos de ejemplo. Conviene que el resto del sistema (catálogo, estados, reseñas) esté funcionando primero.

### Versión Mínima (objetivo: aprobar el curso en el plazo)

- Login mínimo (punto 1)
- **Catálogo acotado pero variado** — orientativamente unos 200 títulos entre películas y series, priorizando variedad de género por sobre cantidad (mismo criterio de popularidad/puntaje del punto 9)
- Página principal con favorito + 3 estados, regla de exclusión, e íconos de acción rápida (punto 2) — **buscador solo por título**, sin filtro por director/guionista/actor todavía; secciones limitadas a 10 títulos, sin pantallas de "ver más" dedicadas todavía
- Favorito + 3 estados de título (Watchlist/Siguiendo/Vista) con recálculo automático por sincronización con TMDB (puntos 4 y 4.1) — **es el corazón de la arquitectura, no se recorta**
- **Reseñas y puntuaciones** (propias, editables después de escritas, y de TMDB), en el detalle de película y serie (puntos 6 y 7) — **prioritario, no un feature menor**, en parte porque el recomendador se apoya en esta información
- Detalle de película y serie con datos técnicos, sinopsis, popularidad, promedio de puntaje (puntos 6 y 7)
- **Recomendador con IA embebida, versión simple — última pieza a implementar, no la primera** (ver "orden de implementación" arriba): sin function calling ni búsqueda semántica por embeddings — extracción básica de palabras clave conocidas (género, actor si aparece literal en el catálogo) + prompt directo a un modelo de chat con perfil del usuario, sus reseñas/puntajes propios, y puntajes de comunidad. Menos preciso que la versión completa, pero cumple con tener IA embebida real, no simulada.
- Carga de datos desde TMDB con filtro de popularidad/puntaje (punto 9), incluyendo el refresco diario de popularidad/puntaje para todo el catálogo (punto 4.1) — no solo lo nuevo. Respaldo JSON manual incluido.

### Versión Superior (objetivo: después de terminar el curso, si no se llega antes)

- Notificaciones de estreno (punto 5)
- Badge "Viendo Actualmente" (🔥) sobre Siguiendo, con ventana de tiempo configurable (punto 4)
- Sección de Estadísticas en el perfil (punto 3)
- Recomendador con function calling + búsqueda semántica por embeddings (punto 8, versión completa)
- Buscador extendido por director, guionista y actor (punto 2), y pantallas dedicadas de "ver más" para cada sección
- Plataformas de streaming por región (punto 10)
- Selector de idioma — sitio y contenido (punto 11)
- Ampliar el catálogo inicial de TMDB más allá del recorte por popularidad

## Sugerencias de Arquitectura y Despliegue (no vinculantes)

Como punto de partida para la discusión, Render (backend) y Vercel (frontend) son una combinación razonable para este tipo de proyecto — pero no es una decisión cerrada, la propuesta de Fase 1 puede proponer algo distinto si tiene mejor fundamento. Lo que sí es innegociable, independientemente de la plataforma elegida: usar variables de entorno (`.env`) para las credenciales de la base de datos y las API keys de TMDB y de los hubs IA, garantizando que no se suban datos sensibles a GitHub, con el `.gitignore` correctamente configurado desde el inicio.

## Fase 1: Propuesta Arquitectónica (No programar aún)

Todo lo anterior son los requerimientos funcionales, no una arquitectura ya decidida. Actuá como el Arquitecto de Software Principal: analizá los requerimientos y generá **tu propia propuesta**, que después vamos a discutir y ajustar juntos antes de aprobar nada — no es un molde a completar, es tu mejor recomendación fundamentada:

1. **Selección de Tecnologías:** proponé un stack (backend, frontend, persistencia) ideal para las plataformas de despliegue seleccionadas, explicado en lenguaje coloquial. El lenguaje/framework de cada capa no está impuesto de antemano — elegí el más adecuado por capa (ver criterio de lenguajes en `AGENTS.md`).
2. **Diseño de Base de Datos:** el modelo de datos debe soportar los siguientes requisitos — la cantidad de tablas, sus nombres y su estructura exacta **no están decididos de antemano**, son una propuesta tuya a hacer, no una lista a completar tal cual:
   - Usuarios, con contraseñas almacenadas con hash.
   - Títulos (películas y series), con sus datos técnicos (ver Fase 1, sección de Carga de Datos).
   - Estructura de temporadas/episodios para series.
   - El favorito y los 3 estados de título por usuario (punto 4) y su historial de episodios vistos.
   - Reseñas propias de la app y de la comunidad de TMDB, distinguibles entre sí, idealmente sin duplicar la lógica de consulta entre ambos orígenes. **Confirmado: TMDB sí devuelve el nombre de quien escribió cada reseña** (campo `author`) — no hace falta inventar nombres genéricos ni dejarlo vacío para las importadas. Se guarda en un campo propio (`autorTMDB`, texto), separado de la FK hacia `Usuario` — **son mutuamente excluyentes**: si la reseña es de un usuario de la app, la FK está poblada y `autorTMDB` queda nulo; si es importada de TMDB, es al revés. Al mostrar una reseña, se lee el que no esté nulo, aclarando el origen TMDB cuando corresponda. El puntaje de una reseña **es opcional en ambos orígenes** — un usuario de la app puede reseñar sin puntuar, y una reseña de TMDB puede no traerlo; en ambos casos, simplemente no se muestra ningún puntaje para esa reseña puntual.
   - Resolvé explícitamente el mecanismo de recálculo automático por sincronización con TMDB (punto 4.1).
3. **Hoja de ruta (Artifact):** pasos lógicos para la construcción del software, y criterios de éxito/pruebas automáticas para asegurar que funcione sin errores.

## Instrucción de Control (Human-in-the-Loop)

DETENTE por completo al finalizar esta Fase 1. Presentá la propuesta de arquitectura, el diseño de la base de datos y la hoja de ruta (Artifact) en el chat. Esperá mi revisión y aprobación explícita antes de abrir la terminal o crear carpetas en el repositorio local.
