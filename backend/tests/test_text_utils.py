import pytest
from app.core.text_utils import extract_tmdb_countries, is_latin_legible


def test_is_latin_legible_valid_titles():
    # Títulos en inglés y con acentos de lenguas europeas
    assert is_latin_legible("Snowy Mountain") is True
    assert is_latin_legible("Amélie") is True
    assert is_latin_legible("El laberinto del fauno") is True
    assert is_latin_legible("Cebollitas") is True
    assert is_latin_legible("Canımın İçi") is True  # Turco latino
    assert is_latin_legible("WALL·E") is True
    assert is_latin_legible("1917") is True
    assert is_latin_legible("300") is True
    assert is_latin_legible("Naruto") is True
    assert is_latin_legible("Squid Game") is True


def test_is_latin_legible_invalid_non_latin_titles():
    # Árabe
    assert is_latin_legible("جبل الحلال") is False
    assert is_latin_legible("المداح") is False
    # Chino
    assert is_latin_legible("丫丫") is False
    assert is_latin_legible("哆啦A梦TV版") is False
    # Coreano
    assert is_latin_legible("누나 친구 4") is False
    # Japonés
    assert is_latin_legible("名探偵コナン") is False
    assert is_latin_legible("進撃の巨人") is False
    # Cirílico
    assert is_latin_legible("Брат 2") is False
    # Cadenas vacías
    assert is_latin_legible("") is False
    assert is_latin_legible("   ") is False
    assert is_latin_legible(None) is False


def test_extract_tmdb_countries_priority_origin():
    # Si hay origin_country, lo prioriza aunque haya production_countries
    details = {
        "origin_country": ["FR", "GB"],
        "production_countries": [
            {"iso_3166_1": "US"},
            {"iso_3166_1": "FR"}
        ]
    }
    assert extract_tmdb_countries(details) == "FR, GB"


def test_extract_tmdb_countries_fallback_production():
    # Si origin_country está vacío, recurre a production_countries
    details = {
        "origin_country": [],
        "production_countries": [
            {"iso_3166_1": "US"},
            {"iso_3166_1": "CA"}
        ]
    }
    assert extract_tmdb_countries(details) == "US, CA"


def test_extract_tmdb_countries_none_when_empty():
    details = {
        "origin_country": [],
        "production_countries": []
    }
    assert extract_tmdb_countries(details) is None
