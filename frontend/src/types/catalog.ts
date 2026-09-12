export type TitleType = 'movie' | 'tv'

export interface GenreItem {
  id: number
  nombre: string
}

export interface TitleCard {
  id: number
  tmdb_id: number
  tipo: TitleType
  nombre: string
  sinopsis?: string | null
  portada_url?: string | null
  poster_url?: string | null
  fecha_estreno?: string | null
  fecha_fin?: string | null
  anio_estreno?: number | null
  anio_fin?: number | null
  duracion?: number | null
  popularidad: number
  popularidad_percentil: number
  vote_average_tmdb: number
  vote_count_tmdb: number
  rating_unificado: number
  generos: GenreItem[]
  total_seasons?: number | null
  user_favorito?: boolean
  user_estado?: string | null
  pais?: string | null
  idioma_original?: string | null
}

export interface HomeSections {
  trending: TitleCard[]
  new_releases: TitleCard[]
  classics: TitleCard[]
  top_rated: TitleCard[]
  by_genre: Record<string, TitleCard[]>
  others: TitleCard[]
}

export interface CastMember {
  actor_id: number
  tmdb_id?: number | null
  nombre: string
  personaje?: string | null
  orden: number
  foto_url?: string | null
}

export interface EpisodeItem {
  id: number
  temporada_id: number
  numero: number
  nombre: string
  fecha_estreno?: string | null
  duracion?: number | null
  visto: boolean
}

export interface SeasonItem {
  id: number
  titulo_id: number
  numero: number
  sinopsis?: string | null
  fecha_estreno?: string | null
  cantidad_episodios: number
  episodios_vistos: number
  temporada_vista: boolean
  episodios: EpisodeItem[]
}

export interface TitleDetail extends TitleCard {
  director?: string | null
  guionista?: string | null
  pais?: string | null
  idioma_original?: string | null
  status_tmdb?: string | null
  proximo_episodio_fecha?: string | null
  elenco: CastMember[]
  temporadas: SeasonItem[]
}

export interface ReviewItem {
  id: number
  titulo_id: number
  usuario_id?: number | null
  nombre_usuario?: string | null
  avatar_url?: string | null
  autor_tmdb?: string | null
  puntaje?: number | null
  texto: string
  fecha: string
}

export interface UserLibrary {
  following: TitleCard[]
  favorites: TitleCard[]
  watchlist: TitleCard[]
  recently_watched: TitleCard[]
}

export interface UserStats {
  total_hours: number
  movie_hours: number
  tv_hours: number
  movies_watched_count: number
  series_watched_count: number
  episodes_watched_count: number
  top_by_popularity: Array<{
    id: number
    nombre: string
    tipo: string
    anio_estreno?: number | null
    portada_url?: string | null
    metric_value: number
  }>
  top_by_community_rating: Array<{
    id: number
    nombre: string
    tipo: string
    anio_estreno?: number | null
    portada_url?: string | null
    metric_value: number
  }>
  top_by_user_rating: Array<{
    id: number
    nombre: string
    tipo: string
    anio_estreno?: number | null
    portada_url?: string | null
    metric_value: number
  }>
}

export interface UserReviewItem {
  id: number
  titulo_id: number
  titulo_nombre: string
  titulo_tipo: string
  titulo_portada_url?: string | null
  titulo_fecha_estreno?: string | null
  puntaje?: number | null
  texto: string
  fecha: string
}

export interface UserReviewsListResponse {
  items: UserReviewItem[]
  total: number
  page: number
  page_size: number
}

export interface UnreviewedWatchedResponse {
  items: TitleCard[]
  total: number
}

