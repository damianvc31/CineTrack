from datetime import date
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Genero, Titulo, titulos_generos
from app.schemas.recommendations import RecommendationItem, RecommendationResponse


@pytest.fixture
async def sample_catalog_for_recs(db_session: AsyncSession):
    # Generos
    g_sci_fi = Genero(id=878, nombre="Ciencia ficción")
    g_drama = Genero(id=18, nombre="Drama")
    g_action = Genero(id=28, nombre="Acción")
    db_session.add_all([g_sci_fi, g_drama, g_action])
    await db_session.flush()

    # Titulos
    m1 = Titulo(
        id=1,
        tmdb_id=101,
        tipo="movie",
        nombre="Interstellar",
        sinopsis="Un grupo de exploradores viaja a través de un agujero de gusano en el espacio.",
        fecha_estreno=date(2014, 11, 7),
        duracion=169,
        director="Christopher Nolan",
        pais="US",
        idioma_original="en",
        popularidad=200.0,
        vote_average_tmdb=8.6,
        vote_count_tmdb=30000,
        rating_unificado=8.6
    )
    m2 = Titulo(
        id=2,
        tmdb_id=102,
        tipo="movie",
        nombre="Inception",
        sinopsis="Un ladrón roba secretos corporativos mediante el uso de la tecnología de compartir sueños.",
        fecha_estreno=date(2010, 7, 16),
        duracion=148,
        director="Christopher Nolan",
        pais="US",
        idioma_original="en",
        popularidad=180.0,
        vote_average_tmdb=8.4,
        vote_count_tmdb=32000,
        rating_unificado=8.4
    )
    s1 = Titulo(
        id=3,
        tmdb_id=201,
        tipo="tv",
        nombre="Dark",
        sinopsis="La desaparición de dos niños expone las dobles vidas y relaciones fracturadas de cuatro familias.",
        fecha_estreno=date(2017, 12, 1),
        director="Baran bo Odar",
        pais="DE",
        idioma_original="de",
        popularidad=150.0,
        vote_average_tmdb=8.5,
        vote_count_tmdb=6000,
        rating_unificado=8.5,
        status_tmdb="Ended"
    )
    m3 = Titulo(
        id=4,
        tmdb_id=301,
        tipo="movie",
        nombre="Nueve Reinas",
        sinopsis="Dos estafadores se conocen en una estación de servicio en Buenos Aires y planean un gran robo.",
        fecha_estreno=date(2000, 8, 31),
        duracion=114,
        director="Fabián Bielinsky",
        pais="AR",
        idioma_original="es",
        popularidad=120.0,
        vote_average_tmdb=7.9,
        vote_count_tmdb=1500,
        rating_unificado=7.9
    )
    m4 = Titulo(
        id=5,
        tmdb_id=302,
        tipo="movie",
        nombre="Happy Together",
        sinopsis="Dos amantes de Hong Kong viajan a Buenos Aires, Argentina y viven una relación tormentosa.",
        fecha_estreno=date(1997, 5, 30),
        duracion=96,
        director="Wong Kar-wai",
        pais="HK",
        idioma_original="zh",
        popularidad=110.0,
        vote_average_tmdb=7.8,
        vote_count_tmdb=1200,
        rating_unificado=7.8
    )

    db_session.add_all([m1, m2, s1, m3, m4])
    await db_session.flush()

    # Relaciones generos
    await db_session.execute(
        titulos_generos.insert().values([
            {"titulo_id": 1, "genero_id": 878},
            {"titulo_id": 1, "genero_id": 18},
            {"titulo_id": 2, "genero_id": 878},
            {"titulo_id": 2, "genero_id": 28},
            {"titulo_id": 3, "genero_id": 878},
            {"titulo_id": 3, "genero_id": 18},
            {"titulo_id": 4, "genero_id": 80},
            {"titulo_id": 4, "genero_id": 18},
            {"titulo_id": 5, "genero_id": 18},
            {"titulo_id": 5, "genero_id": 10749},
        ])
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_recommendations_gemini_success(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test standard recommendation flow with Gemini returning valid titles."""
    mock_gemini_dict = {
        "status": "recommended",
        "message": "Aquí tienes unas excelentes opciones de ciencia ficción espacial:",
        "recommendations": [
            {
                "title_id": 1,
                "reason": "Una obra maestra de viajes espaciales y agujeros de gusano dirigida por Christopher Nolan."
            },
            {
                "title_id": 2,
                "reason": "Aunque transcurre en la mente, comparte la misma escala cerebral y tensión."
            }
        ],
        "clarification_suggestions": ["¿Prefieres algo más realista o más fantasioso?"]
    }

    with patch("app.services.ai_recommender_service.settings.GEMINI_API_KEY", "mock-gemini-key"), \
         patch("app.services.ai_recommender_service.settings.AI_RECOMMENDER_PRIMARY", "gemini"), \
         patch("app.services.ai_recommender_service.ai_recommender_service._call_gemini", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_gemini_dict

        res = await async_client.post(
            "/api/v1/recommendations",
            json={"prompt": "Recomiéndame películas sobre viajes en el espacio y paradojas temporales"}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recommended"
        assert data["provider_used"] == "gemini"
        assert len(data["recommendations"]) == 2
        assert data["recommendations"][0]["title_id"] == 1
        assert data["recommendations"][0]["title"]["nombre"] == "Interstellar"
        assert data["recommendations"][0]["title"]["tipo"] == "movie"
        assert data["recommendations"][1]["title_id"] == 2
        assert data["recommendations"][1]["title"]["nombre"] == "Inception"


@pytest.mark.asyncio
async def test_recommendations_gemini_fails_falls_back_to_groq(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test fallback to Groq when Gemini raises an exception."""
    mock_groq_dict = {
        "status": "recommended",
        "message": "Te recomiendo esta serie de misterio y viajes en el tiempo:",
        "recommendations": [
            {
                "title_id": 3,
                "reason": "Dark es el referente definitivo en paradojas temporales de la última década."
            }
        ],
        "clarification_suggestions": ["¿Quieres series similares de otros países?"]
    }

    with patch("app.services.ai_recommender_service.settings.GEMINI_API_KEY", "mock-gemini-key"), \
         patch("app.services.ai_recommender_service.settings.GROQ_API_KEY", "mock-groq-key"), \
         patch("app.services.ai_recommender_service.settings.AI_RECOMMENDER_PRIMARY", "gemini"), \
         patch("app.services.ai_recommender_service.ai_recommender_service._call_gemini", side_effect=RuntimeError("Gemini 429 Rate Limit")), \
         patch("app.services.ai_recommender_service.ai_recommender_service._call_groq", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = mock_groq_dict

        res = await async_client.post(
            "/api/v1/recommendations",
            json={"prompt": "Algo sobre viajes en el tiempo"}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recommended"
        assert data["provider_used"] == "groq"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["title"]["nombre"] == "Dark"


@pytest.mark.asyncio
async def test_recommendations_heuristic_fallback(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test fallback to local heuristic engine when both AI providers fail or lack keys."""
    with patch("app.services.ai_recommender_service.settings.GEMINI_API_KEY", ""), \
         patch("app.services.ai_recommender_service.settings.GROQ_API_KEY", ""):

        res = await async_client.post(
            "/api/v1/recommendations",
            json={"prompt": "ciencia ficcion"}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recommended"
        assert data["provider_used"] == "heuristic"
        assert len(data["recommendations"]) > 0
        first_rec = data["recommendations"][0]
        assert first_rec["title"] is not None
        assert "★" in first_rec["reason"]


@pytest.mark.asyncio
async def test_recommendations_clarification_needed(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test prompt ambiguity leading to clarification_needed status with suggestions."""
    mock_clarification = {
        "status": "clarification_needed",
        "message": "¿Podrías darme una pista sobre qué género o estado de ánimo buscas?",
        "recommendations": [],
        "clarification_suggestions": [
            "Algo de acción y adrenalina",
            "Una buena película de ciencia ficción",
            "Sorpréndeme con lo mejor del catálogo"
        ]
    }

    with patch("app.services.ai_recommender_service.settings.GEMINI_API_KEY", "mock-gemini-key"), \
         patch("app.services.ai_recommender_service.settings.AI_RECOMMENDER_PRIMARY", "gemini"), \
         patch("app.services.ai_recommender_service.ai_recommender_service._call_gemini", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_clarification

        res = await async_client.post(
            "/api/v1/recommendations",
            json={"prompt": "dame algo pero no se que ver"}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "clarification_needed"
        assert len(data["recommendations"]) == 0
        assert len(data["clarification_suggestions"]) == 3
        assert data["provider_used"] == "gemini"

    # Test de detección temprana determinista de texto ininteligible (letras y números aleatorios)
    res_gibberish = await async_client.post(
        "/api/v1/recommendations",
        json={"prompt": "xyz123 ?????"}
    )
    assert res_gibberish.status_code == 200
    data_gib = res_gibberish.json()
    assert data_gib["status"] == "clarification_needed"
    assert len(data_gib["clarification_suggestions"]) == 4


@pytest.mark.asyncio
async def test_recommendations_filter_by_tipo(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test filtering candidates specifically by movie or tv."""
    res = await async_client.post(
        "/api/v1/recommendations",
        json={"prompt": "Quiero una serie", "tipo_filtro": "tv"}
    )
    assert res.status_code == 200
    data = res.json()
    for rec in data.get("recommendations", []):
        if rec.get("title"):
            assert rec["title"]["tipo"] == "tv"


@pytest.mark.asyncio
async def test_recommendations_only_watched(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test recommending only from watched titles when requested in prompt."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"nombre_usuario": "watcher1", "password": "password123"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mark title 1 (Interstellar) as watched
    await async_client.post("/api/v1/titles/1/watched", headers=headers)

    res = await async_client.post(
        "/api/v1/recommendations",
        json={"prompt": "Recomiéndame de las que ya vi"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "recommended"
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["title_id"] == 1


@pytest.mark.asyncio
async def test_recommendations_language_support(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test passing explicit language to recommendation endpoint."""
    with patch("app.services.ai_recommender_service.settings.GEMINI_API_KEY", ""), \
         patch("app.services.ai_recommender_service.settings.GROQ_API_KEY", ""):

        res = await async_client.post(
            "/api/v1/recommendations",
            json={"prompt": "sci-fi space travel", "language": "en"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recommended"
        assert "handpicked selection" in data["message"]
        assert len(data["recommendations"]) > 0
        assert "★" in data["recommendations"][0]["reason"]


@pytest.mark.asyncio
async def test_recommendations_with_clarification_context(
    async_client: AsyncClient,
    sample_catalog_for_recs
):
    """Test resolving a relative response using clarification_context."""
    with patch("app.services.ai_recommender_service.settings.GEMINI_API_KEY", ""), \
         patch("app.services.ai_recommender_service.settings.GROQ_API_KEY", ""):

        res = await async_client.post(
            "/api/v1/recommendations",
            json={
                "prompt": "la primera",
                "clarification_context": {
                    "previous_prompt": "asdfghjkl",
                    "assistant_message": "¿Prefieres ciencia ficción o comedia?",
                    "suggestions": [
                        "Películas de ciencia ficción y viajes espaciales",
                        "Comedias ligeras y familiares"
                    ]
                }
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "recommended"
        assert len(data["recommendations"]) > 0
        # Should recommend science fiction (Interstellar is in sample_catalog_for_recs)
        rec_ids = [r["title_id"] for r in data["recommendations"]]
        assert 1 in rec_ids


def test_relaxed_validator_legitimate_prompts():
    """Valida que prompts legítimos en español e inglés con números y consonantes complejas no sean rechazados."""
    from app.services.ai_recommender_service import is_unintelligible_prompt

    valid_prompts = [
        "Películas de atracos, robos ingeniosos y planes maestros con giros inesperados",
        "Obras fascinantes sobre bucles temporales, paradojas y viajes en el tiempo",
        "Unforgettable 80s and 90s cult classics",
        "Psychological thrillers with unpredictable twists",
        "sci-fi movies from 2024",
        "best 4k films",
        "classic horror movies",
        "quiero una pelicula divertida asdsakjdha",
        "recomiéndame algo bueno para ver hoy",
        "quiero algo de suspenso",
    ]
    for p in valid_prompts:
        assert is_unintelligible_prompt(p) is False, f"Falso positivo en prompt válido: {p}"


def test_relaxed_validator_gibberish_rejection():
    """Valida que teclado machacado extremo y secuencias sin vocales sean correctamente rechazadas."""
    from app.services.ai_recommender_service import is_unintelligible_prompt

    gibberish = [
        "asdfghjkl",
        "qwertyuiop",
        "asdf123",
        "asdasd",
        "qweqwe",
        "12345",
        "ajskdhaskjdh",
        "sdklfj",
        "bcdfghjklmnpqr",
        "z",
        "   ",
        "zzzzzzzzzzzz",
        "quiero un asdsadasdhk",
        "quiero un asdf",
        "busco asdasd",
        "dame algo asdasd",
        "recomienda qweqwe",
        "busco zxcvbnm",
    ]
    for g in gibberish:
        assert is_unintelligible_prompt(g) is True, f"Falso negativo en basura: {g}"


@pytest.mark.asyncio
async def test_recommendations_endpoint_unintelligible_prompt(async_client: AsyncClient):
    """Verifica que un prompt ininteligible corta de inmediato en el endpoint con el Validador de Entrada."""
    res = await async_client.post("/api/v1/recommendations", json={"prompt": "asdf123"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "clarification_needed"
    assert data["model_used"] == "Validador de Entrada (CineTrack Recommender Engine)"
    assert data["recommendations"] == []
    assert len(data["clarification_suggestions"]) > 0


@pytest.mark.asyncio
async def test_negative_genre_filtering(db_session: AsyncSession, sample_catalog_for_recs):
    """Verifica que el filtrado negativo (ej. 'sin drama') excluya títulos que contengan dicho género."""
    from app.services.catalog_service import get_recommendation_candidates

    # Interstellar y Dark tienen drama (id=18). Inception tiene Acción (28) y Sci-Fi (878), no drama.
    candidates, _ = await get_recommendation_candidates(
        db_session,
        prompt="ciencia ficcion pero sin drama",
        usuario_id=None
    )
    cand_ids = [c["id"] for c in candidates]
    # Inception no tiene drama, debería estar presente
    assert 2 in cand_ids
    # Interstellar y Dark tienen drama, deben haber sido filtrados por la exclusión negativa
    assert 1 not in cand_ids
    assert 3 not in cand_ids


def test_embedding_service_build_text():
    """Verifica la construcción del texto formateado para vectorización semántica."""
    from app.services.embedding_service import EmbeddingService

    text = EmbeddingService.build_title_text(
        nombre="Inception",
        tipo="movie",
        generos=["Ciencia ficción", "Acción"],
        director="Christopher Nolan",
        sinopsis="Un ladrón que roba secretos corporativos mediante sueños."
    )
    assert "Título: Inception." in text
    assert "Tipo: Película." in text
    assert "Géneros: Ciencia ficción, Acción." in text
    assert "Director: Christopher Nolan." in text
    assert "Sinopsis: Un ladrón que roba" in text


@pytest.mark.asyncio
async def test_country_origin_filtering(db_session: AsyncSession, sample_catalog_for_recs):
    """Verifica que 'peliculas de argentina' filtre estrictamente por Titulo.pais == 'AR', excluyendo obras extranjeras ambientadas allí."""
    from app.services.catalog_service import get_recommendation_candidates

    candidates, _ = await get_recommendation_candidates(
        db_session,
        prompt="peliculas de argentina",
        usuario_id=None
    )
    cand_ids = [c["id"] for c in candidates]
    # Nueve Reinas es producción argentina (AR)
    assert 4 in cand_ids
    # Happy Together es de Hong Kong (HK), debe quedar excluida por el filtro de procedencia
    assert 5 not in cand_ids
    # Verificamos que los metadatos de país e idioma estén presentes en el candidato
    ar_cand = next(c for c in candidates if c["id"] == 4)
    assert ar_cand["pais"] == "AR"
    assert ar_cand["idioma_original"] == "es"


@pytest.mark.asyncio
async def test_setting_location_allows_foreign_setting(db_session: AsyncSession, sample_catalog_for_recs):
    """Verifica que 'ambientadas en Buenos Aires' NO aplique filtro excluyente de país, permitiendo títulos extranjeros que transcurren allí."""
    from app.services.catalog_service import get_recommendation_candidates

    candidates, _ = await get_recommendation_candidates(
        db_session,
        prompt="peliculas ambientadas en buenos aires",
        usuario_id=None
    )
    cand_ids = [c["id"] for c in candidates]
    # Happy Together (HK) y Nueve Reinas (AR) ambas transcurren en Buenos Aires
    assert 4 in cand_ids or 5 in cand_ids


@pytest.mark.asyncio
async def test_language_filtering(db_session: AsyncSession, sample_catalog_for_recs):
    """Verifica que 'series en aleman' filtre estrictamente por Titulo.idioma_original == 'de'."""
    from app.services.catalog_service import get_recommendation_candidates

    candidates, _ = await get_recommendation_candidates(
        db_session,
        prompt="series en aleman",
        usuario_id=None
    )
    cand_ids = [c["id"] for c in candidates]
    # Dark es alemana (de)
    assert 3 in cand_ids
    # Interstellar e Inception son en inglés (en)
    assert 1 not in cand_ids
    assert 2 not in cand_ids



