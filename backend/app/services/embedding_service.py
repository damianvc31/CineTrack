import asyncio
import logging
from typing import Any, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Servicio para generar embeddings semánticos a través de la API oficial de Google AI Studio
    (usando gemini-embedding-001 / gemini-embedding-2 con outputDimensionality=768).
    Soporta rotación balanceada Round-Robin y conmutación por fallos entre múltiples API Keys.
    """

    def __init__(self, api_key: Optional[str] = None):
        raw_keys = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.api_keys: List[str] = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self._current_key_idx: int = 0
        self.model = getattr(settings, "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.dimension = getattr(settings, "EMBEDDING_DIMENSION", 768)

    def get_current_key(self) -> str:
        if not self.api_keys:
            return ""
        return self.api_keys[self._current_key_idx % len(self.api_keys)]

    def rotate_key(self) -> str:
        if not self.api_keys:
            return ""
        self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)
        new_key = self.get_current_key()
        masked = new_key[:8] + "..." if len(new_key) > 12 else "***"
        logger.info(f"Rotando a API Key index {self._current_key_idx} ({masked})")
        return new_key

    @staticmethod
    def build_title_text(
        nombre: str,
        tipo: str,
        generos: List[str],
        director: Optional[str] = None,
        sinopsis: Optional[str] = None,
    ) -> str:
        """
        Construye una representación textual condensada de la obra cinematográfica
        optimizada para captura conceptual en el espacio latente vectorial.
        """
        tipo_str = "Película" if tipo == "movie" else "Serie de TV"
        generos_str = ", ".join(generos) if generos else "General"
        dir_label = "Director" if tipo == "movie" else "Creador"
        dir_str = director.strip() if director and director.strip() else "Desconocido"
        sinopsis_str = sinopsis.strip() if sinopsis and sinopsis.strip() else "Sin sinopsis disponible."

        return (
            f"Título: {nombre}. "
            f"Tipo: {tipo_str}. "
            f"Géneros: {generos_str}. "
            f"{dir_label}: {dir_str}. "
            f"Sinopsis: {sinopsis_str}"
        )

    async def get_embedding(self, text: str, max_retries: int = 3) -> Optional[List[float]]:
        """
        Genera el vector de embedding para un único texto (ej. prompt de usuario o título individual).
        """
        if not self.api_keys:
            logger.warning("GEMINI_API_KEY no configurada. No se puede generar embedding.")
            return None

        clean_text = text.strip()
        if not clean_text:
            return None

        models_to_try = [self.model]
        for alt in ["gemini-embedding-2", "gemini-embedding-001"]:
            if alt not in models_to_try:
                models_to_try.append(alt)

        for _ in range(len(self.api_keys)):
            current_key = self.get_current_key()
            for model in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={current_key}"
                payload = {
                    "content": {"parts": [{"text": clean_text}]},
                    "outputDimensionality": self.dimension,
                }

                for attempt in range(max_retries):
                    try:
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            resp = await client.post(url, json=payload)
                            if resp.status_code == 200:
                                data = resp.json()
                                values = data.get("embedding", {}).get("values")
                                if values and len(values) == self.dimension:
                                    return values
                            elif resp.status_code in (429, 503):
                                if len(self.api_keys) > 1:
                                    self.rotate_key()
                                    break
                                delay = 2.0 * (attempt + 1)
                                logger.warning(
                                    f"Embedding rate-limit {resp.status_code} en {model}. Reintentando en {delay}s..."
                                )
                                await asyncio.sleep(delay)
                            else:
                                logger.error(f"Error {resp.status_code} en embedding {model}: {resp.text}")
                                break
                    except Exception as e:
                        logger.warning(f"Excepción en intento {attempt+1} para embedding: {e}")
                        await asyncio.sleep(1.0)

        logger.error("No se pudo generar embedding tras agotar modelos y keys.")
        return None

    async def get_embeddings_batch(
        self, texts: List[str], max_retries: int = 6
    ) -> List[Optional[List[float]]]:
        """
        Genera embeddings para una lista de textos usando batchEmbedContents.
        Balancea automáticamente entre las múltiples API Keys configuradas con enfriamiento inteligente.
        """
        if not self.api_keys or not texts:
            return [None] * len(texts)

        requests_payload = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t.strip() or "Sin información"}]},
                "outputDimensionality": self.dimension,
            }
            for t in texts
        ]

        last_was_ratelimit = False
        num_keys = len(self.api_keys)

        for attempt in range(max_retries):
            current_key = self.get_current_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={current_key}"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json={"requests": requests_payload})
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_embeddings = data.get("embeddings", [])
                        results = []
                        for item in raw_embeddings:
                            vals = item.get("values")
                            if vals and len(vals) == self.dimension:
                                results.append(vals)
                            else:
                                results.append(None)
                        if len(results) == len(texts):
                            # Rotación proactiva round-robin entre lotes exitosos
                            if num_keys > 1:
                                self.rotate_key()
                            return results
                    elif resp.status_code in (429, 503):
                        last_was_ratelimit = True
                        if "perday" in resp.text.lower() and current_key in self.api_keys and len(self.api_keys) > 1:
                            logger.warning(
                                f"API Key {current_key[:12]}... agotó su cuota DIARIA (1.000 req/día). "
                                f"Desactivándola de la rotación activa."
                            )
                            self.api_keys.remove(current_key)
                            self._current_key_idx = 0
                            num_keys = len(self.api_keys)
                            await asyncio.sleep(1.0)
                            continue

                        if num_keys > 1:
                            self.rotate_key()
                            if (attempt + 1) % num_keys == 0:
                                logger.warning(
                                    f"Todas las API Keys activas ({num_keys}) han recibido 429. "
                                    f"Pausando 20s para enfriamiento de ventana por minuto de Google..."
                                )
                                await asyncio.sleep(20.0)
                            else:
                                logger.warning(
                                    "Batch rate-limit 429 en key actual. Conmutando de inmediato a la siguiente API Key..."
                                )
                                await asyncio.sleep(1.0)
                        else:
                            delay = 15.0 * (attempt + 1)
                            logger.warning(f"Batch embedding rate-limit {resp.status_code}. Pausando {delay}s...")
                            await asyncio.sleep(delay)
                    else:
                        last_was_ratelimit = False
                        logger.error(f"Batch embedding falló con código {resp.status_code}: {resp.text}")
                        break
            except Exception as e:
                logger.warning(f"Excepción en batch embedding intento {attempt+1}: {e}")
                await asyncio.sleep(2.0)

        if last_was_ratelimit:
            logger.warning("Lote omitido temporalmente tras agotar reintentos con enfriamiento por rate-limit.")
            return [None] * len(texts)

        return [None] * len(texts)
