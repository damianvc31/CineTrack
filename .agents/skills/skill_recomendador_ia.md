# Skill: Recomendador con IA — Function Calling (Versión Superior)

Consultar este documento antes de implementar la versión superior del recomendador. **Implementar esto al final del proyecto**, después de que el resto del sistema (catálogo, estados, reseñas) esté funcionando con datos reales — el recomendador depende de tener esa información real para recomendar con criterio, no solo con datos de ejemplo.

> Para la versión mínima (keyword matching simple, sin function calling), ver el documento de inicio de proyecto directamente — este skill es específico de la versión superior.

## Las 2 herramientas

```
buscar_por_filtros_exactos(genero?, actor?, anio_desde?, anio_hasta?, orden?)
buscar_por_similitud_semantica(texto, restringir_a_ids?)
```

El modelo de chat principal recibe ambas herramientas y **decide solo** cuál invocar, según entienda el pedido del usuario — no hay un paso separado de "clasificar la intención" antes. Puede invocar una sola, o encadenar las dos (ej. "una película triste de los 90": primero filtro exacto por década, después similitud semántica restringida a esos IDs).

## Traducción de género

Los géneros están guardados en la base en inglés. Si el usuario pide algo por género en otro idioma, el modelo debe traducir el término **antes** de llamar a `buscar_por_filtros_exactos` — es parte de lo que resuelve el function calling, no un paso aparte ni un diccionario fijo.

## Embeddings — cuándo se calculan

El vector de cada título (a partir de sinopsis + género) se calcula **una vez, durante la sincronización** — nunca en cada pedido del usuario. `buscar_por_similitud_semantica` calcula el embedding del *pedido* al vuelo y lo compara contra los vectores ya precalculados.

## Perfil del usuario — nunca se ignora

La recomendación siempre cruza: el prompt del usuario + su perfil (favoritos, reseñas propias, puntajes propios) + puntajes de la comunidad. El peso relativo entre los tres puede variar según qué tan específico sea el pedido, pero el perfil nunca se ignora por completo — ni siquiera cuando el pedido suena objetivo (ej. "la mejor película del último mes" igual se cruza contra el perfil antes de la respuesta final).

## Política de incertidumbre

El recomendador puede responder *"no encontré información suficiente para recomendar con confianza"* en vez de forzar siempre una recomendación — específicamente cuando:
- El prompt es poco interpretable (vago o ambiguo), **y/o**
- El perfil del usuario está vacío (sin favoritos, sin reseñas, sin puntajes propios)

**Esto NO aplica a pedidos objetivos y ordenables directo del catálogo** (ej. "la más popular", "la mejor puntuada") — ahí no hace falta juicio de IA, es una consulta directa que no requiere negarse a responder.
