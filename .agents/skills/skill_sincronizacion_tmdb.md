# Skill: Sincronización con TMDB

Consultar este documento antes de escribir o modificar código relacionado a la carga inicial, el job de sincronización diaria, o el manejo de datos provenientes de TMDB.

## Carga inicial

Poblar la base con los archivos de exportación diaria de TMDB (no recorrer `/search` título por título). Estos archivos son livianos (solo ID y datos básicos) — elenco, traducciones y otros datos ricos requieren un llamado adicional por título (combinable con `append_to_response`). Filtrar por popularidad/puntaje razonable, priorizando variedad de género por sobre cantidad total.

## Job de sincronización periódica (diario)

En una sola pasada, para el catálogo completo (no solo lo nuevo):
1. Agregar títulos nuevos.
2. Actualizar `status` y `next_episode_to_air` de series existentes.
3. Agregar temporadas/episodios nuevos de series ya cargadas.
4. **Refrescar `popularity`, `vote_average`, `vote_count` de TODO el catálogo existente** — no solo de lo nuevo. Reutiliza el mismo llamado al detalle del título que los puntos 2 y 3 ya necesitan, sin costo adicional real. Es necesario porque un título viejo puede volverse tendencia sin tener nada "nuevo" que sincronizar (relanzamiento, noticia, etc.) — sin esto, la sección Trending muestra datos desactualizados.

**Percentil de popularidad:** `popularity` de TMDB es un valor abierto sin escala fija, poco presentable tal cual. Calcular un percentil (1-100, relativo al propio catálogo de la app, no al de TMDB completo) usando una función de ventana SQL (`PERCENT_RANK()` o similar) como parte de este mismo job — no en cada request.

## Sincronización por usuario, al loguearse

Comparar el estado guardado de cada título en seguimiento contra el estado actualizado de la base, aplicando las transiciones automáticas que correspondan (ver skill de Máquina de Estados) en ese momento, no en tiempo real permanente.

## Reseñas de TMDB — importación progresiva hasta el tope, no estrictamente única

Las reseñas se importan al cargar el título por primera vez, **y se sigue intentando traer más en cada sincronización diaria posterior, mientras la cantidad ya guardada para ese título no haya llegado al tope configurable.** Esto resuelve un caso real: un estreno recién cargado tiene pocas o ninguna reseña en TMDB todavía — quedaría vacío para siempre con una importación estrictamente única, ya que las reseñas se acumulan recién después del estreno.

**Por qué esto no reintroduce la complejidad que se descartó antes (chequeo diario de `total_results` para todo el catálogo):** la condición para intentar de nuevo es local, no requiere ningún llamado a TMDB — simplemente comparar cuántas reseñas ya tenemos guardadas para ese título contra el tope. Para la mayoría de los títulos (los que ya alcanzaron el tope), esa comparación ya alcanza para no hacer nada — se autolimitan solos, sin gastar ningún llamado de más. Solo los títulos todavía por debajo del tope (típicamente estrenos recientes) generan un llamado adicional en el job diario.

- **Tope configurable** de reseñas por título (parámetro ajustable, no un número fijo grabado — arrancar conservador y afinar con datos reales de volumen).
- Deduplicar por el ID propio de cada reseña (que TMDB sí provee), para no importar la misma dos veces al reintentar.
- TMDB no expone campo de "utilidad"/votos por reseña — no hay forma de traer "las más útiles", solo lo que la API devuelva.
- Cada reseña trae el nombre real del autor (campo `author`) — guardarlo en un campo propio (`autorTMDB`), separado y mutuamente excluyente de la FK hacia `Usuario` de la app.
- El puntaje de una reseña de TMDB puede venir nulo — no forzar un valor, simplemente no mostrar puntaje en ese caso (aplica también a reseñas propias sin puntaje).

## Géneros

TMDB devuelve varios géneros por título (campo `genres`, lista — no un valor único). Modelar como relación muchos a muchos entre Título y Género, nunca como campo de texto único. Es normal que un título aparezca en más de una sección de género a la vez en la exploración.

**Traducción de género — solo aplica a la versión superior.** La versión mínima opera en inglés (sin selector de idioma), así que el usuario ya escribe el género en el mismo idioma en que se guarda — no hace falta traducir nada ahí. En la versión superior, si el usuario pide algo por género en otro idioma, es el modelo de function calling el que traduce antes de armar el filtro SQL (ver skill de Recomendador).

## Portadas e imágenes

TMDB no entrega el archivo de imagen — entrega `poster_path`, que combinado con la URL base de su CDN arma la dirección completa. Guardar solo ese texto/URL como campo de `Título` — nunca manejar binarios de portadas propios. El navegador del usuario carga la imagen directo desde TMDB.

## Atribución obligatoria

Es condición real de uso de la API gratuita, no una decisión estética — incluir el logo/texto oficial "Powered by TMDB" de forma visible en la interfaz (ej. junto al nombre de la app en el header).
