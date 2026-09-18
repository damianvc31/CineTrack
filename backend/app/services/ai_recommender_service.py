import asyncio
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.schemas.recommendations import (
    RecommendationItem,
    RecommendationResponse,
)
from app.services.catalog_service import THEME_EXPANSION_MAP

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Asistente Cinematográfico Inteligente de CineTrack.
Tu objetivo es recomendar entre 2 y 5 títulos de películas o series al usuario, basándote en su pedido (prompt) y en su perfil de preferencias.

### REGLAS FUNDAMENTALES:
1. SOLO puedes recomendar títulos que estén explícitamente presentes en la lista de CANDIDATOS que se te proporciona. Está TERMINANTEMENTE PROHIBIDO inventar títulos o recomendar obras fuera de esa lista.
2. Cada recomendación debe incluir su "title_id" exacto (entero) y una breve "reason" redactada ESTRICTAMENTE en el idioma especificado en la consulta (español o inglés). Explica el porqué de la recomendación haciendo referencia al director, actores, género, trama o tono solicitado.
3. El mensaje general "message" debe ser cálido, entusiasta y cinematográfico, redactado ESTRICTAMENTE en el idioma especificado en la consulta.
4. POLÍTICA DE INCERTIDUMBRE Y RESOLUCIÓN OBLIGATORIA:
   - AFINIDAD ESTRICTA VS. RELLENO: Es preferible recomendar 2 o 3 títulos con estricta y genuina afinidad temática, autoral o de tono antes que rellenar con obras no relacionadas solo por alcanzar un cupo numérico. NUNCA incluyas obras que no guarden relación con el pedido temático del usuario (ej: si piden "películas de robos y atracos/heist", jamás recomiendes una comedia de viajes en el tiempo solo porque tenga alta nota). Si en el pool hay solo 2 o 3 obras que encajan genuinamente, recomienda solo esas y aclara en el mensaje de apertura que son las joyas ideales disponibles en el catálogo para ese criterio.
   - PREFERENCIA TEMÁTICA ESTRICTA: Si el usuario solicita una dinámica, subgénero o temática puntual (como "planes elaborados", "atracos/robos/heist", "asesinos en serie", "venganza", "viajes en el tiempo", etc.), debes seleccionar prioritariamente aquellas obras cuya premisa o sinopsis aborde DIRECTAMENTE esa temática. NO selecciones títulos simplemente porque pertenezcan a la categoría general de género si su trama no tiene relación con el pedido específico (ejemplo: si piden "thrillers de crimen y planes elaborados", recomienda obras como Heat, The Usual Suspects, Reservoir Dogs, Lock Stock, Nine Queens, etc., y NUNCA documentales de narcotraficantes o dramas ajenos a la temática).
   - SIEMPRE que haya al menos 1 o 2 títulos en el pool de candidatos que guarden afinidad con el pedido (por género, temática, director, actor o tono), DEBES RESPONDER con "status": "recommended". Nunca respondas que no hay títulos en el catálogo si dispones de candidatos afines.
   - Si el usuario pide algo genérico o amplio ("recomiéndame algo bueno", "sorpréndeme", "qué puedo ver"): DEBES RESOLVER con confianza seleccionando 3 a 5 de los títulos con mayor puntaje y popularidad del pool.
   - ÚNICAMENTE si el prompt es un texto ininteligible o caracteres aleatorios sin ningún sentido lingüístico o temático (ej: "asdasd", "12345", "qwerty") responde con:
     "status": "clarification_needed", "recommendations": [], y en "clarification_suggestions" incluye de 3 a 4 opciones de búsqueda concretas y atractivas para que el usuario explore (ej: ["Películas de ciencia ficción y viajes espaciales", "Thrillers y misterio policial", "Clásicos aclamados (+8.5★)", "Películas de Christopher Nolan"]). NUNCA hagas preguntas retóricas en clarification_suggestions.
   - PROHIBICIÓN ESTRICTA DE SOBREINTERPRETACIÓN:
     Está TERMINANTEMENTE PROHIBIDO interpretar combinaciones aleatorias de caracteres, letras y números, palabras inexistentes o secuencias sin sentido (ej: "asdf123", "x89f2a", "zxcvbnm", etc.) como si fueran "códigos secretos", "enigmas misteriosos", "criptografía", "hackers" o "películas de misterio/suspenso". Ante cualquier texto sin significado lingüístico ni temático real, DEBES responder OBLIGATORIAMENTE con "status": "clarification_needed", NUNCA asociarlo creativamente con el género de misterio.

