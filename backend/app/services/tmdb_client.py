import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TMDBClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_concurrency: int = 10,
        timeout: float = 15.0,
    ):
        self.api_key = api_key or settings.TMDB_API_KEY
        self.base_url = (base_url or settings.TMDB_BASE_URL).rstrip('/')
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/json",
            }
            # Si el token es largo (Read Access Token v4), va como Bearer
            if self.api_key and len(self.api_key) > 40:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        client = await self._get_client()
        req_params = dict(params or {})
        
        # Si la key es corta (v3), se envia como parametro api_key
        if self.api_key and len(self.api_key) <= 40:
            req_params["api_key"] = self.api_key
        
        req_params.setdefault("language", settings.TMDB_LANGUAGE)

        retries = 3
        backoff = 1.0

        for attempt in range(1, retries + 1):
            async with self.semaphore:
                try:
                    response = await client.request(method, endpoint, params=req_params)
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", backoff))
                        logger.warning(f"TMDB rate-limited (429). Reintentando en {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        backoff *= 2
                        continue
                    response.raise_for_status()
                    return response.json()
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    if attempt == retries:
                        logger.error(f"Error al llamar a TMDB endpoint {endpoint}: {exc}")
                        raise
                    logger.warning(f"Fallo intento {attempt}/{retries} en {endpoint}: {exc}. Reintentando...")
                    await asyncio.sleep(backoff)
                    backoff *= 1.5

        return {}

    async def get_genres(self, media_type: str = "movie") -> List[Dict[str, Any]]:
        endpoint = f"/genre/{media_type}/list"
        data = await self._request("GET", endpoint)
        return data.get("genres", [])

    async def discover(
        self,
        media_type: str,
        sort_by: str = "popularity.desc",
        page: int = 1,
        vote_count_gte: Optional[int] = None,
        release_date_gte: Optional[str] = None,
        release_date_lte: Optional[str] = None,
        vote_average_gte: Optional[float] = None,
        with_genres: Optional[str] = None,
    ) -> Dict[str, Any]:
        endpoint = f"/discover/{media_type}"
        params: Dict[str, Any] = {
            "sort_by": sort_by,
            "page": page,
        }
        if vote_count_gte is not None:
            params["vote_count.gte"] = vote_count_gte
        if vote_average_gte is not None:
            params["vote_average.gte"] = vote_average_gte
        if with_genres is not None:
            params["with_genres"] = with_genres

        if media_type == "movie":
            if release_date_gte:
                params["primary_release_date.gte"] = release_date_gte
            if release_date_lte:
                params["primary_release_date.lte"] = release_date_lte
        else:
            if release_date_gte:
                params["first_air_date.gte"] = release_date_gte
            if release_date_lte:
                params["first_air_date.lte"] = release_date_lte

        return await self._request("GET", endpoint, params=params)

    async def get_details(
        self,
        media_type: str,
        tmdb_id: int,
        append_to_response: str = "credits",
    ) -> Dict[str, Any]:
        endpoint = f"/{media_type}/{tmdb_id}"
        params = {}
        if append_to_response:
            params["append_to_response"] = append_to_response
        return await self._request("GET", endpoint, params=params)

    async def get_season_details(self, series_id: int, season_number: int) -> Dict[str, Any]:
        endpoint = f"/tv/{series_id}/season/{season_number}"
        return await self._request("GET", endpoint)

    async def search(
        self,
        media_type: str,
        query: str,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        endpoint = f"/search/{media_type}"
        params: Dict[str, Any] = {"query": query}
        if year is not None:
            if media_type == "movie":
                params["primary_release_year"] = year
            else:
                params["first_air_date_year"] = year
        return await self._request("GET", endpoint, params=params)

    async def get_reviews(
        self,
        media_type: str,
        tmdb_id: int,
        page: int = 1,
    ) -> Dict[str, Any]:
        endpoint = f"/{media_type}/{tmdb_id}/reviews"
        return await self._request("GET", endpoint, params={"page": page})

    async def get_changes(
        self,
        media_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
    ) -> Dict[str, Any]:
        endpoint = f"/{media_type}/changes"
        params: Dict[str, Any] = {"page": page}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._request("GET", endpoint, params=params)

    async def get_person(self, person_id: int) -> Dict[str, Any]:
        """Obtiene información de una persona/actor desde TMDB, incluyendo profile_path."""
        endpoint = f"/person/{person_id}"
        return await self._request("GET", endpoint)

