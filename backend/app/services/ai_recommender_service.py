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

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Asistente Cinematográfico Inteligente de CineTrack.
Tu objetivo es recomendar entre 2 y 5 títulos de películas o series al usuario, basándote en su pedido (prompt) y en su perfil de preferencias.

### REGLAS FUNDAMENTALES:
1. SOLO puedes recomendar títulos que estén explícitamente presentes en la lista de CANDIDATOS que se te proporciona. Está TERMINANTEMENTE PROHIBIDO inventar títulos o recomendar obras fuera de esa lista.
2. Cada recomendación debe incluir su "title_id" exacto (entero) y una breve "reason" redactada ESTRICTAMENTE en el idioma especificado en la consulta (español o inglés). Explica el porqué de la recomendación haciendo referencia al director, actores, género, trama o tono solicitado.
3. El mensaje general "message" debe ser cálido, entusiasta y cinematográfico, redactado ESTRICTAMENTE en el idioma especificado en la consulta.
4. POLÍTICA DE INCERTIDUMBRE Y RESOLUCIÓN OBLIGATORIA:
   - AFINIDAD ESTRICTA VS. RELLENO: Es preferible recomendar 2 o 3 títulos con estricta y genuina afinidad temática, autoral o de tono antes que rellenar con obras no relacionadas solo por alcanzar un cupo numérico. NUNCA incluyas obras que no guarden relación con el pedido temático del usuario (ej: si piden "películas de robos y atracos/heist", jamás recomiendes una comedia de viajes en el tiempo solo porque tenga alta nota). Si en el pool hay solo 2 o 3 obras que encajan genuinamente, recomienda solo esas y aclara en el mensaje de apertura que son las joyas ideales disponibles en el catálogo para ese criterio.
   - SIEMPRE que haya al menos 1 o 2 títulos en el pool de candidatos que guarden afinidad con el pedido (por género, temática, director, actor o tono), DEBES RESPONDER con "status": "recommended". Nunca respondas que no hay títulos en el catálogo si dispones de candidatos afines.
   - Si el usuario pide algo genérico o amplio ("recomiéndame algo bueno", "sorpréndeme", "qué puedo ver"): DEBES RESOLVER con confianza seleccionando 3 a 5 de los títulos con mayor puntaje y popularidad del pool.
   - ÚNICAMENTE si el prompt es un texto ininteligible o caracteres aleatorios sin ningún sentido lingüístico o temático (ej: "asdasd", "12345", "qwerty") responde con:
     "status": "clarification_needed", "recommendations": [], y en "clarification_suggestions" incluye de 3 a 4 opciones de búsqueda concretas y atractivas para que el usuario explore (ej: ["Películas de ciencia ficción y viajes espaciales", "Thrillers y misterio policial", "Clásicos aclamados (+8.5★)", "Películas de Christopher Nolan"]). NUNCA hagas preguntas retóricas en clarification_suggestions.

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


def _build_user_message(
    prompt: str,
    user_context: Optional[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    language: Optional[str] = None
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

    return f"""CONSULTA DEL USUARIO:
"{prompt}"

IDIOMA OBLIGATORIO DE RESPUESTA: {lang_name} ({lang.upper()})
DIRECTIVA CRÍTICA: Debes redactar el mensaje de apertura ('message') y ABSOLUTAMENTE TODAS las justificaciones ('reason') en {lang_name}. NO uses otro idioma bajo ninguna circunstancia.

CONTEXTO DEL USUARIO:
{context_text}{instructions_extra}

POOL DE CANDIDATOS DISPONIBLES EN CINETRACK ({len(candidates)} títulos):
{chr(10).join(candidates_summary)}

Genera la respuesta en formato JSON estricto siguiendo las reglas del sistema:"""


class AIRecommenderService:
    def __init__(self):
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

    async def _call_gemini(self, user_message: str) -> Dict[str, Any]:
        """Llamada directa asíncrona a Google Gemini API."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no configurada")

        gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
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

    async def _call_groq(self, user_message: str) -> Dict[str, Any]:
        """Llamada directa asíncrona a Groq API."""
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY no configurada")

        groq_model = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
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

    async def _call_gemini_with_retry(self, user_message: str, max_retries: int = 2) -> Dict[str, Any]:
        """Invoca Gemini API con reintentos espaciados ante errores temporales (429, 503, timeouts)."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await self._call_gemini(user_message)
            except Exception as e:
                last_error = e
                logger.warning(f"Intento {attempt + 1}/{max_retries} en Gemini API falló: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.5)
        raise last_error

    async def _call_groq_with_retry(self, user_message: str, max_retries: int = 2) -> Dict[str, Any]:
        """Invoca Groq API con reintentos espaciados ante errores temporales."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await self._call_groq(user_message)
            except Exception as e:
                last_error = e
                logger.warning(f"Intento {attempt + 1}/{max_retries} en Groq API falló: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.5)
        raise last_error

    def _fallback_heuristic(
        self,
        prompt: str,
        user_context: Optional[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Respaldo offline de último recurso: puntúa y selecciona dinámicamente los candidatos más afines al prompt."""
        lower = prompt.strip().lower()
        lang = language or _detect_language(prompt)

        # Detectar caso incomprensible (menos de 2 caracteres o letras repetidas sin sentido)
        if len(lower) < 2 or (re.match(r"^[asdfghjklqwertyuiopzxcvbnm]+$", lower) and len(set(lower)) <= 2):
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
        prompt_words = set(re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]{3,}", lower))

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
            if any(w in gen_str for w in prompt_words):
                score += 25.0

            syn_str = (c.get("sinopsis_corta") or "").lower()
            syn_matches = sum(1 for w in prompt_words if w in syn_str)
            score += min(syn_matches * 15.0, 45.0)

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
        language: Optional[str] = "es"
    ) -> RecommendationResponse:
        """Punto de entrada principal: orquesta llamada con reintentos antes de caer en heurístico."""
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

        user_message = _build_user_message(prompt, user_context, candidates, language=language)
        candidate_ids = {c["id"] for c in candidates}

        raw_result: Optional[Dict[str, Any]] = None
        provider_used = "heuristic"
        model_used = "Motor Heurístico Local (CineTrack Recommender Engine)"

        primary = getattr(settings, "AI_RECOMMENDER_PRIMARY", "gemini").lower()
        providers_order = ["gemini", "groq"] if primary == "gemini" else ["groq", "gemini"]

        for prov in providers_order:
            if raw_result:
                break

            if prov == "gemini" and settings.GEMINI_API_KEY:
                try:
                    raw_result = await self._call_gemini_with_retry(user_message, max_retries=2)
                    provider_used = "gemini"
                    model_used = getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
                except Exception as e:
                    logger.warning("Falla persistente en Gemini API (%s), evaluando siguiente proveedor...", e)

            elif prov == "groq" and settings.GROQ_API_KEY:
                try:
                    raw_result = await self._call_groq_with_retry(user_message, max_retries=2)
                    provider_used = "groq"
                    model_used = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
                except Exception as e:
                    logger.warning("Falla persistente en Groq API (%s), evaluando siguiente proveedor...", e)

        # Último recurso: Motor heurístico offline si fallaron ambos servicios en la nube
        if not raw_result:
            logger.info("Todos los servicios de IA en la nube fallaron o no están disponibles. Activando motor heurístico local como último recurso...")
            raw_result = self._fallback_heuristic(prompt, user_context, candidates, language=language)
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
