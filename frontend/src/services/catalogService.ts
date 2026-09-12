import { api } from './api'
import type { HomeSections, TitleCard, TitleDetail, ReviewItem, UserLibrary, UserStats } from '@/types/catalog'

export interface TitleFilters {
  section?: 'new_releases' | 'trending' | 'classics' | 'top_rated' | 'others'
  tipo?: 'movie' | 'tv'
  genero?: string
  genero_id?: number
  actor?: string
  actor_id?: number
  q?: string
  sort_by?: 'popularity' | 'rating' | 'release_date' | 'title'
  order?: 'desc' | 'asc'
  page?: number
  page_size?: number
}

export interface TitlesResponse {
  items: TitleCard[]
  total: number
  page: number
  page_size: number
}

export const catalogService = {
  getHome: (filters?: { tipo?: 'movie' | 'tv' }) =>
    api.get<HomeSections>('/home', filters as Record<string, string | number | boolean>),

  getTitles: (filters: TitleFilters = {}) =>
    api.get<TitlesResponse>('/titles', filters as Record<string, string | number | boolean>),

  getTitleDetail: (id: number) => api.get<TitleDetail>(`/titles/${id}`),

  getGenres: () => api.get<Array<{ id: number; nombre: string }>>('/genres'),

  getReviews: (titleId: number, page: number = 1) =>
    api.get<{ items: ReviewItem[]; total: number }>(`/titles/${titleId}/reviews`, { page }),

  addReview: (titleId: number, texto: string, puntaje?: number) =>
    api.post<ReviewItem>(`/titles/${titleId}/reviews`, { texto, puntaje }),

  toggleFavorite: (titleId: number) =>
    api.post<{ favorito: boolean; timestamp: string }>(`/titles/${titleId}/favorite`),

  toggleWatchlist: (titleId: number) =>
    api.post<{ titulo_id: number; nuevo_estado: string | null; mensaje: string }>(
      `/titles/${titleId}/watchlist`
    ),

  toggleWatched: (titleId: number) =>
    api.post<{ titulo_id: number; nuevo_estado: string | null; mensaje: string }>(
      `/titles/${titleId}/watched`
    ),

  toggleEpisodeWatch: (titleId: number, seasonNum: number, episodeNum: number) =>
    api.post<{ episodio_id: number; visto: boolean; nuevo_estado_serie: string | null }>(
      `/titles/${titleId}/seasons/${seasonNum}/episodes/${episodeNum}/watch`
    ),

  toggleSeasonWatch: (titleId: number, seasonNum: number) =>
    api.post<{ temporada_vista: boolean; nuevo_estado_serie: string | null }>(
      `/titles/${titleId}/seasons/${seasonNum}/watch`
    ),

  unfollowSeries: (titleId: number) =>
    api.post<{ nuevo_estado: string | null; mensaje: string }>(`/titles/${titleId}/unfollow`),

  getUserState: (titleId: number) =>
    api.get<{
      titulo_id: number
      tipo: string
      favorito: boolean
      estado: string | null
      total_episodios: number
      episodios_vistos: number
      porcentaje_progreso: number
    }>(`/titles/${titleId}/user-state`),

  getLibrary: () => api.get<UserLibrary>('/users/me/library'),

  getStats: () => api.get<UserStats>('/users/me/stats'),
}
