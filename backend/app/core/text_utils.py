import unicodedata
from typing import Any, Dict, Optional


def is_latin_legible(text: Optional[str]) -> bool:
    """
    Verifica si una cadena es legible para una audiencia occidental.
    Retorna True si todos los caracteres alfabéticos pertenecen al alfabeto latino
    (incluyendo acentos y diacríticos europeos: español, francés, alemán, turco, etc.),
    o si está compuesta únicamente por números y símbolos (ej. '1917', '300').
    Retorna False si contiene caracteres de alfabetos no latinos (árabe, CJK, cirílico, hangul, etc.)
    o si está vacía.
    """
    if not text or not text.strip():
        return False

    for char in text:
        if char.isalpha():
            name = unicodedata.name(char, "")
            # En la tabla Unicode oficial, todo caracter de alfabeto latino inicia con 'LATIN'
            if not name.startswith("LATIN"):
                return False

    return True


def extract_tmdb_countries(details: Dict[str, Any], max_countries: int = 4) -> Optional[str]:
    """
    Extrae la lista consolidada de códigos de país (ISO 3166-1 alpha-2) en mayúsculas.
    Prioridad 1: details.get('origin_country') (países de origen cultural/creativo).
    Prioridad 2 (Fallback): details.get('production_countries') (si origin_country viene vacío).
    Devuelve un string delimitado por comas (ej. 'FR, GB' o 'US, CA') o None si no hay información.
    """
    raw_origin = details.get("origin_country") or []
    if isinstance(raw_origin, str):
        raw_origin = [raw_origin]

    countries: list[str] = [
        c.strip().upper() for c in raw_origin if isinstance(c, str) and c.strip()
    ]

    if not countries:
        prod_countries = details.get("production_countries") or []
        for item in prod_countries:
            if isinstance(item, dict):
                code = item.get("iso_3166_1")
                if code and isinstance(code, str) and code.strip():
                    countries.append(code.strip().upper())

    # Desduplicar preservando orden
    seen = set()
    unique = [c for c in countries if not (c in seen or seen.add(c))]

    if not unique:
        return None

    return ", ".join(unique[:max_countries])
