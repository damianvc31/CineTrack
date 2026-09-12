# AGENTS.md — Directivas del Orquestador

Este archivo define cómo debe comportarse el agente en **cualquier proyecto** dentro de este entorno. No es específico de un proyecto puntual — esas instrucciones van en el mensaje de inicio de cada proyecto, no acá.

**Antes de empezar cualquier tarea, leé también `soul.md` (quién sos, tu personalidad y valores) y `user.md` (quién es el usuario y cómo tratarlo) en la raíz del repo** — no asumas que se cargan solos, confirmá haberlos leído si no estás seguro.

---

## 1. Hubs y Modelos Disponibles

**Hubs activos — permitidos, con su modelo configurado:**

**Nota — solo aplica a Hugging Face y NVIDIA:** son catálogos grandes con muchos modelos disponibles — el que figura en la tabla es el que ya se probó y se sabe que funciona por defecto, no el único que existe en ese hub. Otros modelos del mismo catálogo podrían funcionar, pero no están comprobados todavía. **El resto de los hubs de esta tabla tienen un solo modelo disponible, fijo en el código** — no hay otra opción para probar ahí.

| Hub | Modelo | Nota |
|---|---|---|
| Groq | `openai/gpt-oss-120b` | Rápido, buena calidad general |
| Google Gemini (vía hub) | `gemini-3.6-flash` | Distinto del Gemini nativo de Antigravity — este es una llamada de herramienta, no el motor del agente |
| Hugging Face | `meta-llama/Llama-3.3-70B-Instruct` (default, se puede pedir otro modelo puntual del catálogo) | Bueno para instrucciones estructuradas |
| NVIDIA | `mistralai/mistral-nemotron` (default, se puede pedir otro modelo puntual del catálogo) | Optimizado para instruction-following, workflows agénticos y function calling — reemplazó a `meta/llama-3.1-70b-instruct`, que dejó de estar disponible en el catálogo |
| OpenRouter — Slot 1 | `nex-agi/nex-n2.5-pro:free` | Modelo agéntico de Nex AGI, orientado específicamente a coding agéntico, uso de herramientas y bucles de auto-corrección (explora código, ejecuta comandos, prueba resultados, corrige si falla) — buen fit para tareas de desarrollo vía hub. Publicado muy recientemente, por debajo de los modelos top de pago en benchmarks de código, pero competente para un modelo gratuito. Ya no es el router variable de antes — modelo fijo, mismo nivel de consistencia que los otros slots. |
| OpenRouter — Slot 2 | `google/gemma-4-31b-it:free` | Modelo fijo |
| OpenRouter — Slot 3 | `cohere/north-mini-code:free` | Modelo fijo, orientado a código |

**Hubs inactivos — PROHIBIDO llamar (sin saldo, no reintentar):**
Cerebras, SambaNova, Kimi. Si en algún momento el usuario confirma que cargó saldo en alguno de estos, se levanta la restricción para ese proveedor puntual — hasta entonces, ignorar cualquier intento de enrutamiento hacia ellos.

**Modelos locales (Ollama) disponibles:**

| Modelo | Rol sugerido |
|---|---|
| `qwen2.5-coder:7b` | Escritura y edición de código |
| `deepseek-r1:14b` | Depuración / razonamiento paso a paso |
| `gemma4:12b` | Auditoría, lectura de documentación extensa |
| `llama3:8b` | Consultas generales |
| `gemma12b-24k:latest` | Variante de `gemma4:12b` con ventana de contexto ampliada — usar solo si un texto/documento es demasiado largo para el default |
| `qwen7b-32k:latest` | Variante de contexto muy ampliado. No sirvió como reemplazo del orquestador (probado y descartado) — dejarlo solo para texto muy largo, como alternativa a `gemma12b-24k` |
| `phi4-mini:latest` | Modelo chico y liviano. Útil para consultas triviales donde la velocidad importa más que la profundidad |
| `nomic-embed-text` | **No es un modelo de chat** — genera embeddings (vectores numéricos de texto), no respuestas. No usar con `ask_ollama`. Reservarlo solo si el proyecto necesita búsqueda semántica/por similitud |

Gemini Flash nativo (motor del agente en Antigravity) se usa solo para coordinar el flujo visual y mapear herramientas MCP — nunca para procesar texto extenso ni escribir código, eso se delega según la tabla de arriba.

---

## 2. Enrutamiento: Criterio de Elección

- **Preferí lo local para tareas repetitivas o de bajo riesgo** (ediciones chicas, consultas rápidas, cosas que no dependen de razonamiento profundo) — cuida cuota de hubs sin sacrificar calidad real.
- **Usá un hub cuando la tarea se beneficie claramente de más capacidad**: refactors grandes, razonamiento complejo de varios pasos, mucho contexto simultáneo, o cuando el modelo local ya mostró señales de fallar o dar resultados de baja calidad en el intento anterior.
- **Nunca upgrades "por las dudas"** — si lo local resuelve bien, no hay razón para gastar cuota de hub.
- Groq/HF/NVIDIA/Gemini(hub)/OpenRouter (los 3 slots) son opciones igual de válidas entre sí para tareas que requieran nube — elegí según disponibilidad y el tipo de tarea, no hay un orden fijo de preferencia entre ellos.
- **Si un hub falla (error 500/503, timeout, o cualquier otro), no reintentes infinitamente** — máximo 1 reintento con una breve espera, y si vuelve a fallar, tratalo como no disponible por ahora. Antes de caer a local, probá con **otro hub de la lista** (son interconectables entre sí, ver punto anterior) — recién si varios hubs fallan seguido, o ninguno es apropiado, seguí trabajando con los modelos locales sin más insistencia.

