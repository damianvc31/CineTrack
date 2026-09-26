import type { TitleCard, TitleDetail } from '@/types/catalog'

export const UPCOMING_STATUSES = [
  'in production',
  'planned',
  'post production',
  'upcoming',
]

/**
 * Determina si un título (película o serie) es un próximo estreno o aún no se ha estrenado.
 * Aplica para ocultar la opción de marcar como visto (el ojo) preservando Favoritos y Watchlist.
 */
export function isTitleUnreleased(title?: Partial<TitleCard | TitleDetail> | null): boolean {
  if (!title) return false

  const todayStr = new Date().toISOString().split('T')[0]
  const st = (title.status_tmdb || '').toLowerCase()
  const isUpcomingStatus = UPCOMING_STATUSES.some((status) => st.includes(status))

  // 1. Películas
  if (title.tipo === 'movie') {
    if (!title.fecha_estreno) return true
    if (title.fecha_estreno > todayStr) return true
    if (isUpcomingStatus) return true
    return false
  }

  // 2. Series (tv)
  if (!title.fecha_estreno) return true
  if (title.fecha_estreno > todayStr) return true
  if (isUpcomingStatus) return true

  // Estreno programado para hoy pero cuyo episodio aún no se emitió
  if (
    title.fecha_estreno === todayStr &&
    (!title.proximo_episodio_fecha || title.proximo_episodio_fecha >= todayStr)
  ) {
    return true
  }

  // Si tiene temporadas y episodios cargados (en TitleDetailPage)
  const detail = title as TitleDetail
  if (detail.temporadas && detail.temporadas.length > 0) {
    let totalAiredCount = 0
    for (const season of detail.temporadas) {
      for (const ep of season.episodios || []) {
        if (ep.fecha_estreno && ep.fecha_estreno <= todayStr) {
          if (
            !detail.proximo_episodio_fecha ||
            detail.proximo_episodio_fecha <= todayStr ||
            ep.fecha_estreno < detail.proximo_episodio_fecha
          ) {
            totalAiredCount++
          }
        }
      }
    }
    // Si la serie tiene temporadas/episodios pero ninguno ha sido emitido
    if (totalAiredCount === 0) return true
  }

  return false
}
