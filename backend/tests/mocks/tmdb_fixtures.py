MOCK_MOVIE_GENRES = [
    {"id": 28, "name": "Acción"},
    {"id": 12, "name": "Aventura"},
    {"id": 878, "name": "Ciencia ficción"},
    {"id": 18, "name": "Drama"},
]

MOCK_TV_GENRES = [
    {"id": 18, "name": "Drama"},
    {"id": 80, "name": "Crimen"},
    {"id": 10765, "name": "Sci-Fi & Fantasy"},
]

MOCK_MOVIE_DETAILS = {
    "id": 157336,
    "title": "Interstellar",
    "overview": "Un grupo de científicos y exploradores viajan a través de un agujero de gusano.",
    "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
    "backdrop_path": "/rAiYTggYH3n2X2mJ07k7i0nwhZc.jpg",
    "release_date": "2014-11-05",
    "runtime": 169,
    "origin_country": ["US"],
    "popularity": 85.5,
    "vote_average": 8.4,
    "vote_count": 34000,
    "genres": [
        {"id": 12, "name": "Aventura"},
        {"id": 18, "name": "Drama"},
        {"id": 878, "name": "Ciencia ficción"},
    ],
    "credits": {
        "crew": [
            {"name": "Christopher Nolan", "job": "Director"},
            {"name": "Jonathan Nolan", "job": "Screenplay"},
            {"name": "Christopher Nolan", "job": "Writer"},
            {"name": "Kip Thorne", "job": "Story"},
            {"name": "Emma Thomas", "job": "Producer"},
        ],
        "cast": [
            {"id": 100 + i, "name": f"Actor {i}", "character": f"Personaje {i}", "profile_path": f"/p{i}.jpg", "order": i}
            for i in range(25)  # 25 actores para verificar que recorta a 15
        ],
    },
}

MOCK_SERIES_DETAILS = {
    "id": 1396,
    "name": "Breaking Bad",
    "overview": "Un profesor de química con cáncer fabrica metanfetamina con su exalumno.",
    "poster_path": "/ztkUQFLlC19CCMYHW9o1zWhJRNq.jpg",
    "backdrop_path": "/9faGSFi5jam6pDWGNd0p8J24gVM.jpg",
    "first_air_date": "2008-01-20",
    "episode_run_time": [47],
    "origin_country": ["US"],
    "popularity": 95.2,
    "vote_average": 8.9,
    "vote_count": 14500,
    "status": "Ended",
    "number_of_seasons": 1,
    "number_of_episodes": 2,
    "next_episode_to_air": None,
    "genres": [
        {"id": 18, "name": "Drama"},
        {"id": 80, "name": "Crimen"},
    ],
    "created_by": [{"id": 1, "name": "Vince Gilligan"}],
    "credits": {
        "crew": [
            {"name": "Vince Gilligan", "job": "Director"},
            {"name": "Vince Gilligan", "job": "Writer"},
        ],
        "cast": [
            {"id": 201, "name": "Bryan Cranston", "character": "Walter White", "profile_path": "/bc.jpg", "order": 0},
            {"id": 202, "name": "Aaron Paul", "character": "Jesse Pinkman", "profile_path": "/ap.jpg", "order": 1},
        ],
    },
    "seasons": [
        {
            "season_number": 0,
            "name": "Especiales",
            "episode_count": 5,
        },
        {
            "season_number": 1,
            "name": "Temporada 1",
            "overview": "Temporada inicial de Breaking Bad.",
            "poster_path": "/s1.jpg",
            "episode_count": 2,
        },
    ],
}

MOCK_SEASON_1_DETAILS = {
    "season_number": 1,
    "name": "Temporada 1",
    "overview": "Temporada inicial de Breaking Bad.",
    "poster_path": "/s1.jpg",
    "episodes": [
        {
            "episode_number": 1,
            "name": "Pilot",
            "overview": "Walter es diagnosticado.",
            "runtime": 58,
            "air_date": "2008-01-20",
        },
        {
            "episode_number": 2,
            "name": "Cat's in the Bag...",
            "overview": "Walt y Jesse lidian con el cuerpo.",
            "runtime": 48,
            "air_date": "2008-01-27",
        },
    ],
}

MOCK_REVIEWS_DATA = {
    "page": 1,
    "results": [
        {
            "id": f"rev_{i}",
            "author": f"Reviewer {i}",
            "author_details": {"rating": 8.0 + (i % 3)},
            "content": f"Esta es una crítica detallada {i} sobre la producción.",
            "created_at": "2023-01-15T12:00:00.000Z",
        }
        for i in range(25)  # 25 reviews para probar que corta en 20
    ],
    "total_pages": 1,
    "total_results": 25,
}