### FORMATO DE RESPUESTA OBLIGATORIO (JSON ESTRICTO):
Debes responder ÚNICAMENTE un objeto JSON válido con esta estructura:
{
  "status": "recommended",
  "message": "...",
  "recommendations": [
    {"title_id": 123, "reason": "..."},
    {"title_id": 456, "reason": "..."}
  ],
  "clarification_suggestions": []
}
O en caso de incertidumbre:
{
  "status": "clarification_needed",
  "message": "...",
  "recommendations": [],
  "clarification_suggestions": ["...", "..."]
}
No incluyas etiquetas markdown adicionales ni texto fuera del JSON.
"""


def _detect_language(prompt: str) -> str:
    """Heurística simple para detectar si el prompt está en español o inglés."""
    lower = prompt.lower()
    spanish_indicators = [
        "pelicula", "película", "serie", "quiero", "algo", "bueno", "buenas", "recomiendame",
        "recomendame", "recomienda", "terror", "comedia", "accion", "acción", "para", "ver",
        "como", "historia", "clasico", "clásico", "suspenso", "ciencia ficcion"
    ]
    if any(re.search(rf"\b{word}\b", lower) for word in spanish_indicators):
        return "es"
    return "en"


def _parse_model_list(models_str: str) -> List[str]:
    """Parsea una lista de nombres de modelos separados por comas eliminando espacios en blanco."""
    return [m.strip() for m in models_str.split(",") if m.strip()]


def _build_user_message(
    prompt: str,
    user_context: Optional[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    language: Optional[str] = None,
    clarification_context: Optional[Dict[str, Any]] = None
) -> str:
    """Construye el payload de contexto y candidatos que se envía al modelo."""
    lang = language or _detect_language(prompt)
    lang_name = "ESPAÑOL" if lang == "es" else "INGLÉS"

    context_text = "Usuario invitado (sin historial previo en CineTrack)."
    if user_context and user_context.get("has_history"):
        favs = [f"{f['nombre']}" for f in user_context.get("favorites", [])[:6]]
        high_rated = [f"{h['nombre']} ({h['puntaje']}★)" for h in user_context.get("high_rated", [])[:6]]
        genres = user_context.get("top_genres", [])

        context_text = f"""
Perfil del usuario:
- Géneros favoritos/más vistos: {', '.join(genres) if genres else 'Varios'}
- Títulos en Favoritos: {', '.join(favs) if favs else 'Ninguno'}
- Títulos mejor puntuados por él: {', '.join(high_rated) if high_rated else 'Sin calificaciones aún'}
"""

    candidates_summary = []
    for c in candidates:
        snippet_text = f" | Opinión comunidad: \"{c['community_review_snippet']}\"" if c.get("community_review_snippet") else ""
        director_text = f" | Director: {c['director']}" if c.get("director") else ""
        actors_list = c.get("actores", [])
        actors_text = f" | Elenco: {', '.join(actors_list[:3])}" if actors_list else ""
        watched_text = " [YA VISTO POR EL USUARIO]" if c.get("is_watched") else ""
        candidates_summary.append(
            f"- ID {c['id']}: \"{c['nombre']}\" ({c['tipo']}, {c.get('anio') or 'N/A'}{watched_text}) - Géneros: {', '.join(c.get('generos', []))} | Puntaje: {c.get('vote_average', 0.0)}★ ({c.get('vote_count', 0)} votos){director_text}{actors_text} | Sinopsis: {c.get('sinopsis_corta', '')}{snippet_text}"
        )

    instructions_extra = ""
    if user_context and user_context.get("only_watched"):
        instructions_extra = "\nATENCIÓN: El usuario solicitó recomendaciones EXCLUSIVAMENTE extraídas de los títulos que ya ha visto en su historial en CineTrack. Enfoca las razones en por qué vale la pena volver a verlas (rewatch)."
    elif user_context and user_context.get("allow_rewatch"):
        instructions_extra = "\nNOTA: El usuario permite o solicitó títulos para volver a ver (rewatch). Puedes incluir tanto obras ya vistas como no vistas."

    clarification_section = ""
    if clarification_context:
        prev_p = clarification_context.get("previous_prompt", "")
        asst_m = clarification_context.get("assistant_message", "")
        suggs = clarification_context.get("suggestions", [])
        suggs_str = ", ".join(f'"{s}"' for s in suggs) if suggs else "Ninguna"
        clarification_section = f"""