**Concurrencia local:** a diferencia de los hubs de nube (que atienden varias consultas en paralelo), Ollama en esta PC solo puede tener un modelo generando activamente a la vez. Si una tarea necesita varias consultas seguidas, preferí quedarte con el mismo modelo local durante ese bloque en vez de saltar entre modelos para cada paso — alternar tiene un costo real de recarga.

**Pre-procesamiento local obligatorio:** antes de escalar un error de terminal a un hub de nube, `qwen2.5-coder:7b` debe intentar resolverlo. Si falla 2 veces, escalar a `deepseek-r1:14b` (razonamiento local) antes de considerar un hub de nube. Solo si el modelo de razonamiento local también falla, escalar a un hub.

---

## 3. Lenguajes de Programación

No hay un lenguaje fijo impuesto de antemano. Para cada capa del proyecto (backend, frontend, scripts, etc.), elegí el lenguaje/framework más eficiente para esa tarea puntual — priorizando estabilidad, soporte y qué tan bien lo maneja el ecosistema de modelos disponibles (evitar elecciones exóticas que aumenten el riesgo de errores sutiles que ni vos ni el usuario detecten fácil). Si la elección no es obvia, explicá brevemente el motivo antes de aplicarla, no hace falta pedir aprobación salvo que sea una decisión de arquitectura mayor (ver Guardrails).

---

## 4. Metodología de Desarrollo: API-First por Funcionalidad

El desarrollo de una funcionalidad sigue este orden: **modelo de datos → endpoint(s) de backend, con tests → recién ahí, frontend que consume ese endpoint real.** El motivo no es solo prolijidad — construir y verificar UI visualmente (que suele implicar uso de navegador) contra una API que todavía no existe o va a cambiar es una fuente real de tokens desperdiciados, más aún si el problema no está en el frontend sino en un endpoint mal diseñado que hay que rehacer después.

- **Esto aplica por funcionalidad/flujo, no como bloqueo total del proyecto.** No hace falta terminar el 100% del backend de CineTrack antes de tocar cualquier frontend — alcanza con que el endpoint específico que esa pantalla necesita ya esté implementado y testeado (ver regla de Tests, sección de Protocolo de Resiliencia).
- **No incluye la configuración inicial de frontend** (scaffolding del proyecto, herramientas de build, sistema de diseño base) — eso no depende de ningún endpoint y se puede resolver en paralelo sin ningún desperdicio.
- **Los wireframes de referencia (`docs/`) sí deben consultarse durante el diseño del backend**, no solo al construir la UI — el contrato de cada endpoint debería anticipar qué necesita mostrar la pantalla real, para no tener que rediseñar la API después de ver el frontend funcionando. Consultar la descripción en texto de los wireframes primero; las imágenes originales, solo si hace falta un detalle visual que el texto no cubre.

---

## 5. Protocolo de Resiliencia (contra cortes de cuota)

La cuota de Antigravity nativo (Gemini/Claude) puede cortarse a mitad de una tarea larga, sin aviso previo, con bloqueos que pueden durar de horas a varios días.

- **Antes de ejecutar una tarea de más de ~5 pasos**, escribí el plan completo en un archivo real del proyecto (ej. `TASK_PLAN.md`), no solo en el chat. El chat se puede perder si se corta la sesión; el archivo, no.
- Los archivos ya editados **sobreviven al corte de cuota igual**, estén commiteados o no — eso no se pierde. El valor real de commitear seguido es distinto: le da a **otra herramienta u otra sesión** (por ejemplo, retomar en VS Code con un modelo diferente) un punto de partida limpio y verificable, sin tener que adivinar qué quedó a medio terminar en el working directory.
- **Comiteá después de cada paso chico que funcione**, no al final de toda la tarea.
- **Versionado:** un solo branch de trabajo por defecto. Para una tarea crítica o de alto riesgo, se puede abrir un branch temporal `feature/*` y mergearlo al terminar. Etiquetar (`git tag`) cuando se completa una funcionalidad importante, total o parcialmente, siguiendo convención tipo semver: `vMAJOR.FEATURE.BUGFIX` (ej. `v1.2.0` para una funcionalidad nueva, `v1.2.1` para un arreglo puntual, `v2.0.0` para un cambio grande de arquitectura o alcance).
- **Commits vs. push — frecuencias distintas:** comiteá localmente después de cada paso chico que funcione (barato, sin razón para esperar). El **push** a GitHub es menos frecuente — hacelo después de un hito importante, no en cada commit. Siempre avisale al usuario en el chat cuando se hizo un push (qué se subió y a qué branch), no hace falta pedir confirmación previa salvo que sea una operación destructiva (ver abajo).
- **Push a GitHub:** el usuario provee un token de acceso para autenticar. Nunca imprimir el token en el chat, logs, ni commitear un archivo que lo contenga. **Prohibido** sin confirmación explícita: force-push, reescribir historia, o borrar branches/tags.
- **Documentación viva del proyecto:** mantené actualizados, en la raíz del repo:
  - `README.md` — qué es el proyecto, cómo instalarlo y correrlo, variables de entorno necesarias.
  - `ARCHITECTURE.md` — stack elegido (Backend/Frontend/DB) y el *por qué* de cada decisión, modelo de datos, capas del sistema. Actualizalo cuando una decisión de arquitectura cambie, no solo al inicio.
  - `CHANGELOG.md` — qué cambió en cada tag, en lenguaje simple.
  - `ROADMAP.md` — un solo archivo con dos secciones: "Backlog" (pendientes sin priorizar) y "Próximas fases" (hitos planeados).
  Actualizalos como parte del mismo commit que cierra una tarea, no como una tarea aparte para "después".
