# Descripción de Wireframes — Estado Final Confirmado

> Describe el resultado **real** de las 3 pantallas generadas en Figma AI, tal como quedaron confirmadas tras revisión (no la intención original de los prompts de generación, que en algunos puntos difiere de lo finalmente obtenido). Las imágenes originales siguen disponibles como referencia visual — este documento es un resumen textual para no depender de procesar las imágenes en cada consulta.

## Pantalla 1 — Home

**Header:** logo "CineTrack" (con ícono tipo claqueta) + "Powered by TMDB" en texto chico. Buscador centrado ("Search movies and series..."). Toggle de 3 opciones (Movies / Series / All). A la derecha: **dos estados confirmados por separado, en imágenes distintas** — `home-not-logged.png` (botones "Log In"/"Sign Up") y `home-logged.png` (panel de usuario, ver abajo) — mutuamente excluyentes, nunca ambos a la vez.

**Panel izquierdo (AI Assistant):** colapsable, con textarea ("Tell us what you feel or what you're looking for...") y botón "Recommend".

**Panel derecho (solo en `home-logged.png`):** avatar + nombre + campanita de notificaciones junto al nombre, y debajo la lista de accesos: Profile, Favorites, Watchlist, Watch History, Following, Reviews, Settings — con íconos: 👤 🤍 🔖 👁 ▶️ 💬 ⚙️.

**Secciones de exploración (tarjetas en fila, scroll horizontal):** Trending, New Releases, Classics, Recommended, y por género (ej. Comedy, Action). Cada tarjeta: póster, indicador de popularidad (🔥 + número), título, puntaje (⭐ + número + cantidad de votos entre paréntesis), y 3 íconos de acción (❤️ favorito / 👁 visto / 🔖 watchlist) — sin ícono de "+" adicional. **Para el dato de año — confirmado en `home-logged.png`:** en películas, el año simple de estreno (ej. "2024"); en series, el mismo formato "N seasons | AAAA-AAAA" que se usa en los rankings de Perfil (ej. "Dark Signal · 4 seasons | 2020-2024") — se verificó que el formato se aplica correctamente en varias tarjetas de series a lo largo de distintas secciones, no solo en un caso aislado.

## Pantalla 2 — TV Series Detail

**Header:** mismo logo unificado que Home. Buscador centrado. Campanita de notificaciones. Avatar de usuario cerrado (su despliegue se documenta aparte, ver sección de interacción más abajo) con nombre al lado.

**Contenido principal:** póster grande a la izquierda. A la derecha: puntaje combinado (⭐ X.X /10, cantidad de votos), título, badge/mensaje de estado de emisión (verde: "Renovada — nueva temporada el DD/MM" o "por confirmar"; neutro/gris: "Finalizada"; rojo: "Cancelada"), tags de género, año y país, sinopsis, director, guionista, elenco principal.

**4 íconos de acción** debajo de los datos: ❤️ Favorite, 👁 Watched, ▶️ Following (bloqueado/no interactuable — reemplaza al bookmark cuando la serie está en seguimiento activo), ❌ Unfollow (solo visible si está siguiendo).

**Selector de temporadas:** tabs horizontales (Season 1, Season 2, Season 3...) — la temporada completamente vista muestra un badge "WATCHED" en su propio tab.

**Lista de episodios** de la temporada seleccionada: número, nombre, duración, y checkbox de visto/no visto. Los episodios vistos tienen el fondo de su fila sombreado en tono cálido, distinguible de los no vistos.

**Sección de reseñas ("User Reviews"):** contador ("Showing X of Y reviews"), tarjetas con avatar circular, nombre de usuario, fecha, texto, y puntaje en estrellas. Botón "Write a Review" al final.

## Pantalla 3 — User Profile

**Header:** mismo patrón que Detail (logo unificado, buscador, campanita, avatar+nombre).

**Columna izquierda (tarjeta de identidad):** avatar grande, nombre, "Member since [fecha]", bio de texto libre, ubicación (ícono de pin + ciudad, país).

**Panel de Statistics (columna derecha, ancho completo):**
- Fila superior: 3 tarjetas — Total Hours (con desglose películas/series), Movies Watched (con promedio semanal), Series Watched (con temporadas completadas).
- Debajo, dos columnas:
  - Izquierda: "Top 5 Watched by Popularity" (5 ítems, con % de popularidad), y debajo el gráfico de torta "Genres Watched" (con cantidad total de títulos en el centro y leyenda de porcentajes por género). Divisor horizontal entre ambos.
  - Derecha: "Top 5 Watched by Rating" (promedio de comunidad) arriba, y "Top 5 Watched by My Rating" (puntaje propio del usuario) abajo — sin divisor entre ambos, ya que son del mismo tipo de contenido.
  - Para series en cualquiera de los 3 rankings: formato "Nombre · N seasons | AAAA-AAAA" (cantidad de temporadas + rango de años).

**Sección "Following" (fila completa, ancho total):** tarjetas grandes con imagen, nombre de la serie, y una barra de progreso por temporada (coloreada: vista / en progreso resaltada distinto / no vista), con leyenda de estado (ej. "S2 in progress", "S3 watchlist").

**Trío de secciones (Favorites | Watchlist | Recently Watched):** cada una con contador entre paréntesis, link "View All", y 3 tarjetas chicas (póster, título, año, puntaje). En las tarjetas de series completadas de la sección "Recently Watched" / "Vista", se incluye el badge visual de estado (🟢 Renovada, ⬛ Finalizada, 🔴 Cancelada) para distinguir rápidamente su continuidad sin alterar el estado de la serie.

## Comportamiento no visible en las imágenes estáticas (Detail y Perfil)

- El avatar, al tocarlo, despliega un menú con los mismos 7 accesos que el panel fijo de Home: Profile (resaltado si es la pantalla actual), Favorites, Watchlist, Watch History, Following, Reviews, Settings. Se guardó como imagen aparte, no superpuesta sobre las pantallas, para no tapar contenido.
- El logo "CineTrack" del header funciona como link de regreso a Home.