DIÁLOGO PREVIO / ACLARACIÓN EN CURSO:
- Consulta inicial previa del usuario: "{prev_p}"
- Repregunta o aclaración que formuló el Asistente: "{asst_m}"
- Opciones o sugerencias que se ofrecieron: [{suggs_str}]
- Aclaración que responde el usuario ahora: "{prompt}"

DIRECTIVA OBLIGATORIA DE DIÁLOGO:
El usuario está respondiendo a la repregunta previa del asistente. Si su respuesta es breve (ej: "la primera", "la 2", "ambas", "sí", o un género específico), interpreta su intención en base a ese diálogo y a las opciones ofrecidas, y procede a recomendar los títulos afines del pool con "status": "recommended".
"""

    return f"""CONSULTA DEL USUARIO:
"{prompt}"{clarification_section}

IDIOMA OBLIGATORIO DE RESPUESTA: {lang_name} ({lang.upper()})
DIRECTIVA CRÍTICA: Debes redactar el mensaje de apertura ('message') y ABSOLUTAMENTE TODAS las justificaciones ('reason') en {lang_name}. NO uses otro idioma bajo ninguna circunstancia.

CONTEXTO DEL USUARIO:
{context_text}{instructions_extra}

POOL DE CANDIDATOS DISPONIBLES EN CINETRACK ({len(candidates)} títulos):
{chr(10).join(candidates_summary)}

