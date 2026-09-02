# Skill: Máquina de Estados de Título (Favorito / Watchlist / Siguiendo / Vista)

Consultar este documento antes de escribir o modificar código relacionado a estados de título, iconografía de acciones del usuario, o transiciones entre Watchlist/Siguiendo/Vista.

## El modelo

Cada título tiene un **favorito independiente**, y en series, **3 estados mutuamente excluyentes** (Watchlist / Siguiendo / Vista). En películas, al no haber episodios, solo aplican dos de los tres (Watchlist / Vista) — no existe "Siguiendo" para películas.

Los 3 estados son mutuamente excluyentes a propósito — desacoplarlos generaría combinaciones sin significado claro (¿qué implicaría "Vista" + "Siguiendo" a la vez?) sin beneficio real.

## Iconografía — 3 botones interactivos + 1 acción condicional

| Ícono | Acción | Aplica a |
|---|---|---|
| ♥ (lleno/vacío) | Marcar/desmarcar favorita — independiente de todo | Películas y series |
| 👁 / 👁‍🗨 (tachado) | Marcar/desmarcar **toda la serie** como vista de una | Películas y series |
| 🔖 (lleno/vacío) | Agregar/quitar de **Watchlist** | Películas y series |
| ❌ (rojo) | **Abandonar** — solo visible en detalle o en sección Siguiendo del perfil, solo si está en ese estado | Solo series |

**"Siguiendo" no tiene botón propio — es 100% automático.** Se entra al marcar un episodio individual como visto, nunca con un ícono dedicado. Como marcador visual de sección (no interactuable): **▶️**.

**El ícono de bookmark tiene un tercer estado visual bloqueado, en dos casos, en cualquier lugar donde aparezca (tarjetas de exploración incluidas, no solo el detalle):**
- **Serie en Siguiendo:** el espacio muestra ▶️ bloqueado en vez de bookmark — evita confundir al usuario mientras la serie ya se está viendo. **Abandonar (❌) no está disponible desde la tarjeta de exploración** — solo en el detalle de la serie o en la sección Siguiendo del perfil; desde Home, el ▶️ es puramente informativo, sin interacción posible. Para volver a Watchlist, primero hay que entrar al detalle y tocar ❌ (Abandonar).
- **Título en Vista:** no tiene sentido agregar a Watchlist algo ya visto por completo — el ícono queda bloqueado/oculto. La única vía de vuelta a Watchlist es desmarcar primero con el ojo tachado.

**El ícono del ojo tiene comportamiento distinto según el contexto:** en exploración, marcar como Vista excluye el título de esa vista al instante (se reemplaza por otro, ver regla de reemplazo en el documento de inicio). En el buscador (exento de esa exclusión), un título ya visto muestra el ojo tachado (👁‍🗨), permitiendo desmarcarlo directo desde ahí.

## Reglas de transición (series)

- Tocar el bookmark agrega/quita directamente de Watchlist — la acción más simple, sin pasar por ningún episodio.
- Tocar el ojo marca/desmarca **la serie entera** de una, desde cualquier estado previo. Marcar como vista excluye de Watchlist automáticamente.
- Marcar un episodio individual: pasa de Watchlist o de "sin estado" a **Siguiendo** automáticamente. Al completar todos los episodios disponibles, pasa a **Vista**.
- Desmarcar un episodio ya visto en una serie "Vista" la devuelve a **Siguiendo** (deshacer error, no el flujo esperado, pero debe soportarse).
- **Caso borde:** si una serie está en Siguiendo con un solo episodio visto y se desmarca justo ese, el estado cae automáticamente a **sin estado activo** — consecuencia de que Siguiendo se deriva de tener al menos un episodio visto, no una acción manual.
- **Abandonar (❌):** quita únicamente el estado activo "Siguiendo" — **no borra ningún episodio marcado como visto**, solo deja de contarla como en seguimiento.
- El progreso de episodios **se conserva siempre**, sin importar el camino de vuelta (Watchlist o marcar directo). La única forma real de "empezar de cero" es desmarcar la serie entera con el ojo — acción explícita e intencional, no efecto colateral de otra cosa.

## Regla de renovación (según `status` de TMDB)

- `Ended` / `Canceled`: al marcarla vista, se queda así de forma permanente.
- `Returning Series` / `In Production`: al marcarla vista, es *temporal* — apenas se confirme fecha de la próxima temporada (`next_episode_to_air`), **vuelve automáticamente a Siguiendo, sin excepción**.
- Sin confirmación de renovación: tratar como vista hasta nuevo aviso.

**Este cambio de estado por renovación aplica en la versión mínima.** Lo que se difiere a la versión superior es solo la *notificación* al usuario avisándole — el cambio de estado en sí no depende de eso.

## Fechas a trackear (para ordenar listas por más reciente)

- `fechaFavorito` y `fechaEstado` en la relación Usuario-Título — dos fechas independientes.
- **`fechaEstado` NO sirve para ordenar "Siguiendo"** — solo cambia cuando el estado en sí cambia, no en cada episodio nuevo visto dentro del mismo estado, quedaría desactualizado. Para ordenar Siguiendo por más reciente, usar `MAX(fechaVisto)` de `EpisodioVisto` para cada título — mismo valor que ya usa el badge "Viendo Actualmente" (versión superior).
- `fechaEstado` sí sirve tal cual para ordenar Watchlist y Vista, donde no hay sub-actividad continua que lo vuelva obsoleto.

## Elegibilidad de reseña (distinta entre película y serie)

- **Película:** solo si está marcada como Vista.
- **Serie:** haber visto al menos un episodio — no importa el estado actual (Siguiendo, Vista, o sin estado con progreso previo), mientras haya algún episodio marcado como visto.
- En ambos casos, la reseña se puede **editar después** de escrita (texto y/o puntaje) — se actualiza sobre la existente, no crea una nueva.
