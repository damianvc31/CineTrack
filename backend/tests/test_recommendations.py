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
        popularidad=150.0,
        vote_average_tmdb=8.5,
        vote_count_tmdb=6000,
        rating_unificado=8.5,
        status_tmdb="Ended"
    )

    db_session.add_all([m1, m2, s1])
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