Genera la respuesta en formato JSON estricto siguiendo las reglas del sistema:"""


CINEMA_KNOWN_KEYWORDS = {
    "pelicula", "peliculas", "película", "películas", "serie", "series", "temporada", "temporadas",
    "film", "films", "movie", "movies", "show", "shows", "cinema", "cine", "ver", "quiero",
    "recomiendame", "recomendame", "recomienda", "dame", "busco",
    "top", "mejor", "mejores", "best", "good", "actor", "actriz", "director", "directores",
    "accion", "acción", "action", "comedia", "comedy", "drama", "terror", "horror", "suspenso",
    "thriller", "misterio", "mystery", "ciencia", "ficcion", "ficción", "sci-fi", "scifi",
    "animacion", "animación", "animation", "anime", "documental", "documentary", "fantasia",
    "fantasía", "fantasy", "aventura", "aventuras", "adventure", "crimen", "crime", "romance",
    "romantica", "romántica", "western", "clasico", "clásico", "classic", "antigua", "reciente",
    "estreno", "estrenos", "nolan", "tarantino", "scorsese", "dicaprio", "spiderman", "batman",
    "sorprendeme", "sorpréndeme", "surprise", "popular", "populares", "visto", "vistas"
}

KEYBOARD_ROWS = [
    "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "poiuytrewq", "lkjhgfdsa", "mnbvcxz"
]


def is_unintelligible_prompt(prompt: str) -> bool:
    """Detecta deterministamente si el prompt es teclado machacado, sopa de caracteres o texto ininteligible."""
    clean = prompt.strip().lower()
    if len(clean) < 2:
        return True

    # Año de lanzamiento válido aislado (ej: '1999', '2024')
    if clean.isdigit():
        return not (len(clean) == 4 and 1900 <= int(clean) <= 2030)

    words = re.findall(r"[a-záéíóúñ0-9]+", clean)
    if not words:
        return True

    # 1. Tokens que mezclan letras y dígitos sin ser especificaciones técnicas comunes (ej: 'asdf123', 'h4', 'a1', 'x89f2a')
    for w in words:
        if re.search(r"[a-z]", w) and re.search(r"[0-9]", w):
            if not re.match(r"^(4k|3d|2d|1080p|720p|imax|se7en)$", w):
                return True

    # 2. Filas continuas de teclado o subcadenas evidentes
    for kr in KEYBOARD_ROWS:
        if clean in kr or kr in clean or any(w in kr and len(w) >= 3 for w in words if not w.isdigit()):
            return True

    # 3. Repetición cíclica (ej: 'asdasd', 'qweqwe', 'lalala')
    for w in words:
        if len(w) >= 4 and not w.isdigit():
            for chunk_size in (2, 3):
                chunk = w[:chunk_size]
                if chunk * (len(w) // chunk_size) == w:
                    return True

    # 4. Consonantes consecutivas o sin vocales en tokens de letras
    for w in words:
        if not w.isdigit():
            if re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", w):
                return True
            vowels = len(re.findall(r"[aeiouáéíóú]", w))
            if len(w) >= 4 and vowels == 0:
                return True
            if len(w) >= 5 and (vowels / len(w)) < 0.2:
                return True

    # 5. Palabra única corta sin vocales o que no existe
    if len(words) == 1 and not words[0].isdigit():
        w = words[0]
        if len(w) <= 3 and w not in {"el", "la", "un", "una", "de", "del", "en", "por", "con", "sin", "top", "ver", "cine", "film", "the", "war"}:
            if not re.search(r"[aeiouáéíóú]", w):
                return True

    # 6. Combinación de 2 tokens: dígito arbitrario + token corto desconocido (ej: 'asd 123', 'abc 123', 'xyz 999')
    if len(words) == 2 and any(w.isdigit() for w in words) and any(not w.isdigit() for w in words):
        non_dig = [w for w in words if not w.isdigit()][0]
        dig = [w for w in words if w.isdigit()][0]
        is_year = len(dig) == 4 and 1900 <= int(dig) <= 2030
        if not is_year and len(non_dig) <= 3 and non_dig not in CINEMA_KNOWN_KEYWORDS:
            return True

    return False


class AIRecommenderService:
    def __init__(self):
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

    async def _call_gemini(self, user_message: str, model_override: Optional[str] = None) -> Dict[str, Any]:
        """Llamada directa asíncrona a Google Gemini API."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no configurada")

        gemini_model = model_override or getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": user_message}]}
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.3
            }
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)

    async def _call_groq(self, user_message: str, model_override: Optional[str] = None) -> Dict[str, Any]:
        """Llamada directa asíncrona a Groq API."""
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY no configurada")

        groq_model = model_override or getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": groq_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.groq_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            return json.loads(raw_text)

    async def _call_gemini_with_retry(self, user_message: str, max_retries: int = 2) -> tuple[Dict[str, Any], str]:
        """Invoca Gemini API con reintentos y cascada automática a modelos alternativos ante 429/503."""
        primary_model = getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
        models_to_try = [primary_model]
        for alt in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
            if alt != primary_model and alt not in models_to_try:
                models_to_try.append(alt)

        last_error = None
        for model in models_to_try:
            for attempt in range(max_retries):
                try:
                    res = await self._call_gemini(user_message, model_override=model)
                    return res, model
                except Exception as e:
                    last_error = e
                    logger.warning(f"Intento {attempt + 1}/{max_retries} en Gemini ({model}) falló: {e}")
                    # Si la cuota está agotada (429), pasar de inmediato al siguiente modelo con cuota fresca
                    if "429" in str(e) or "quota" in str(e).lower():
                        break
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0)
        raise last_error

    async def _call_groq_with_retry(self, user_message: str, max_retries: int = 2) -> tuple[Dict[str, Any], str]:
        """Invoca Groq API con reintentos y cascada automática a modelos alternativos ante 429/timeouts."""
        primary_model = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
        models_to_try = [primary_model]
        for alt in ["openai/gpt-oss-20b", "groq/compound-mini", "qwen/qwen3.8-27b"]:
            if alt != primary_model and alt not in models_to_try:
                models_to_try.append(alt)

        last_error = None
        for model in models_to_try:
            for attempt in range(max_retries):
                try:
                    res = await self._call_groq(user_message, model_override=model)
                    return res, model
                except Exception as e:
                    last_error = e
                    logger.warning(f"Intento {attempt + 1}/{max_retries} en Groq ({model}) falló: {e}")
                    # Si es 429 (límite de tasa por minuto o día), pasar de inmediato al siguiente modelo con cuota fresca
                    if "429" in str(e):
                        break
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0)
        raise last_error

    def _fallback_heuristic(
        self,
        prompt: str,
        user_context: Optional[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        language: Optional[str] = None,
        clarification_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Respaldo offline de último recurso: puntúa y selecciona dinámicamente los candidatos más afines al prompt."""
        lower = prompt.strip().lower()
        lang = language or _detect_language(prompt)

        is_valid_clarification_choice = False
        if clarification_context:
            clean_choice = lower
            valid_choices = {
                "1", "2", "3", "4", "5", "primera", "primero", "1era", "1ra", "segunda", "segundo",
                "2da", "tercera", "tercero", "3ra", "cuarta", "cuarto", "quinta", "quinto",
                "la 1", "la 2", "la 3", "la primera", "la segunda", "la tercera", "el primero", "el segundo", "el tercero",
                "ambas", "ambos", "todos", "todas", "ninguna", "ninguno", "cualquiera",
                "first", "second", "third", "both", "all", "none", "either", "the first", "the second", "the third"
            }
            if clean_choice in valid_choices:
                is_valid_clarification_choice = True

        # Detectar caso incomprensible
        if not is_valid_clarification_choice and is_unintelligible_prompt(prompt):
            if lang == "es":
                return {
                    "status": "clarification_needed",
                    "message": "No logré interpretar con claridad lo que estás buscando. ¿Podrías darme una pista adicional?",
                    "recommendations": [],
                    "clarification_suggestions": [
                        "Películas de ciencia ficción y viajes espaciales",
                        "Thrillers y misterio policial",
                        "Sorpréndeme con lo mejor valorado",
                        "Películas de Christopher Nolan"
                    ]
                }
            else:
                return {
                    "status": "clarification_needed",
                    "message": "I couldn't quite catch what you're looking for. Could you give me a bit more detail?",
                    "recommendations": [],
                    "clarification_suggestions": [
                        "Space sci-fi and time travel",
                        "Police mystery and thrillers",
                        "Surprise me with top rated",
                        "Christopher Nolan masterpieces"
                    ]
                }

        is_only_watched = bool(user_context and user_context.get("only_watched"))
        augmented_text = lower
        if clarification_context:
            prev_p = clarification_context.get("previous_prompt", "").lower()
            suggs = [s.lower() for s in clarification_context.get("suggestions", [])]
            if any(w in lower for w in ("primera", "primero", "1", "first")) and len(suggs) >= 1:
                augmented_text = f"{lower} {suggs[0]}"
            elif any(w in lower for w in ("segunda", "segundo", "2", "second")) and len(suggs) >= 2:
                augmented_text = f"{lower} {suggs[1]}"
            elif any(w in lower for w in ("tercera", "tercero", "3", "third")) and len(suggs) >= 3:
                augmented_text = f"{lower} {suggs[2]}"
            else:
                augmented_text = f"{lower} {prev_p} {' '.join(suggs)}"

        prompt_words = set(re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]{3,}", augmented_text))

        # Enriquecer términos temáticos bilingües (ES -> EN) para análisis en sinopsis y géneros
        thematic_syn_words: set[str] = set()
        for w in prompt_words:
            if w in THEME_EXPANSION_MAP:
                thematic_syn_words.update(THEME_EXPANSION_MAP[w])
        for term, en_terms in THEME_EXPANSION_MAP.items():
            if term in lower:
                thematic_syn_words.update(en_terms)

        # Puntuación heurística de afinidad para cada candidato en el pool
        scored_candidates = []
        for c in candidates:
            # Base por calificación y popularidad
            score = float(c.get("vote_average", 7.0)) * 1.5 + min(float(c.get("vote_count", 0)) / 1000.0, 4.0)

            dir_str = (c.get("director") or "").lower()
            if any(w in dir_str for w in prompt_words):
                score += 80.0

            act_str = " ".join(c.get("actores", [])).lower()
            if any(w in act_str for w in prompt_words):
                score += 60.0

            name_str = (c.get("nombre") or "").lower()
            if any(w in name_str for w in prompt_words):
                score += 50.0

            gen_str = " ".join(c.get("generos", [])).lower()
            if any(w in gen_str for w in (prompt_words | thematic_syn_words)):
                score += 25.0

            syn_str = (c.get("sinopsis_corta") or "").lower()
            # Bonificación prioritaria si la sinopsis coincide con conceptos temáticos clave (ej: heist, robbery, mastermind)
            thematic_matches = sum(1 for w in thematic_syn_words if len(w) >= 4 and w in syn_str)
            direct_matches = sum(1 for w in prompt_words if len(w) >= 4 and w in syn_str)
            syn_score = (thematic_matches * 25.0) + (direct_matches * 15.0)
            score += min(syn_score, 60.0)

            # Pequeño jitter aleatorio (0 a 1.5) para que búsquedas generales roten naturalmente
            score += random.uniform(0.0, 1.5)

            scored_candidates.append((score, c))

        # Ordenar candidatos de mayor a menor afinidad
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        # Si hubo coincidencias reales con términos del pedido, priorizar exclusivamente esas y evitar rellenar con obras no afines
        matching_candidates = [item[1] for item in scored_candidates if item[0] >= 30.0]
        if matching_candidates:
            top_candidates = matching_candidates[:4]
        else:
            top_candidates = [item[1] for item in scored_candidates[:4]]

        recs = []
        for c in top_candidates:
            director = c.get("director")
            actores = c.get("actores", [])
            generos = c.get("generos", [])
            rating = c.get("vote_average", 8.0)

            if is_only_watched:
                if lang == "es":
                    reason = f"Obra destacada de tu historial ({', '.join(generos[:2])}, {rating}★) que vale totalmente la pena volver a ver."
                else:
                    reason = f"A standout gem from your watch history ({', '.join(generos[:2])}, {rating}★) well worth rewatching."
            elif director and any(w in director.lower() for w in prompt_words):
                if lang == "es":
                    reason = f"Aclamada producción dirigida por {director} ({rating}★), referente imperdible en su género."
                else:
                    reason = f"Acclaimed work directed by {director} ({rating}★), a true benchmark in its genre."
            elif actores and any(w in " ".join(actores).lower() for w in prompt_words):
                matching_actor = next((a for a in actores if any(w in a.lower() for w in prompt_words)), actores[0])
                if lang == "es":
                    reason = f"Protagonizada por {matching_actor} con una actuación memorable ({rating}★)."
                else:
                    reason = f"Starring {matching_actor} with a standout performance ({rating}★)."
            elif generos:
                if lang == "es":
                    reason = f"Excelente obra de {', '.join(generos[:2])} aclamada con {rating}★ por la comunidad."
                else:
                    reason = f"Top-tier {', '.join(generos[:2])} title acclaimed with a {rating}★ rating."
            else:
                if lang == "es":
                    reason = f"Selección destacada en CineTrack con una valoración de {rating}★."
                else:
                    reason = f"Handpicked selection on CineTrack with a {rating}★ score."

            recs.append({"title_id": c["id"], "reason": reason})

        if is_only_watched:
            msg = "Revisando tus títulos vistos en CineTrack, te recomendamos revivir estas grandes obras:" if lang == "es" else "Looking back at your watched titles in CineTrack, here are fantastic gems to rewatch:"
        elif lang == "es":
            msg = f"Basándome en tu búsqueda \"{prompt}\" y en las obras más afines de nuestro catálogo, aquí tienes una selección ideal:"
        else:
            msg = f"Based on your query \"{prompt}\" and matching catalog titles, here is a handpicked selection for you:"

        return {
            "status": "recommended",
            "message": msg,
            "recommendations": recs,
            "clarification_suggestions": []
        }

    async def get_recommendation(
        self,
        prompt: str,
        user_context: Optional[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        language: Optional[str] = "es",
        clarification_context: Optional[Dict[str, Any]] = None,
        is_cancelled: Optional[Any] = None
    ) -> RecommendationResponse:
        """Punto de entrada principal: orquesta llamada con reintentos antes de caer en heurístico."""
        # 0. Si el cliente ya canceló la petición en vuelo, salir inmediatamente
        if is_cancelled and await is_cancelled():
            return RecommendationResponse(
                status="clarification_needed",
                message="Búsqueda cancelada por el usuario.",
                recommendations=[],
                clarification_suggestions=[],
                provider_used="heuristic",
                model_used="Cancelado"
            )

        # 1. Detección temprana determinista de texto ininteligible (caracteres aleatorios, teclado machacado, códigos)
        # Si hay contexto de aclaración, solo se permiten respuestas válidas (ej: "1", "la primera", "ambas").
        # Si el texto es ininteligible/basura, se rechaza de inmediato SIN llamar a LLMs.
        is_valid_clarification_choice = False
        if clarification_context:
            clean_choice = prompt.strip().lower()
            valid_choices = {
                "1", "2", "3", "4", "5", "primera", "primero", "1era", "1ra", "segunda", "segundo",
                "2da", "tercera", "tercero", "3ra", "cuarta", "cuarto", "quinta", "quinto",
                "la 1", "la 2", "la 3", "la primera", "la segunda", "la tercera", "el primero", "el segundo", "el tercero",
                "ambas", "ambos", "todos", "todas", "ninguna", "ninguno", "cualquiera",
                "first", "second", "third", "both", "all", "none", "either", "the first", "the second", "the third"
            }
            if clean_choice in valid_choices:
                is_valid_clarification_choice = True

        if not is_valid_clarification_choice and is_unintelligible_prompt(prompt):
            lang = language or _detect_language(prompt)
            if lang == "es":
                msg = "No he podido comprender tu mensaje. Por favor, dime qué género, actor, director o temática tienes ganas de ver hoy para poder darte una buena recomendación."
                suggestions = [
                    "Películas de ciencia ficción y viajes espaciales",
                    "Thrillers y misterio policial",
                    "Clásicos aclamados (+8.5★)",
                    "Películas de Christopher Nolan"
                ]
            else:
                msg = "I couldn't quite understand your query. Please tell me what genre, actor, director or theme you are in the mood for today."
                suggestions = [
                    "Space sci-fi and time travel",
                    "Police mystery and thrillers",
                    "Top rated classics (+8.5★)",
                    "Christopher Nolan masterpieces"
                ]
            return RecommendationResponse(
                status="clarification_needed",
                message=msg,
                recommendations=[],
                clarification_suggestions=suggestions,
                provider_used="heuristic",
                model_used="Validador de Entrada (CineTrack Recommender Engine)"
            )

        if not candidates:
            lang = language or _detect_language(prompt)
            if user_context and user_context.get("only_watched"):
                msg = "No encontramos títulos marcados como vistos en tu biblioteca para recomendar entre ellos. ¡Comienza marcando las películas y series que hayas visto!" if lang == "es" else "No watched titles found in your library to recommend from. Start marking your watched movies and series!"
            else:
                msg = "No se encontraron títulos disponibles en el catálogo para esta consulta." if lang == "es" else "No matching titles were found in the catalog for this query."
            suggestions = ["Explorar catálogo general", "Ver tendencias de hoy"] if lang == "es" else ["Explore full catalog", "See today's trending"]
            return RecommendationResponse(
                status="clarification_needed",
                message=msg,
                recommendations=[],
                clarification_suggestions=suggestions,
                provider_used="none",
                model_used="N/A"
            )

        user_message = _build_user_message(
            prompt,
            user_context,
            candidates,
            language=language,
            clarification_context=clarification_context
        )
        candidate_ids = {c["id"] for c in candidates}

        raw_result: Optional[Dict[str, Any]] = None
        provider_used = "heuristic"
        model_used = "Motor Heurístico Local (CineTrack Recommender Engine)"

        primary_prov = getattr(settings, "AI_RECOMMENDER_PRIMARY", "gemini").lower()
        secondary_prov = "groq" if primary_prov == "gemini" else "gemini"

        # Modelos principales y fallbacks configurados
        gemini_primary = getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
        gemini_fallbacks = _parse_model_list(getattr(settings, "GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest,gemini-3.5-flash-lite,gemini-3.8-flash"))
        groq_primary = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
        groq_fallbacks = _parse_model_list(getattr(settings, "GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b,groq/compound-mini,qwen/qwen3.8-27b"))

        models_by_prov = {
            "gemini": (gemini_primary, gemini_fallbacks),
            "groq": (groq_primary, groq_fallbacks),
        }

        # Secuencia ordenada de intentos:
        # Nivel 1: Modelos insignia principales (primero proveedor primario, luego proveedor secundario)
        cascade_schedule: List[tuple[str, str]] = [
            (primary_prov, models_by_prov[primary_prov][0]),
            (secondary_prov, models_by_prov[secondary_prov][0]),
        ]
        # Nivel 2: Modelos de respaldo ligeros (primero proveedor primario, luego proveedor secundario)
        for m in models_by_prov[primary_prov][1]:
            cascade_schedule.append((primary_prov, m))
        for m in models_by_prov[secondary_prov][1]:
            cascade_schedule.append((secondary_prov, m))

        for prov, model in cascade_schedule:
            if raw_result:
                break
            if is_cancelled and await is_cancelled():
                logger.info("Cliente canceló la solicitud durante la cascada. Deteniendo ejecución.")
                break

            if prov == "gemini" and settings.GEMINI_API_KEY:
                try:
                    raw_result = await self._call_gemini(user_message, model_override=model)
                    provider_used = "gemini"
                    model_used = model
                    break
                except Exception as e:
                    logger.warning("Falla en Gemini API con modelo '%s': %s", model, e)

            elif prov == "groq" and settings.GROQ_API_KEY:
                try:
                    raw_result = await self._call_groq(user_message, model_override=model)
                    provider_used = "groq"
                    model_used = model
                    break
                except Exception as e:
                    logger.warning("Falla en Groq API con modelo '%s': %s", model, e)

        # Si el cliente canceló durante la cascada, retornar de inmediato
        if is_cancelled and await is_cancelled():
            return RecommendationResponse(
                status="clarification_needed",
                message="Búsqueda cancelada por el usuario.",
                recommendations=[],
                clarification_suggestions=[],
                provider_used="heuristic",
                model_used="Cancelado"
            )

        # Último recurso: Motor heurístico offline si fallaron ambos servicios en la nube
        if not raw_result:
            logger.info("Todos los servicios de IA en la nube fallaron o no están disponibles. Activando motor heurístico local como último recurso...")
            raw_result = self._fallback_heuristic(
                prompt,
                user_context,
                candidates,
                language=language,
                clarification_context=clarification_context
            )
            provider_used = "heuristic"
            model_used = "Motor Heurístico Local (CineTrack Recommender Engine)"

        # Validar y sanear la respuesta
        status = raw_result.get("status", "recommended")
        message = raw_result.get("message", "Recomendación generada.")
        clarification_suggestions = raw_result.get("clarification_suggestions", [])

        # Filtrar recomendaciones para que ÚNICAMENTE contengan IDs reales presentes en el pool
        sanitized_recs: List[RecommendationItem] = []
        for r in raw_result.get("recommendations", []):
            tid = r.get("title_id")
            if tid in candidate_ids:
                sanitized_recs.append(
                    RecommendationItem(
                        title_id=tid,
                        reason=r.get("reason", "Título seleccionado por afinidad.")
                    )
                )

        # Si el status era 'recommended' pero la IA no devolvió ningún ID válido del pool, seleccionar los más relevantes
        if status == "recommended" and not sanitized_recs:
            for c in candidates[:4]:
                sanitized_recs.append(
                    RecommendationItem(
                        title_id=c["id"],
                        reason="Seleccionado por concordancia temática y alto puntaje en el catálogo."
                    )
                )

        return RecommendationResponse(
            status="recommended" if sanitized_recs else status,
            message=message,
            recommendations=sanitized_recs,
            clarification_suggestions=clarification_suggestions,
            provider_used=provider_used,
            model_used=model_used
        )


ai_recommender_service = AIRecommenderService()
