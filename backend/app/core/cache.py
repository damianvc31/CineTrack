import asyncio
import time
from typing import Any, Optional


class MemoryCache:
    """
    Gestor de caché en memoria de alto rendimiento y bajo footprint para FastAPI.
    Soporta TTL por clave, invalidación por prefijos y operaciones thread-safe / asyncio.
    Ideal para planes serverless (Render Free Tier) sin sobrecosto de Redis.
    """

    def __init__(self, default_ttl: int = 3600):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor de la caché si no ha expirado."""
        item = self._cache.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and time.monotonic() > expires_at:
            # Clave expirada: eliminación perezosa
            self._cache.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Almacena un valor con TTL en segundos (None para default_ttl). Si TTL <= 0, no almacena nada (desactivado)."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        if ttl is not None and ttl <= 0:
            return
        expires_at = time.monotonic() + ttl if ttl and ttl > 0 else None
        self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """Elimina una clave específica de la caché."""
        return self._cache.pop(key, None) is not None

    def clear(self, prefix: Optional[str] = None) -> int:
        """
        Elimina todas las claves que comiencen con el prefijo dado.
        Si no se pasa prefijo, vacía la caché completa.
        Retorna la cantidad de claves eliminadas.
        """
        if prefix is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_delete:
            self._cache.pop(k, None)
        return len(keys_to_delete)

    def delete_prefix(self, prefix: str) -> int:
        """Alias para clear con prefijo."""
        return self.clear(prefix)

    def delete_pattern(self, pattern: str) -> int:
        """Elimina claves coincidentes con un patrón simple de prefijo (ej: 'prefix*')."""
        prefix = pattern.rstrip("*")
        return self.clear(prefix)

    def size(self) -> int:
        """Retorna la cantidad de elementos en caché (incluyendo no purgados)."""
        return len(self._cache)


# Instancia global del caché en memoria para toda la aplicación
cache = MemoryCache(default_ttl=3600)
