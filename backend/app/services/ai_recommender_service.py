import json
import logging
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
Tu objetivo es recomendar entre 3 y 5 títulos de películas o series al usuario, basándote en su pedido (prompt) y en su perfil de preferencias.

### REGLAS FUNDAMENTALES:
1. SOLO puedes recomendar títulos que estén explícitamente presentes en la lista de CANDIDATOS que se te proporciona. Está TERMINANTEMENTE PROHIBIDO inventar títulos o recomendar obras fuera de esa lista.
2. Cada recomendación debe incluir su "title_id" exacto (entero) y una breve "reason" en el idioma del usuario (español o inglés, coincidente con el prompt), explicando por qué le gustará y cómo conecta con su búsqueda o gustos.
3. El mensaje general "message" debe ser cálido, entusiasta y cinematográfico, redactado en el mismo idioma del usuario.
4. POLÍTICA DE INCERTIDUMBRE Y HEURÍSTICA DE PONDERACIÓN:
   - Si el usuario pide algo genérico o amplio ("recomiéndame algo bueno", "sorpréndeme", "qué puedo ver"): DEBES RESOLVER con confianza seleccionando 3 a 5 de los títulos con mayor puntaje (vote_average) y popularidad del pool. No te niegues a responder.
   - Si el usuario es muy específico ("película de terror espacial de los 80"): Pondera la concordancia temática por sobre la nota masiva.
   - SOLO si el pedido es incomprensible, contradictorio o una cadena sin sentido (ej: "asdasd", "qwerty") responde con:
     "status": "clarification_needed", "recommendations": [], y en "clarification_suggestions" incluye 3 o 4 preguntas/chips para ayudarlo (ej: ["¿Preferís una película o una serie?", "¿Qué género te atrae hoy?", "¿Buscás un clásico o un estreno?", "Sorpréndeme con lo mejor valorado"]).

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