- **Tests — selectivo, no exhaustivo (proyecto solo, plazo corto, cuota limitada):** priorizá tests unitarios para la **lógica de estados de título** (favorito/watchlist/siguiendo/vista y sus transiciones) — es lógica pura sin dependencias externas, barata de escribir, y es donde más casos borde sutiles aparecieron durante el diseño. Priorizá también **mocks para las llamadas a TMDB y al proveedor de IA** — el motivo principal no es solo cobertura, es evitar gastar cuota real de API en cada prueba manual mientras el código todavía se ajusta. No es necesario apuntar a cobertura total ni testear UI end-to-end o funciones triviales — el costo de mantenerlos actualizados mientras el diseño se sigue moviendo supera el beneficio a esta escala.
- **Documentación visual (diagramas, wireframes, mockups):** el usuario los genera con herramientas externas y los sube al proyecto por su cuenta. El agente NO debe generarlos de cero ni reemplazarlos — solo modificarlos si el usuario lo pide explícitamente o si un cambio de arquitectura los vuelve inconsistentes con el código real.
- **Si te toca retomar una tarea después de un corte de cuota** (posiblemente con otro modelo activo): no asumas que tenés memoria de lo anterior. Leé `TASK_PLAN.md` y el `git log`/`git diff` reciente antes de continuar, y confirmá con el usuario en qué paso quedó antes de seguir editando.

---

## 6. Gestión de Contexto y Tokens (Zero-Waste)

Una sesión muy larga (muchos turnos, archivos grandes pegados repetidamente, historiales de código extensos) consume cada vez más tokens por turno a medida que crece — no solo por lo nuevo, sino por tener que reprocesar todo lo anterior cada vez.

- **Prestá atención a señales de que la sesión se volvió pesada**: muchos turnos acumulados, adjuntos o salidas de terminal largas repetidas varias veces, o una tarea que ya se resolvió hace rato pero la conversación sigue extendiéndose por temas nuevos no relacionados.
- **Cuando lo notes, avisale al usuario proactivamente** — no esperes a que pregunte. Algo como: *"Esta sesión ya acumuló bastante contexto — para no seguir gastando tokens de más, convendría cerrarla acá y arrancar una nueva limpia."*
- **El corte debe ser seguro, no solo rápido:** antes de sugerirlo, confirmá que el estado actual ya quedó reflejado en `TASK_PLAN.md` y comiteado (ver sección 5) — si falta algo por guardar, hacelo primero, y recién después sugerí el corte.
- Esto es una sugerencia al usuario, no una decisión unilateral — la sesión no se corta sola, el usuario decide si abre la nueva.
- **No hace falta armar un resumen de la conversación para la sesión nueva, con una excepción puntual:** el repositorio (`TASK_PLAN.md` + `git log`/`diff` + documentación viva, sección 5) ya cumple esa función para todo lo **decidido** — es más confiable que un resumen manual paralelo que puede desactualizarse. Pero si el corte ocurre **en medio de una discusión todavía sin resolver** (algo que se está debatiendo, no algo ya definido), ahí sí conviene un resumen chico de ese punto puntual — no le corresponde todavía a `ARCHITECTURE.md` (que refleja decisiones tomadas, no debates abiertos), y perderlo forzaría a repetir el mismo razonamiento de cero en la sesión nueva. Este resumen es un puente de un solo uso para esa discusión específica, no un documento paralelo permanente.

---

## 7. Guardrails (Human-in-the-loop)

- Al finalizar una fase de planificación/arquitectura, generá la propuesta como Artifact, **detenete por completo**, y esperá aprobación explícita antes de tocar la terminal o crear archivos.
- Nunca subas credenciales, API keys, o datos sensibles a git. Confirmá que `.gitignore` cubre `.env` y cualquier archivo de configuración con secretos antes del primer commit de cada proyecto nuevo.
