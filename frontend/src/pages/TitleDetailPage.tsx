import React, { useEffect, useState, useCallback } from 'react'
import { useParams, Link, useOutletContext } from 'react-router-dom'
import {
  Star,
  Heart,
  Bookmark,
  Eye,
  Play,
  X,
  Clock,
  Tv,
  AlertCircle,
  Calendar,
  MessageSquare,
  Send,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Pencil,
  Trash2,
  Minus,
  Plus,
  Users,
} from 'lucide-react'
import { catalogService } from '@/services/catalogService'
import type { TitleDetail, ReviewItem, SeasonItem } from '@/types/catalog'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import posterFallback from '@/assets/placeholders/poster-empty.svg'
import { CountryFlag } from '@/components/common/CountryFlag'
import { getLanguageName } from '@/utils/countryUtils'

interface OutletContextType {
  openAuth: (mode?: 'login' | 'register') => void
}

export const TitleDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { language, translateGenreName } = useLanguage()
  const { openAuth } = useOutletContext<OutletContextType>()

  const [title, setTitle] = useState<TitleDetail | null>(null)
  const [reviews, setReviews] = useState<ReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Estado de interacción de usuario
  const [isFavorite, setIsFavorite] = useState(false)
  const [userEstado, setUserEstado] = useState<string | null>(null)
  const [selectedSeason, setSelectedSeason] = useState<number>(1)
  const [episodesCollapsed, setEpisodesCollapsed] = useState(false)
  const [seasonWatchLoading, setSeasonWatchLoading] = useState(false)
  const [episodeNotice, setEpisodeNotice] = useState<string | null>(null)

  // Scroll to top automatically when navigating to any title detail
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [id])

  // Estado de Reseñas
  const [reviewText, setReviewText] = useState('')
  const [reviewScore, setReviewScore] = useState<number>(8.0)
  const [includeScore, setIncludeScore] = useState<boolean>(true)
  const [isEditingReview, setIsEditingReview] = useState(false)
  const [submittingReview, setSubmittingReview] = useState(false)
  const [deletingReview, setDeletingReview] = useState(false)
  const [reviewSuccess, setReviewSuccess] = useState(false)
  const [reviewPage, setReviewPage] = useState(1)
  const [hasMoreReviews, setHasMoreReviews] = useState(false)
  const [loadingMoreReviews, setLoadingMoreReviews] = useState(false)

  const titleId = parseInt(id || '0', 10)

  const loadData = useCallback(async (showSpinner = true) => {
    if (!titleId) return
    if (showSpinner) setLoading(true)
    setError(null)
    try {
      const [titleRes, reviewsRes] = await Promise.all([
        catalogService.getTitleDetail(titleId),
        catalogService.getReviews(titleId, 1, 20).catch(() => [] as ReviewItem[]),
      ])
      setTitle(titleRes)
      setIsFavorite(titleRes.user_favorito ?? false)
      setUserEstado(titleRes.user_estado ?? null)
      const list = Array.isArray(reviewsRes) ? reviewsRes : (reviewsRes as any).items || []
      setReviews(list)
      setReviewPage(1)
      setHasMoreReviews(list.length >= 20)

      if (titleRes.tipo === 'tv' && titleRes.temporadas && titleRes.temporadas.length > 0) {
        const visible = titleRes.temporadas.filter(
          (t) => (t.episodios && t.episodios.length > 0) || t.fecha_estreno
        )
        if (visible.length > 0) {
          setSelectedSeason((prev) => {
            const exists = visible.some((t) => t.numero === prev)
            return exists ? prev : visible[0].numero
          })
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Failed to load title information.')
      }
    } finally {
      if (showSpinner) setLoading(false)
    }
  }, [titleId])

  useEffect(() => {
    loadData(true)
  }, [loadData])

  const handleFavoriteToggle = async () => {
    if (!user) {
      openAuth()
      return
    }
    try {
      const res = await catalogService.toggleFavorite(titleId)
      setIsFavorite(res.favorito)
    } catch (err) {
      console.error('Error toggling favorite:', err)
    }
  }

  const handleWatchlistToggle = async () => {
    if (!user) {
      openAuth()
      return
    }
    try {
      const res = await catalogService.toggleWatchlist(titleId)
      setUserEstado(res.nuevo_estado ?? null)
    } catch (err) {
      console.error('Error toggling watchlist:', err)
    }
  }

  const handleWatchedToggle = async () => {
    if (!user) {
      openAuth()
      return
    }
    try {
      const res = await catalogService.toggleWatched(titleId)
      setUserEstado(res.nuevo_estado ?? null)
      loadData(false)
    } catch (err) {
      console.error('Error toggling watched:', err)
    }
  }

  const handleUnfollow = async () => {
    if (!user) {
      openAuth()
      return
    }
    try {
      const res = await catalogService.unfollowSeries(titleId)
      setUserEstado(res.nuevo_estado ?? null)
      loadData(false)
    } catch (err) {
      console.error('Error dropping series:', err)
    }
  }

  const handleFollow = async () => {
    if (!user) {
      openAuth()
      return
    }
    try {
      const res = await catalogService.followSeries(titleId)
      setUserEstado(res.nuevo_estado ?? 'siguiendo')
      loadData(false)
    } catch (err) {
      console.error('Error resuming series:', err)
    }
  }

  const handleEpisodeToggle = async (
    seasonNum: number,
    episodeNum: number,
    isUnreleased: boolean,
    isWatched: boolean
  ) => {
    if (!user) {
      openAuth()
      return
    }
    if (isUnreleased && !isWatched) {
      setEpisodeNotice(`Episode E${episodeNum} has not aired yet. Only aired episodes can be marked.`)
      setTimeout(() => setEpisodeNotice(null), 4500)
      return
    }
    try {
      const res = await catalogService.toggleEpisodeWatch(titleId, seasonNum, episodeNum)
      if (res.nuevo_estado_serie !== undefined) {
        setUserEstado(res.nuevo_estado_serie)
      }
      loadData(false)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setEpisodeNotice(err.message)
      } else {
        setEpisodeNotice('Failed to update episode.')
      }
      setTimeout(() => setEpisodeNotice(null), 4500)
    }
  }

  const handleToggleSeasonWatched = async (seasonNum: number) => {
    if (!user) {
      openAuth()
      return
    }
    setSeasonWatchLoading(true)
    try {
      const res = await catalogService.toggleSeasonWatch(titleId, seasonNum)
      if (res.nuevo_estado_serie !== undefined) {
        setUserEstado(res.nuevo_estado_serie)
      }
      loadData(false)
    } catch (err) {
      console.error('Error marcando temporada completa:', err)
    } finally {
      setSeasonWatchLoading(false)
    }
  }

  const handleStartEdit = (rev: ReviewItem) => {
    setIsEditingReview(true)
    setReviewText(rev.texto)
    if (rev.puntaje !== null && rev.puntaje !== undefined) {
      setIncludeScore(true)
      setReviewScore(rev.puntaje)
    } else {
      setIncludeScore(false)
      setReviewScore(8.0)
    }
  }

  const handleCancelEdit = () => {
    setIsEditingReview(false)
    setReviewText('')
    setReviewScore(8.0)
    setIncludeScore(true)
  }

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) {
      openAuth()
      return
    }
    if (!reviewText.trim()) return

    setSubmittingReview(true)
    try {
      const finalScore = includeScore ? Math.round(reviewScore * 2) / 2 : null
      const saved = await catalogService.addReview(titleId, reviewText.trim(), finalScore)
      setReviews((prev) => {
        const idx = prev.findIndex((r) => r.usuario_id === user.id)
        if (idx >= 0) {
          const updated = [...prev]
          updated[idx] = saved
          return updated
        }
        return [saved, ...prev]
      })
      setIsEditingReview(false)
      setReviewText('')
      setReviewSuccess(true)
      setTimeout(() => setReviewSuccess(false), 4000)

      // Actualizar información del título para reflejar rating_unificado recalculado
      const updatedTitle = await catalogService.getTitleDetail(titleId)
      setTitle(updatedTitle)
    } catch (err) {
      console.error('Error guardando reseña:', err)
    } finally {
      setSubmittingReview(false)
    }
  }

  const handleDeleteReview = async () => {
    if (!user) return
    if (!window.confirm(language === 'es' ? '¿Estás seguro de que deseas eliminar tu reseña?' : 'Are you sure you want to delete your review?')) {
      return
    }
    setDeletingReview(true)
    try {
      await catalogService.deleteReview(titleId)
      setReviews((prev) => prev.filter((r) => r.usuario_id !== user.id))
      setIsEditingReview(false)
      setReviewText('')

      // Actualizar información del título para reflejar rating_unificado recalculado
      const updatedTitle = await catalogService.getTitleDetail(titleId)
      setTitle(updatedTitle)
    } catch (err) {
      console.error('Error deleting review:', err)
    } finally {
      setDeletingReview(false)
    }
  }

  const handleLoadMoreReviews = async () => {
    if (loadingMoreReviews || !hasMoreReviews) return
    setLoadingMoreReviews(true)
    try {
      const nextPage = reviewPage + 1
      const more = await catalogService.getReviews(titleId, nextPage, 20)
      const moreList = Array.isArray(more) ? more : (more as any).items || []
      if (moreList.length > 0) {
        setReviews((prev) => [...prev, ...moreList])
        setReviewPage(nextPage)
        setHasMoreReviews(moreList.length >= 20)
      } else {
        setHasMoreReviews(false)
      }
    } catch (err) {
      console.error('Error loading more reviews:', err)
    } finally {
      setLoadingMoreReviews(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3">
        <div className="w-12 h-12 border-4 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
        <p className="text-xs text-gray-400">
          {language === 'es' ? 'Cargando detalles del título...' : 'Loading title details...'}
        </p>
      </div>
    )
  }

  if (error || !title) {
    return (
      <div className="max-w-md mx-auto my-20 p-6 bg-[#141414] border border-[#262626] rounded-2xl text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-white mb-2">
          {language === 'es' ? 'Título No Encontrado' : 'Title Not Found'}
        </h3>
        <p className="text-xs text-gray-400 mb-6">
          {error || (language === 'es' ? 'El título solicitado no existe o fue eliminado.' : 'The requested title does not exist or was removed.')}
        </p>
        <Link
          to="/"
          className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md transition-all"
        >
          {language === 'es' ? 'Volver al Inicio' : 'Back to Home'}
        </Link>
      </div>
    )
  }

  // Temporadas visibles en el selector y lista de episodios:
  // Solo se muestran temporadas con episodios cargados o con fecha de estreno confirmada.
  // Temporadas confirmadas sin fecha ni episodios (ej. Landman S3) solo informan el badge superior.
  const visibleSeasons: SeasonItem[] =
    title.tipo === 'tv' && title.temporadas
      ? title.temporadas.filter(
          (s) => (s.episodios && s.episodios.length > 0) || s.fecha_estreno
        )
      : []

  const currentSeasonData: SeasonItem | undefined =
    visibleSeasons.find((s) => s.numero === selectedSeason) || visibleSeasons[0]

  // Portada e imagen
  const portada = title.portada_url || title.poster_url || posterFallback
  const percentilNum =
    title.popularidad_percentil > 1
      ? Math.round(title.popularidad_percentil)
      : Math.round(title.popularidad_percentil * 100)

  // Formato para series y películas
  const startYear = title.anio_estreno || (title.fecha_estreno ? title.fecha_estreno.substring(0, 4) : '')
  const endYear = title.anio_fin || (title.fecha_fin ? title.fecha_fin.substring(0, 4) : '')
  const yearRange = endYear ? `${startYear}-${endYear}` : `${startYear}-`
  const seasonsCount = visibleSeasons.length || 1
  const seasonsLabel = `${seasonsCount} ${language === 'es' ? (seasonsCount === 1 ? 'temporada' : 'temporadas') : (seasonsCount === 1 ? 'season' : 'seasons')}`

  // Render semantic series status badge based on season progress and TMDB status
  const renderStatusBadge = () => {
    if (title.tipo !== 'tv' || !title.status_tmdb) return null
    const st = title.status_tmdb.toLowerCase()

    if (st.includes('ended') || st.includes('finaliz')) {
      return (
        <span className="px-3 py-1 rounded-full bg-gray-800/90 border border-gray-600 text-gray-300 text-xs font-semibold">
          {language === 'es' ? 'Finalizada' : 'Ended'}
        </span>
      )
    }

    if (st.includes('cancel')) {
      return (
        <span className="px-3 py-1 rounded-full bg-red-950/80 border border-red-600/70 text-red-300 text-xs font-bold">
          {language === 'es' ? 'Cancelada' : 'Canceled'}
        </span>
      )
    }

    const todayStr = new Date().toISOString().split('T')[0]

    // 1. Detect if a season is actively in progress:
    // (has at least 1 aired episode AND at least 1 unreleased/future episode)
    let inProgressSeason: { seasonNum: number; nextEpDate?: string } | null = null
    // 2. Future season with a scheduled air date
    let upcomingSeasonWithDate: { seasonNum: number; startDate: string } | null = null
    // 3. Confirmed future season WITHOUT scheduled date (dateless, like Landman Season 3)
    let confirmedSeasonDateless: { seasonNum: number } | null = null

    if (title.temporadas && title.temporadas.length > 0) {
      const sortedSeasons = [...title.temporadas].sort((a, b) => a.numero - b.numero)

      for (const season of sortedSeasons) {
        const eps = season.episodios || []
        const airedEpisodes = eps.filter(
          (ep) => ep.fecha_estreno && ep.fecha_estreno <= todayStr
        )
        const unreleasedEpisodes = eps
          .filter((ep) => ep.fecha_estreno && ep.fecha_estreno > todayStr)
          .sort((a, b) => (a.fecha_estreno! > b.fecha_estreno! ? 1 : -1))

        if (airedEpisodes.length > 0 && unreleasedEpisodes.length > 0) {
          inProgressSeason = {
            seasonNum: season.numero,
            nextEpDate: unreleasedEpisodes[0]?.fecha_estreno || title.proximo_episodio_fecha || undefined,
          }
          break
        }

        // Check if this season is entirely in the future (not started yet)
        if (airedEpisodes.length === 0) {
          if (unreleasedEpisodes.length > 0) {
            if (!upcomingSeasonWithDate) {
              upcomingSeasonWithDate = {
                seasonNum: season.numero,
                startDate: unreleasedEpisodes[0]!.fecha_estreno!,
              }
            }
          } else if (season.fecha_estreno) {
            if (!upcomingSeasonWithDate) {
              upcomingSeasonWithDate = {
                seasonNum: season.numero,
                startDate: season.fecha_estreno,
              }
            }
          } else {
            // Season confirmed without episodes or air_date yet (e.g. Landman S3)
            if (!confirmedSeasonDateless) {
              confirmedSeasonDateless = {
                seasonNum: season.numero,
              }
            }
          }
        }
      }
    }

    // Next scheduled date from TMDB if available
    const nextDate = title.proximo_episodio_fecha

    // State 1: Active season in progress -> Currently Airing (Green pulse)
    if (inProgressSeason) {
      const nextDateStr = inProgressSeason.nextEpDate
        ? (language === 'es' ? ` — Próximo ep. el ${inProgressSeason.nextEpDate}` : ` — Next ep on ${inProgressSeason.nextEpDate}`)
        : ''
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 text-xs font-bold shadow-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>{language === 'es' ? 'En Emisión' : 'Currently Airing'}{nextDateStr}</span>
        </span>
      )
    }

    // State 2: A new season is scheduled in the calendar with a known/estimated date -> Renewed (Blue)
    if (upcomingSeasonWithDate || nextDate) {
      const dateStr = upcomingSeasonWithDate?.startDate || nextDate
      const label = upcomingSeasonWithDate
        ? (language === 'es' ? `Temporada ${upcomingSeasonWithDate.seasonNum}` : `Season ${upcomingSeasonWithDate.seasonNum}`)
        : (language === 'es' ? 'Nueva Temporada' : 'New Season')
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-950/80 border border-blue-500/60 text-blue-300 text-xs font-bold shadow-sm">
          <span className="w-2 h-2 rounded-full bg-blue-400" />
          <span>{language === 'es' ? 'Renovada' : 'Renewed'} — {label}{dateStr ? (language === 'es' ? ` el ${dateStr}` : ` on ${dateStr}`) : ''}</span>
        </span>
      )
    }

    // State 3: Confirmed renewal without a release date yet, or TMDB status In Production / Planned -> Renewed TBA (Purple/Violet)
    if (confirmedSeasonDateless || st.includes('production') || st.includes('planned')) {
      const label = confirmedSeasonDateless
        ? (language === 'es' ? `Temporada ${confirmedSeasonDateless.seasonNum}` : `Season ${confirmedSeasonDateless.seasonNum}`)
        : (language === 'es' ? 'Próxima Temporada' : 'Next Season')
      const statusSuffix = st.includes('production')
        ? (language === 'es' ? 'En Producción' : 'In Production')
        : (language === 'es' ? 'Por anunciar' : 'TBA')
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-950/80 border border-purple-500/60 text-purple-300 text-xs font-bold shadow-sm">
          <span className="w-2 h-2 rounded-full bg-purple-400" />
          <span>{language === 'es' ? 'Renovada' : 'Renewed'} — {label} ({statusSuffix})</span>
        </span>
      )
    }

    // State 4: Season concluded, active show without scheduled future seasons -> Pending Renewal (Amber)
    return (
      <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-600/50 text-amber-300 text-xs font-semibold">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        <span>{language === 'es' ? 'Pendiente de Renovación (Entre Temporadas)' : 'Pending Renewal (Between Seasons)'}</span>
      </span>
    )
  }

  return (
    <div className="pb-16">
      {/* Encabezado y Portada */}
      <div className="relative w-full overflow-hidden bg-gray-950 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 relative z-10">
          <div className="flex flex-col md:flex-row gap-8 items-start">
            {/* Poster Principal */}
            <div className="shrink-0 w-52 sm:w-64 aspect-[2/3] rounded-2xl overflow-hidden shadow-2xl border border-gray-700/60 bg-gray-900 mx-auto md:mx-0">
              <img src={portada} alt={title.nombre} className="w-full h-full object-cover" />
            </div>

            {/* Metadatos e Información */}
            <div className="flex-1 space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 font-semibold uppercase text-[10px] tracking-wider">
                  {title.tipo === 'movie' ? (language === 'es' ? 'Película' : 'Movie') : (language === 'es' ? 'Serie' : 'TV Series')}
                </span>

                {percentilNum > 0 && (
                  <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 font-bold text-xs">
                    <span>🔥</span> {percentilNum}% {language === 'es' ? 'Popularidad' : 'Popularity'}
                  </span>
                )}

                {/* Badge de estado de emisión */}
                {renderStatusBadge()}
              </div>

              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
                {title.nombre}
              </h1>

              {/* Fila con rating, formato de año/temporadas */}
              <div className="flex flex-wrap items-center gap-4 text-xs sm:text-sm text-gray-300">
                <div className="flex items-center gap-1.5 text-amber-400 font-bold bg-amber-400/10 px-2.5 py-1 rounded-lg border border-amber-400/20">
                  <Star className="w-4 h-4 fill-amber-400" />
                  <span>{title.vote_average_tmdb.toFixed(1)}</span>
                  <span className="text-[11px] text-gray-400 font-normal">
                    ({title.vote_count_tmdb} {language === 'es' ? 'votos' : 'votes'})
                  </span>
                </div>

                {title.tipo === 'tv' ? (
                  <div className="flex items-center gap-2 text-gray-300 font-medium">
                    <Tv className="w-4 h-4 text-amber-400" />
                    <span>
                      {seasonsLabel} · {yearRange}
                    </span>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-1 text-gray-400">
                      <Calendar className="w-4 h-4" />
                      <span>{title.fecha_estreno || '-'}</span>
                    </div>
                    <div className="flex items-center gap-1 text-gray-400">
                      <Clock className="w-4 h-4" />
                      <span>{title.duracion && title.duracion > 0 ? `${title.duracion} min` : '-'}</span>
                    </div>
                  </>
                )}
              </div>

              {/* Ficha técnica: Director / Creador, Guionista, País, Idioma Original */}
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-gray-400 pt-1">
                <div>
                  <span className="text-gray-500 font-medium">
                    {title.tipo === 'movie' ? (language === 'es' ? 'Director:' : 'Director:') : (language === 'es' ? 'Creador:' : 'Creator:')}
                  </span>{' '}
                  <strong className="text-gray-200">{title.director || '-'}</strong>
                </div>

                <div>
                  <span className="text-gray-500 font-medium">
                    {language === 'es' ? 'Guionista:' : 'Writer:'}
                  </span>{' '}
                  <strong className="text-gray-200">{title.guionista || '-'}</strong>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-gray-500 font-medium">
                    {language === 'es' ? 'País:' : 'Country:'}
                  </span>{' '}
                  <CountryFlag code={title.pais} showName={true} />
                </div>

                <div>
                  <span className="text-gray-500 font-medium">
                    {language === 'es' ? 'Idioma original:' : 'Original Language:'}
                  </span>{' '}
                  <span className="text-gray-300 font-medium">
                    {getLanguageName(title.idioma_original)}
                  </span>
                </div>
              </div>

              {/* Géneros */}
              {title.generos && title.generos.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {title.generos.map((g) => {
                    const gName = typeof g === 'string' ? g : g.nombre
                    return (
                      <Link
                        key={gName}
                        to={`/catalog?genero=${encodeURIComponent(gName)}`}
                        className="px-2.5 py-1 rounded-md bg-gray-800/80 hover:bg-gray-700/80 border border-gray-700/60 text-xs text-gray-300 transition-colors"
                      >
                        {translateGenreName(gName)}
                      </Link>
                    )
                  })}
                </div>
              )}

              {/* 4 Action Icons */}
              <div className="pt-4 border-t border-gray-800 flex flex-wrap items-center gap-3">
                {/* 1. Favorite button */}
                <button
                  onClick={handleFavoriteToggle}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                    isFavorite
                      ? 'bg-rose-900/40 border-rose-500 text-rose-300 shadow-md'
                      : 'bg-gray-900 border-gray-700 text-gray-300 hover:bg-rose-950/30 hover:border-rose-500/40 hover:text-rose-300'
                  }`}
                >
                  <Heart className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
                  <span>{language === 'es' ? 'Favorito' : 'Favorite'}</span>
                </button>

                {/* 2. Watched button */}
                <button
                  onClick={handleWatchedToggle}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                    userEstado === 'vista'
                      ? 'bg-emerald-900/40 border-emerald-500 text-emerald-300 shadow-md'
                      : 'bg-gray-900 border-gray-700 text-gray-300 hover:bg-emerald-950/30 hover:border-emerald-500/40 hover:text-emerald-300'
                  }`}
                >
                  <Eye className="w-4 h-4" />
                  <span>
                    {userEstado === 'vista'
                      ? (language === 'es' ? 'Vista' : 'Watched')
                      : (language === 'es' ? 'Marcar Vista' : 'Mark Watched')}
                  </span>
                </button>

                {/* 3 & 4. Series Logic: Following / Drop Series vs Watchlist */}
                {title.tipo === 'tv' ? (
                  (() => {
                    const hasWatchedEpisodes = !!title.temporadas?.some((t) => t.episodios?.some((e) => e.visto))
                    const isAbandoned = userEstado !== 'siguiendo' && userEstado !== 'vista' && hasWatchedEpisodes

                    return (
                      <>
                        {userEstado === 'siguiendo' && (
                          <>
                            {/* Following Badge */}
                            <span className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-blue-900/40 border border-blue-500 text-blue-300 cursor-default shadow-md">
                              <Play className="w-4 h-4 fill-current" />
                              <span>{language === 'es' ? 'Siguiendo' : 'Following'}</span>
                            </span>

                            {/* Drop Series Button */}
                            <button
                              onClick={handleUnfollow}
                              title={language === 'es' ? 'Abandonar serie manteniendo historial de episodios vistos' : 'Drop series keeping watched episodes history'}
                              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-red-950/40 border border-red-700/80 text-red-300 hover:bg-red-900/50 hover:border-red-500 transition-all"
                            >
                              <X className="w-4 h-4" />
                              <span>{language === 'es' ? 'Abandonar Serie' : 'Drop Series'}</span>
                            </button>
                          </>
                        )}

                        {isAbandoned && (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-red-950/40 border border-red-800/60 text-red-300">
                              <X className="w-4 h-4 text-red-400" />
                              <span>{language === 'es' ? 'Serie Abandonada' : 'Dropped Series'}</span>
                            </span>

                            <button
                              onClick={handleFollow}
                              title={language === 'es' ? 'Reanudar seguimiento de la serie' : 'Resume following series'}
                              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-blue-600/20 hover:bg-blue-600/40 border border-blue-500/50 text-blue-300 hover:text-white shadow-md transition-all"
                            >
                              <Play className="w-4 h-4 fill-current text-blue-400" />
                              <span>{language === 'es' ? 'Reanudar / Seguir' : 'Resume / Follow'}</span>
                            </button>
                          </div>
                        )}

                        {/* Watchlist button if not following, watched or dropped */}
                        {userEstado !== 'siguiendo' && userEstado !== 'vista' && !isAbandoned && (
                          <button
                            onClick={handleWatchlistToggle}
                            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                              userEstado === 'watchlist'
                                ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-md'
                                : 'bg-[#141414] border-[#262626] text-gray-300 hover:bg-amber-500/10 hover:border-amber-500/40 hover:text-amber-300'
                            }`}
                          >
                            <Bookmark className={`w-4 h-4 ${userEstado === 'watchlist' ? 'fill-current' : ''}`} />
                            <span>{language === 'es' ? 'Lista de seguimiento' : 'Watchlist'}</span>
                          </button>
                        )}
                      </>
                    )
                  })()
                ) : (
                  /* Movies: Watchlist if not watched */
                  userEstado !== 'vista' && (
                    <button
                      onClick={handleWatchlistToggle}
                      className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                        userEstado === 'watchlist'
                          ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-md'
                          : 'bg-[#141414] border-[#262626] text-gray-300 hover:bg-amber-500/10 hover:border-amber-500/40 hover:text-amber-300'
                      }`}
                    >
                      <Bookmark className={`w-4 h-4 ${userEstado === 'watchlist' ? 'fill-current' : ''}`} />
                      <span>{language === 'es' ? 'Lista de seguimiento' : 'Watchlist'}</span>
                    </button>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
        {/* Synopsis */}
        {title.sinopsis && (
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">
              {language === 'es' ? 'Sinopsis' : 'Synopsis'}
            </h2>
            <p className="text-sm sm:text-base text-gray-300 leading-relaxed max-w-4xl">
              {title.sinopsis}
            </p>
          </section>
        )}

        {/* Sección de Reparto Principal / Top Cast (arriba de temporadas en series) */}
        {title.elenco && title.elenco.length > 0 && (
          <section className="space-y-4 pt-6 border-t border-gray-800">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <Users className="w-5 h-5 text-amber-400" />{' '}
                {language === 'es' ? 'Reparto Principal' : 'Top Cast'}
              </h2>
              <span className="text-xs text-gray-400">
                {title.elenco.length} {language === 'es' ? 'actores' : 'actors'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 sm:gap-4">
              {title.elenco.slice(0, 12).map((actor) => (
                <Link
                  key={`${actor.actor_id}-${actor.orden}`}
                  to={`/catalog?actor=${encodeURIComponent(actor.nombre)}`}
                  className="p-3 rounded-2xl bg-[#141414] border border-[#262626] hover:border-amber-500/40 transition-all flex flex-col items-center text-center space-y-2.5 group shadow-sm block"
                >
                  {/* Foto de perfil del actor con fallback */}
                  <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-[#2b2b2b] group-hover:border-amber-500/50 bg-[#1c1c1c] flex items-center justify-center shrink-0 shadow-md transition-all">
                    {actor.foto_url ? (
                      <img
                        src={actor.foto_url}
                        alt={actor.nombre}
                        loading="lazy"
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          ;(e.target as HTMLElement).style.display = 'none'
                        }}
                      />
                    ) : (
                      <span className="text-xl font-black text-gray-500 group-hover:text-amber-400 transition-colors">
                        {actor.nombre.charAt(0)}
                      </span>
                    )}
                  </div>

                  <div className="min-w-0 w-full space-y-0.5">
                    <h4
                      className="text-xs font-bold text-white group-hover:text-amber-400 transition-colors truncate"
                    >
                      {actor.nombre}
                    </h4>
                    {actor.personaje && (
                      <p
                        className="text-[11px] text-gray-400 truncate"
                      >
                        {actor.personaje}
                      </p>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Acordeón y Gestión de Temporadas / Episodios (Solo Series) */}
        {title.tipo === 'tv' && visibleSeasons.length > 0 && (
          <section className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <Tv className="w-5 h-5 text-amber-400" />{' '}
                {language === 'es' ? 'Temporadas y Episodios' : 'Seasons & Episodes'}
              </h2>

              {/* Selector de Temporadas Híbrido: Tabs si <= 5 temporadas, Combobox con stepper si > 5 */}
              {visibleSeasons.length <= 5 ? (
                <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
                  {visibleSeasons.map((t) => {
                    const isActive = t.numero === selectedSeason
                    return (
                      <button
                        key={t.id}
                        onClick={() => setSelectedSeason(t.numero)}
                        className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                          isActive
                            ? 'bg-amber-500 text-black font-bold shadow-md'
                            : 'bg-[#141414] text-gray-400 hover:text-white hover:bg-[#202020] border border-[#262626]'
                        }`}
                      >
                        <span>{language === 'es' ? `Temporada ${t.numero}` : `Season ${t.numero}`}</span>
                        {t.temporada_vista && (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-500 text-black uppercase font-extrabold">
                            {language === 'es' ? 'VISTA' : 'WATCHED'}
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="relative flex items-center">
                    <select
                      value={selectedSeason}
                      onChange={(e) => setSelectedSeason(Number(e.target.value))}
                      className="appearance-none pl-3.5 pr-8 py-2 rounded-xl bg-[#141414] border border-[#262626] text-xs font-bold text-white hover:border-amber-500 focus:outline-none focus:border-amber-500 transition-colors cursor-pointer shadow-sm"
                    >
                      {visibleSeasons.map((t) => (
                        <option key={t.id} value={t.numero} className="bg-[#141414] text-white">
                          {language === 'es' ? `Temporada ${t.numero}` : `Season ${t.numero}`}{' '}
                          {t.temporada_vista
                            ? (language === 'es' ? '— ✓ VISTA' : '— ✓ WATCHED')
                            : `(${t.episodios_vistos || 0}/${t.cantidad_episodios})`}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="w-4 h-4 text-gray-400 absolute right-2.5 pointer-events-none" />
                  </div>

                  {/* Previous / next season quick nav buttons */}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => {
                        const seasons = visibleSeasons.map((t) => t.numero)
                        const currIdx = seasons.indexOf(selectedSeason)
                        if (currIdx > 0) setSelectedSeason(seasons[currIdx - 1])
                      }}
                      disabled={selectedSeason === visibleSeasons[0]?.numero}
                      title={language === 'es' ? 'Temporada anterior' : 'Previous season'}
                      className="p-2 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        const seasons = visibleSeasons.map((t) => t.numero)
                        const currIdx = seasons.indexOf(selectedSeason)
                        if (currIdx < seasons.length - 1) setSelectedSeason(seasons[currIdx + 1])
                      }}
                      disabled={selectedSeason === visibleSeasons[visibleSeasons.length - 1]?.numero}
                      title={language === 'es' ? 'Temporada siguiente' : 'Next season'}
                      className="p-2 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Notice banner */}
            {episodeNotice && (
              <div className="p-3.5 rounded-xl bg-amber-950/60 border border-amber-600/60 text-amber-200 text-xs flex items-center gap-2.5 animate-fadeIn shadow-lg">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>{episodeNotice}</span>
              </div>
            )}

            {/* Header and mark season watched button */}
            {currentSeasonData && (
              <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {language === 'es' ? `Temporada ${currentSeasonData.numero}` : `Season ${currentSeasonData.numero}`} ({currentSeasonData.cantidad_episodios} {language === 'es' ? 'episodios' : 'episodes'})
                  </h3>
                  {currentSeasonData.sinopsis && (
                    <p className="text-xs text-gray-400 mt-1 max-w-3xl leading-relaxed">
                      {currentSeasonData.sinopsis}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  <button
                    type="button"
                    onClick={() => setEpisodesCollapsed(!episodesCollapsed)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#141414] hover:bg-[#202020] text-gray-300 hover:text-white border border-[#262626] transition-colors"
                    title={episodesCollapsed ? (language === 'es' ? 'Mostrar episodios' : 'Expand episodes') : (language === 'es' ? 'Ocultar episodios' : 'Collapse episodes')}
                  >
                    {episodesCollapsed ? (
                      <>
                        <ChevronDown className="w-4 h-4 text-amber-400" />
                        <span>{language === 'es' ? 'Mostrar Episodios' : 'Show Episodes'}</span>
                      </>
                    ) : (
                      <>
                        <ChevronUp className="w-4 h-4 text-amber-400" />
                        <span>{language === 'es' ? 'Ocultar Episodios' : 'Hide Episodes'}</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => handleToggleSeasonWatched(currentSeasonData.numero)}
                    disabled={seasonWatchLoading}
                    className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                      currentSeasonData.temporada_vista
                        ? 'bg-emerald-950/80 border-emerald-500/70 text-emerald-300'
                        : 'bg-gray-800/80 border-gray-700 text-gray-300 hover:bg-emerald-950/40 hover:border-emerald-600 hover:text-emerald-300'
                    }`}
                  >
                    <CheckCheck className="w-4 h-4" />
                    <span>
                      {currentSeasonData.temporada_vista
                        ? (language === 'es' ? 'Temporada Vista' : 'Season Watched')
                        : (language === 'es' ? 'Marcar Temporada Completa' : 'Mark Entire Season')}
                    </span>
                  </button>
                </div>
              </div>
            )}

            {/* Episode List */}
            {currentSeasonData && currentSeasonData.episodios && (
              episodesCollapsed ? (
                <div
                  onClick={() => setEpisodesCollapsed(false)}
                  className="p-4 text-center rounded-xl bg-[#141414] hover:bg-[#1c1c1c] border border-[#262626] text-xs text-gray-400 hover:text-amber-300 cursor-pointer transition-colors space-y-1"
                >
                  <p className="font-semibold text-gray-300">
                    {language === 'es'
                      ? `${currentSeasonData.cantidad_episodios} episodios ocultos de la Temporada ${currentSeasonData.numero}`
                      : `${currentSeasonData.cantidad_episodios} episodes hidden for Season ${currentSeasonData.numero}`}
                  </p>
                  <p className="text-[11px] text-amber-500/80">
                    {language === 'es' ? 'Haz clic para ver la lista de episodios' : 'Click to expand episode list'}
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {currentSeasonData.episodios.map((ep) => {
                    const isEpWatched = !!ep.visto
                    const todayStr = new Date().toISOString().split('T')[0]
                    const isUnreleased = !!(ep.fecha_estreno && ep.fecha_estreno > todayStr)

                    return (
                      <div
                        key={ep.id}
                        className={`flex items-start justify-between gap-4 p-3.5 rounded-xl border transition-colors ${
                          isEpWatched
                            ? 'bg-emerald-950/20 border-emerald-900/50'
                            : isUnreleased
                            ? 'bg-[#111827]/40 border-dashed border-gray-800/60 opacity-80'
                            : 'bg-[#111827] border-gray-800/80 hover:border-gray-700'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <button
                            onClick={() =>
                              handleEpisodeToggle(
                                currentSeasonData.numero,
                                ep.numero,
                                isUnreleased,
                                isEpWatched
                              )
                            }
                            title={
                              isEpWatched
                                ? (language === 'es' ? 'Marcar como no visto' : 'Mark as unwatched')
                                : isUnreleased
                                ? (language === 'es' ? `Sin estrenar (estreno: ${ep.fecha_estreno})` : `Unreleased (air date: ${ep.fecha_estreno})`)
                                : (language === 'es' ? 'Marcar como visto' : 'Mark as watched')
                            }
                            className={`mt-0.5 p-1 rounded-full transition-colors ${
                              isEpWatched
                                ? 'text-emerald-400 hover:text-gray-400'
                                : isUnreleased
                                ? 'text-gray-600 hover:text-amber-400 cursor-not-allowed'
                                : 'text-gray-600 hover:text-emerald-400'
                            }`}
                          >
                            <Eye className={`w-5 h-5 ${isEpWatched ? 'stroke-[2.5]' : ''}`} />
                          </button>

                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h4 className="text-sm font-semibold text-white">
                                <span className="text-amber-400 mr-2">E{ep.numero}</span>
                                {ep.nombre}
                              </h4>
                              {isUnreleased && !isEpWatched && (
                                <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[10px] font-semibold flex items-center gap-1">
                                  <Clock className="w-3 h-3" /> {language === 'es' ? 'Sin estrenar' : 'Unreleased'}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-3 text-[11px] text-gray-500">
                              {ep.fecha_estreno ? (
                                <span className={isUnreleased ? 'text-amber-400/80 font-medium' : ''}>
                                  {language === 'es' ? 'Fecha de estreno:' : 'Air Date:'} {ep.fecha_estreno}
                                </span>
                              ) : (
                                <span>{language === 'es' ? 'Fecha de estreno: -' : 'Air Date: -'}</span>
                              )}
                              <span>• {ep.duracion && ep.duracion > 0 ? `${ep.duracion} min` : '-'}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )
            )}
          </section>
        )}

        {/* Sección de Reseñas */}
        <section className="space-y-6 pt-6 border-t border-gray-800">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-amber-400" />{' '}
              {language === 'es' ? 'Reseñas y Opiniones' : 'Reviews & Opinions'}
            </h2>
            <span className="text-xs text-gray-400">
              {reviews.length} {language === 'es' ? 'reseñas' : 'reviews'}
            </span>
          </div>

          {reviewSuccess && (
            <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/80 text-xs text-emerald-300">
              {language === 'es'
                ? '¡Tu reseña se publicó exitosamente y la calificación unificada ha sido actualizada!'
                : 'Your review was published successfully and unified rating has been updated!'}
            </div>
          )}

          {/* Gestión de reseña propia del usuario logueado */}
          {user ? (
            (() => {
              const userReview = reviews.find((r) => r.usuario_id === user.id)

              if (userReview && !isEditingReview) {
                return (
                  <div className="p-5 rounded-2xl bg-[#171717] border-2 border-amber-500/40 space-y-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-amber-500/20 border border-amber-500/50 flex items-center justify-center text-xs font-bold text-amber-300">
                          {user.nombre_usuario.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-xs font-bold text-white">@{user.nombre_usuario}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40 font-semibold">
                          {language === 'es' ? 'Tu Reseña' : 'Your Review'}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {userReview.puntaje !== null && userReview.puntaje !== undefined ? (
                          <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#0d0d0d] border border-[#262626] text-amber-400 text-xs font-bold">
                            <Star className="w-3.5 h-3.5 fill-current" />
                            <span>{userReview.puntaje.toFixed(1)}/10</span>
                          </div>
                        ) : (
                          <span className="text-xs text-gray-400 italic">
                            {language === 'es' ? 'Sin puntuación' : 'No score rating'}
                          </span>
                        )}

                        <button
                          type="button"
                          onClick={() => handleStartEdit(userReview)}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#222222] hover:bg-[#2c2c2c] text-gray-200 hover:text-white border border-[#333333] text-xs font-semibold transition-colors"
                          title={language === 'es' ? 'Editar tu reseña' : 'Edit your review'}
                        >
                          <Pencil className="w-3.5 h-3.5 text-amber-400" />
                          <span>{language === 'es' ? 'Editar' : 'Edit'}</span>
                        </button>

                        <button
                          type="button"
                          onClick={handleDeleteReview}
                          disabled={deletingReview}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-red-950/30 hover:bg-red-900/50 text-red-300 hover:text-red-200 border border-red-800/40 text-xs font-semibold transition-colors disabled:opacity-50"
                          title={language === 'es' ? 'Eliminar reseña' : 'Delete review'}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>{deletingReview ? (language === 'es' ? 'Eliminando...' : 'Deleting...') : (language === 'es' ? 'Eliminar' : 'Delete')}</span>
                        </button>
                      </div>
                    </div>

                    <p className="text-xs sm:text-sm text-gray-200 leading-relaxed whitespace-pre-line">
                      {userReview.texto}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-gray-500 pt-1 border-t border-[#262626]">
                      <span>
                        {userReview.fecha
                          ? `${language === 'es' ? 'Última actualización:' : 'Last updated:'} ${new Date(userReview.fecha).toLocaleDateString()}`
                          : ''}
                      </span>
                    </div>
                  </div>
                )
              }

              // Si no tiene reseña previa, verificar si es elegible (ha visto la película o al menos un episodio de la serie)
              const hasWatchedEpisodes = !!title.temporadas?.some((t) => t.episodios?.some((e) => e.visto))
              const isEligibleToReview = title.tipo === 'movie'
                ? userEstado === 'vista'
                : userEstado === 'vista' || hasWatchedEpisodes

              // Si no tiene reseña y no ha visto el título, mostrar mensaje informativo en lugar del formulario
              if (!userReview && !isEligibleToReview) {
                return (
                  <div className="p-5 rounded-2xl bg-[#141414] border border-[#262626] flex items-center gap-4 text-xs text-gray-300 shadow-sm">
                    <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 shrink-0">
                      <Eye className="w-5 h-5" />
                    </div>
                    <div className="space-y-0.5">
                      <p className="font-semibold text-gray-200">
                        {language === 'es' ? '¿Quieres dejar tu reseña?' : 'Want to leave a review?'}
                      </p>
                      <p className="text-gray-400">
                        {language === 'es'
                          ? title.tipo === 'movie'
                            ? 'Debes marcar la película como vista para poder dejar una reseña.'
                            : 'Debes marcar la serie como vista o al menos un episodio para poder dejar una reseña.'
                          : title.tipo === 'movie'
                            ? 'You must mark this movie as watched to leave a review.'
                            : 'You must mark this series as watched or at least one episode to leave a review.'}
                      </p>
                    </div>
                  </div>
                )
              }

              // Formulario de edición o creación
              return (
                <form
                  onSubmit={handleReviewSubmit}
                  className="p-5 rounded-2xl bg-[#141414] border border-[#262626] space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold text-gray-200 uppercase tracking-wider">
                      {isEditingReview
                        ? (language === 'es' ? 'Edita tu reseña' : 'Edit your review')
                        : (language === 'es' ? 'Deja tu reseña' : 'Leave your review')}
                    </h3>
                    {isEditingReview && (
                      <button
                        type="button"
                        onClick={handleCancelEdit}
                        className="text-xs text-gray-400 hover:text-white underline"
                      >
                        {language === 'es' ? 'Cancelar' : 'Cancel'}
                      </button>
                    )}
                  </div>

                  {/* Toggle para dejar puntaje o no */}
                  <div className="space-y-3">
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300 select-none">
                      <input
                        type="checkbox"
                        checked={includeScore}
                        onChange={(e) => setIncludeScore(e.target.checked)}
                        className="w-4 h-4 rounded border-[#333333] bg-[#0d0d0d] text-amber-500 focus:ring-amber-500"
                      />
                      <span className="font-medium">
                        {language === 'es' ? 'Incluir puntuación' : 'Include rating score'}
                      </span>
                    </label>

                    {includeScore && (
                      <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-[#0d0d0d] border border-[#262626]">
                        <div className="flex items-center gap-1.5">
                          <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                          <span className="text-sm font-bold text-amber-400 w-12 text-center">
                            {reviewScore.toFixed(1)}
                          </span>
                          <span className="text-[11px] text-gray-500">/ 10</span>
                        </div>

                        {/* Botones de incremento / decremento de 0.5 */}
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => setReviewScore((prev) => Math.max(0, Math.round((prev - 0.5) * 2) / 2))}
                            className="p-1.5 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] text-gray-300 hover:text-white border border-[#333333] transition-colors"
                            title="-0.5"
                          >
                            <Minus className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setReviewScore((prev) => Math.min(10, Math.round((prev + 0.5) * 2) / 2))}
                            className="p-1.5 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] text-gray-300 hover:text-white border border-[#333333] transition-colors"
                            title="+0.5"
                          >
                            <Plus className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Slider continuo con salto de 0.5 */}
                        <input
                          type="range"
                          min="0"
                          max="10"
                          step="0.5"
                          value={reviewScore}
                          onChange={(e) => setReviewScore(parseFloat(e.target.value))}
                          className="flex-1 min-w-[140px] accent-amber-500 cursor-pointer h-1.5 bg-[#262626] rounded-lg"
                        />
                      </div>
                    )}
                  </div>

                  <textarea
                    required
                    rows={3}
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    placeholder={
                      language === 'es'
                        ? '¿Qué te pareció este título? Comparte tu opinión sin spoilers...'
                        : 'What did you think of this title? Share your thoughts without spoilers...'
                    }
                    className="w-full p-3 text-sm bg-[#0d0d0d] border border-[#262626] rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
                  />

                  <div className="flex justify-end gap-2">
                    {isEditingReview && (
                      <button
                        type="button"
                        onClick={handleCancelEdit}
                        className="px-4 py-2 rounded-xl bg-[#222222] hover:bg-[#2c2c2c] text-gray-300 hover:text-white text-xs font-bold transition-all"
                      >
                        {language === 'es' ? 'Cancelar' : 'Cancel'}
                      </button>
                    )}
                    <button
                      type="submit"
                      disabled={submittingReview}
                      className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      {submittingReview
                        ? (language === 'es' ? 'Guardando...' : 'Saving...')
                        : isEditingReview
                        ? (language === 'es' ? 'Guardar Cambios' : 'Save Changes')
                        : (language === 'es' ? 'Publicar Reseña' : 'Post Review')}
                    </button>
                  </div>
                </form>
              )
            })()
          ) : (
            <div className="p-6 rounded-2xl bg-[#141414] border border-[#262626] text-center space-y-2">
              <p className="text-xs text-gray-400">
                {language === 'es' ? 'Inicia sesión para calificar y dejar una reseña.' : 'Sign in to rate and leave a review.'}
              </p>
              <button
                onClick={() => openAuth('login')}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md transition-all"
              >
                {language === 'es' ? 'Iniciar Sesión para Reseñar' : 'Sign In to Review'}
              </button>
            </div>
          )}

          {/* Listado de reseñas de la comunidad y TMDB */}
          <div className="space-y-4">
            {(() => {
              const otherReviews = reviews.filter((r) => !user || r.usuario_id !== user.id)

              if (otherReviews.length === 0) {
                const hasUserReview = user && reviews.some((r) => r.usuario_id === user.id)
                return (
                  <p className="text-xs text-gray-500 italic">
                    {hasUserReview
                      ? (language === 'es' ? 'Aún no hay otras reseñas para este título.' : 'No other reviews for this title yet.')
                      : (language === 'es' ? 'Aún no hay reseñas para este título. ¡Sé el primero en compartir tu opinión!' : 'No reviews for this title yet. Be the first to share your thoughts!')}
                  </p>
                )
              }

              return (
                <>
                  {otherReviews.map((rev) => (
                    <div
                      key={rev.id}
                      className="p-4 rounded-xl bg-[#141414] border border-[#262626] space-y-2"
                    >
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-xs font-bold text-amber-300">
                            {rev.nombre_usuario
                              ? rev.nombre_usuario.charAt(0).toUpperCase()
                              : rev.autor_tmdb
                              ? rev.autor_tmdb.charAt(0).toUpperCase()
                              : 'U'}
                          </div>
                          <span className="text-xs font-semibold text-gray-200">
                            {rev.nombre_usuario || rev.autor_tmdb || (language === 'es' ? 'Usuario' : 'User')}
                          </span>
                          {rev.autor_tmdb && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#202020] text-amber-400/90 border border-amber-500/30 font-semibold">
                              {language === 'es' ? 'Reseña TMDB' : 'TMDB Review'}
                            </span>
                          )}
                        </div>

                        {rev.puntaje !== null && rev.puntaje !== undefined && (
                          <div className="flex items-center gap-1 text-amber-400 text-xs font-bold">
                            <Star className="w-3 h-3 fill-current" />
                            <span>{rev.puntaje}/10</span>
                          </div>
                        )}
                      </div>

                      <p className="text-xs sm:text-sm text-gray-300 leading-relaxed whitespace-pre-line">
                        {rev.texto}
                      </p>
                      <span className="text-[10px] text-gray-500 block">
                        {rev.fecha ? new Date(rev.fecha).toLocaleDateString() : '-'}
                      </span>
                    </div>
                  ))}

                  {/* Paginación / Cargar más */}
                  {hasMoreReviews && (
                    <div className="flex justify-center pt-2">
                      <button
                        type="button"
                        onClick={handleLoadMoreReviews}
                        disabled={loadingMoreReviews}
                        className="px-5 py-2 rounded-xl bg-[#171717] hover:bg-[#202020] border border-[#262626] text-xs font-semibold text-gray-300 hover:text-white transition-all disabled:opacity-50"
                      >
                        {loadingMoreReviews
                          ? (language === 'es' ? 'Cargando más reseñas...' : 'Loading more reviews...')
                          : (language === 'es' ? 'Cargar más reseñas' : 'Load more reviews')}
                      </button>
                    </div>
                  )}
                </>
              )
            })()}
          </div>
        </section>
      </div>
    </div>
  )
}