def _build_user_message(prompt: str, user_context: Optional[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> str:
    """Construye el payload de contexto y candidatos que se envía al modelo."""
    lang = _detect_language(prompt)

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
        candidates_summary.append(
            f"- ID {c['id']}: \"{c['nombre']}\" ({c['tipo']}, {c.get('anio') or 'N/A'}) - Géneros: {', '.join(c.get('generos', []))} | Puntaje: {c.get('vote_average', 0.0)}★ ({c.get('vote_count', 0)} votos){director_text} | Sinopsis: {c.get('sinopsis_corta', '')}{snippet_text}"
        )

    return f"""CONSULTA DEL USUARIO:
"{prompt}"

IDIOMA DETECTADO: {lang.upper()}

CONTEXTO DEL USUARIO:
{context_text}

POOL DE CANDIDATOS DISPONIBLES EN CINETRACK ({len(candidates)} títulos):
{chr(10).join(candidates_summary)}

Genera la respuesta en formato JSON estricto siguiendo las reglas del sistema:"""


class AIRecommenderService:
    def __init__(self):
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

    async def _call_gemini(self, user_message: str) -> Dict[str, Any]:
        """Llamada directa asíncrona a Google Gemini API."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no configurada")

        url = f"{self.gemini_url}?key={settings.GEMINI_API_KEY}"
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
        """Llamada directa asíncrona a Groq API (Llama-3.3-70B)."""
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY no configurada")

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
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

    def _fallback_heuristic(self, prompt: str, user_context: Optional[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Respaldo determinista offline cuando no hay API keys o fallan los servicios externos."""
        lower = prompt.strip().lower()
        lang = _detect_language(prompt)

        # Detectar caso incomprensible (menos de 2 caracteres o letras repetidas sin sentido)
        if len(lower) < 2 or re.match(r"^[asdfghjklqwertyuiopzxcvbnm]+$", lower) and len(set(lower)) <= 2:
            if lang == "es":
                return {
                    "status": "clarification_needed",
                    "message": "No logré interpretar con claridad lo que estás buscando. ¿Podrías darme una pista adicional?",
                    "recommendations": [],
                    "clarification_suggestions": [
                        "¿Buscás una película o una serie?",
                        "¿Qué género tenés ganas de ver hoy?",
                        "Sorpréndeme con lo mejor valorado",
                        "Quiero un clásico de ciencia ficción"
                    ]
                }
            else:
                return {
                    "status": "clarification_needed",
                    "message": "I couldn't quite catch what you're looking for. Could you give me a bit more detail?",
                    "recommendations": [],
                    "clarification_suggestions": [
                        "Looking for a movie or TV series?",
                        "What genre are you in the mood for?",
                        "Surprise me with the top rated",
                        "Show me an 80s classic"
                    ]
                }

        # Seleccionar entre los 3 mejores candidatos del pool
        top_candidates = candidates[:3] if len(candidates) >= 3 else candidates
        recs = []
        for c in top_candidates:
            if lang == "es":
                recs.append({
                    "title_id": c["id"],
                    "reason": f"Excelente obra aclamada de {', '.join(c.get('generos', [])[:2])} con un puntaje de {c.get('vote_average', 8.0)}★ en la comunidad."
                })
            else:
                recs.append({
                    "title_id": c["id"],
                    "reason": f"Highly acclaimed {', '.join(c.get('generos', [])[:2])} title with a {c.get('vote_average', 8.0)}★ community score."
                })

        if lang == "es":
            msg = f"Basándome en tu búsqueda \"{prompt}\" y en las obras más destacadas de nuestro catálogo, aquí tienes una selección ideal para disfrutar:"
        else:
            msg = f"Based on your query \"{prompt}\" and our top-rated catalog titles, here is a handpicked selection for you:"

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
        candidates: List[Dict[str, Any]]
    ) -> RecommendationResponse:
        """Punto de entrada principal: orquesta llamada híbrida con conmutación por error."""
        if not candidates:
            lang = _detect_language(prompt)
            return RecommendationResponse(
                status="clarification_needed",
                message="No se encontraron títulos disponibles en el catálogo para esta consulta." if lang == "es" else "No matching titles were found in the catalog for this query.",
                recommendations=[],
                clarification_suggestions=["Explorar catálogo general", "Ver tendencias de hoy"],
                provider_used="none"
            )

        user_message = _build_user_message(prompt, user_context, candidates)
        candidate_ids = {c["id"] for c in candidates}

        raw_result: Optional[Dict[str, Any]] = None
        provider_used = "heuristic"

        # 1. Intentar proveedor primario
        primary = getattr(settings, "AI_RECOMMENDER_PRIMARY", "gemini").lower()

        if primary == "gemini" and settings.GEMINI_API_KEY:
            try:
                raw_result = await self._call_gemini(user_message)
                provider_used = "gemini"
            except Exception as e:
                logger.warning("Falla al invocar Gemini API (%s), intentando fallback a Groq...", e)

        if not raw_result and settings.GROQ_API_KEY:
            try:
                raw_result = await self._call_groq(user_message)
                provider_used = "groq"
            except Exception as e:
                logger.warning("Falla al invocar Groq API (%s)...", e)

        if not raw_result:
            logger.info("Activando fallback heurístico determinista para recomendador...")
            raw_result = self._fallback_heuristic(prompt, user_context, candidates)
            provider_used = "heuristic"

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

        # Si el status era 'recommended' pero la IA no devolvió ningún ID válido del pool, forzar candidatos top
        if status == "recommended" and not sanitized_recs:
            for c in candidates[:3]:
                sanitized_recs.append(
                    RecommendationItem(
                        title_id=c["id"],
                        reason="Seleccionado por alto puntaje y concordancia con el catálogo."
                    )
                )

        return RecommendationResponse(
            status="recommended" if sanitized_recs else status,
            message=message,
            recommendations=sanitized_recs,
            clarification_suggestions=clarification_suggestions,
            provider_used=provider_used
        )


ai_recommender_service = AIRecommenderService()
