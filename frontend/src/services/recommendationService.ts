import { api } from './api'
import type { TitleCard } from '@/types/catalog'

export interface RecommendationItem {
  title_id: number
  reason: string
  title?: TitleCard | null
}

export interface RecommendationResponse {
  status: 'recommended' | 'clarification_needed'
  message: string
  recommendations: RecommendationItem[]
  clarification_suggestions: string[]
  provider_used: string
  model_used?: string
}

export interface RecommendationParams {
  prompt: string
  tipo_filtro?: 'all' | 'movie' | 'tv'
  language?: 'es' | 'en'
}

export const recommendationService = {
  getRecommendations: async (params: RecommendationParams): Promise<RecommendationResponse> => {
    return api.post<RecommendationResponse>('/recommendations', {
      prompt: params.prompt,
      tipo_filtro: params.tipo_filtro || 'all',
      language: params.language || 'es'
    })
  }
}
