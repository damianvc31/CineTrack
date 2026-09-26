import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { useParams, Link, useOutletContext } from 'react-router-dom'
import {
  Star,
  Heart,
  Bookmark,
  Eye,
  EyeOff,
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
import { useTitleMutations } from '@/hooks/useTitleMutations'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/context/ToastContext'
import posterFallback from '@/assets/placeholders/poster-empty.svg'
import { CountryFlag } from '@/components/common/CountryFlag'
import { getLanguageName } from '@/utils/countryUtils'

interface OutletContextType {
  openAuth: (mode?: 'login' | 'register') => void
}

const getActorInitials = (fullName: string): string => {
  if (!fullName) return '?'
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return parts.map(p => p[0]).join('').toUpperCase().slice(0, 3)
}

const ActorAvatar: React.FC<{ nombre: string; fotoUrl?: string | null }> = ({ nombre, fotoUrl }) => {
  const [hasError, setHasError] = useState(false)
  const initials = getActorInitials(nombre)

  return (
    <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-[#2b2b2b] group-hover:border-amber-500/50 bg-[#1c1c1c] flex items-center justify-center shrink-0 shadow-md transition-all">
      {fotoUrl && !hasError ? (
        <img
          src={fotoUrl}
          alt={nombre}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          onError={() => setHasError(true)}
        />
      ) : (
        <span className="text-lg font-black text-gray-400 group-hover:text-amber-400 transition-colors tracking-wider">
          {initials}
        </span>
      )}
    </div>
  )
}

export const TitleDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { language, translateGenreName } = useLanguage()
  const { openAuth } = useOutletContext<OutletContextType>()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

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
  const [showAllCast, setShowAllCast] = useState(false)

  // Estados de hover y supresión inmediata post-clic para botones de acción
  const [isFavHovered, setIsFavHovered] = useState(false)
  const [justToggledFav, setJustToggledFav] = useState(false)

  const [isWlHovered, setIsWlHovered] = useState(false)
  const [justToggledWl, setJustToggledWl] = useState(false)

  const [isWatchedHovered, setIsWatchedHovered] = useState(false)
  const [justToggledWatched, setJustToggledWatched] = useState(false)

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

  // Calificación personal del usuario (de su reseña o de user_rating en el título)
  const userPersonalScore = useMemo(() => {
    if (!user) return null
    const userRev = reviews.find((r) => r.usuario_id === user.id)
    if (userRev && userRev.puntaje !== null && userRev.puntaje !== undefined) {
      return userRev.puntaje
    }
    return title?.user_rating ?? null
  }, [user, reviews, title])

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

  const { favoriteMutation, watchlistMutation, watchedMutation } = useTitleMutations()

  const handleFavoriteToggle = () => {
    if (!user) {
      openAuth()
      return
    }
    const prevFav = isFavorite
    const nextFav = !prevFav
    setIsFavorite(nextFav)
    setJustToggledFav(true)
    favoriteMutation.mutate(titleId, {
      onError: () => setIsFavorite(prevFav),
    })
  }

  const handleWatchlistToggle = () => {
    if (!user) {
      openAuth()
      return
    }
    const prevEstado = userEstado
    const nextEstado = prevEstado === 'watchlist' ? null : 'watchlist'
    setUserEstado(nextEstado)
    setJustToggledWl(true)
    watchlistMutation.mutate(titleId, {
      onError: () => setUserEstado(prevEstado),
    })
  }

  const handleWatchedToggle = () => {
    if (!user) {
      openAuth()
      return
    }
    const prevEstado = userEstado
    const isCurrentlyWatched = prevEstado === 'vista'
    const nextEstado = isCurrentlyWatched ? null : 'vista'

    if (isCurrentlyWatched && title?.tipo === 'tv' && title.temporadas) {
      setTitle((prev) => {
        if (!prev || !prev.temporadas) return prev
        const resetTemporadas = prev.temporadas.map((s) => ({
          ...s,
          episodios: s.episodios?.map((e) => ({ ...e, visto: false })) || [],
        }))
        return { ...prev, temporadas: resetTemporadas }
      })
    }

    setUserEstado(nextEstado)
    setJustToggledWatched(true)
    watchedMutation.mutate(titleId, {
      onError: () => {
        setUserEstado(prevEstado)
        loadData(false)
      },
      onSuccess: () => {
        loadData(false)
      },
    })
  }

  const handleUnfollow = async () => {
    if (!user) {
      openAuth()
      return
    }
    const prevEstado = userEstado
    setUserEstado(null)
    try {
      const res = await catalogService.unfollowSeries(titleId)
      setUserEstado(res.nuevo_estado ?? null)
      queryClient.invalidateQueries({ queryKey: ['userLibrary'] })
      queryClient.invalidateQueries({ queryKey: ['userStats'] })
      queryClient.invalidateQueries({ queryKey: ['homeSections'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
    } catch (err) {
      setUserEstado(prevEstado)
      showToast(
        language === 'es'
          ? 'No se pudo abandonar la serie. Por favor, reintenta.'
          : 'Could not drop series. Please try again.',
        'error'
      )
    }
  }

  const handleFollow = async () => {
    if (!user) {
      openAuth()
      return
    }
    const prevEstado = userEstado
    setUserEstado('siguiendo')
    try {
      const res = await catalogService.followSeries(titleId)
      setUserEstado(res.nuevo_estado ?? 'siguiendo')
      queryClient.invalidateQueries({ queryKey: ['userLibrary'] })
      queryClient.invalidateQueries({ queryKey: ['userStats'] })
      queryClient.invalidateQueries({ queryKey: ['homeSections'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
    } catch (err) {
      setUserEstado(prevEstado)
      showToast(
        language === 'es'
          ? 'No se pudo reanudar el seguimiento. Por favor, reintenta.'
          : 'Could not resume following. Please try again.',
        'error'
      )
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
      setEpisodeNotice(
        language === 'es'
          ? `El episodio E${episodeNum} aún no se ha estrenado. Solo se pueden marcar episodios emitidos.`
          : `Episode E${episodeNum} has not aired yet. Only aired episodes can be marked.`
      )
      setTimeout(() => setEpisodeNotice(null), 4500)
      return
    }

    const prevTitle = title
    const prevEstado = userEstado
    const nextWatched = !isWatched

    // 1. Parche optimista instantáneo (0 ms) en temporadas y episodios
    setTitle((prev) => {
      if (!prev || !prev.temporadas) return prev
      const todayStr = new Date().toISOString().split('T')[0]
      const isTitleEnded = !!(
        prev.status_tmdb &&
        (prev.status_tmdb.toLowerCase().includes('ended') || prev.status_tmdb.toLowerCase().includes('cancel'))
      )
      const updatedSeasons = prev.temporadas.map((s) => {
        if (s.numero !== seasonNum) return s
        const updatedEpisodes =
          s.episodios?.map((e) => {
            if (e.numero !== episodeNum) return e
            return { ...e, visto: nextWatched }
          }) || []
        const watchedCount = updatedEpisodes.filter((e) => e.visto).length

        // Episodios disponibles para ver (emitidos hasta la fecha)
        const availableEpisodes = updatedEpisodes.filter((e) => {
          const isEpUnreleased = !isTitleEnded && !!(
            !e.fecha_estreno ||
            e.fecha_estreno > todayStr ||
            (prev.proximo_episodio_fecha && prev.proximo_episodio_fecha > todayStr && e.fecha_estreno && e.fecha_estreno >= prev.proximo_episodio_fecha)
          )
          return !isEpUnreleased
        }).length

        const isSeasonComplete = availableEpisodes > 0 && watchedCount >= availableEpisodes

        return {
          ...s,
          episodios: updatedEpisodes,
          episodios_vistos: watchedCount,
          temporada_vista: isSeasonComplete,
        }
      })
      return { ...prev, temporadas: updatedSeasons }
    })

    // 2. Parche semántico en el estado de la serie
    if (nextWatched && prevEstado !== 'siguiendo' && prevEstado !== 'vista') {
      setUserEstado('siguiendo')
    }

    // 3. Envío al backend en background
    try {
      const res = await catalogService.toggleEpisodeWatch(titleId, seasonNum, episodeNum)
      if (res.nuevo_estado_serie !== undefined) {
        setUserEstado(res.nuevo_estado_serie)
      }
      queryClient.invalidateQueries({ queryKey: ['userLibrary'] })
      queryClient.invalidateQueries({ queryKey: ['userStats'] })
      queryClient.invalidateQueries({ queryKey: ['homeSections'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
    } catch (err: unknown) {
      setTitle(prevTitle)
      setUserEstado(prevEstado)
      showToast(
        language === 'es'
          ? 'No se pudo actualizar el episodio. Por favor, reintenta.'
          : 'Could not update episode. Please try again.',
        'error'
      )
    }
  }

  const handleToggleSeasonWatched = async (seasonNum: number) => {
    if (!user) {
      openAuth()
      return
    }
    if (!title || !title.temporadas) return
    const currentSeason = title.temporadas.find((s) => s.numero === seasonNum)
    if (!currentSeason) return

    const prevTitle = title
    const prevEstado = userEstado
    const wasSeasonWatched = !!currentSeason.temporada_vista
    const targetWatched = !wasSeasonWatched
    const todayStr = new Date().toISOString().split('T')[0]

    // 1. Parche optimista instantáneo (0 ms) en la temporada
    setTitle((prev) => {
      if (!prev || !prev.temporadas) return prev
      const updatedSeasons = prev.temporadas.map((s) => {
        if (s.numero !== seasonNum) return s
        const isTitleEnded = !!(
          title?.status_tmdb &&
          (title.status_tmdb.toLowerCase().includes('ended') || title.status_tmdb.toLowerCase().includes('cancel'))
        )
        const updatedEpisodes =
          s.episodios?.map((e) => {
            const isUnreleased = !isTitleEnded && !!(
              !e.fecha_estreno ||
              e.fecha_estreno > todayStr ||
              (title?.proximo_episodio_fecha && title.proximo_episodio_fecha > todayStr && e.fecha_estreno && e.fecha_estreno >= title.proximo_episodio_fecha)
            )
            if (targetWatched && isUnreleased) return e
            return { ...e, visto: targetWatched }
          }) || []
        const watchedCount = updatedEpisodes.filter((e) => e.visto).length
        return {
          ...s,
          episodios: updatedEpisodes,
          episodios_vistos: watchedCount,
          temporada_vista: targetWatched,
        }
      })
      return { ...prev, temporadas: updatedSeasons }
    })

    if (targetWatched && prevEstado !== 'siguiendo' && prevEstado !== 'vista') {
      setUserEstado('siguiendo')
    }

    setSeasonWatchLoading(true)
    try {
      const res = await catalogService.toggleSeasonWatch(titleId, seasonNum)
      if (res.nuevo_estado_serie !== undefined) {
        setUserEstado(res.nuevo_estado_serie)
      }
      queryClient.invalidateQueries({ queryKey: ['userLibrary'] })
      queryClient.invalidateQueries({ queryKey: ['userStats'] })
      queryClient.invalidateQueries({ queryKey: ['homeSections'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
    } catch (err) {
      setTitle(prevTitle)
      setUserEstado(prevEstado)
      showToast(
        language === 'es'
          ? 'No se pudo actualizar la temporada completa. Por favor, reintenta.'
          : 'Could not update full season. Please try again.',
        'error'
      )
    } finally {
      setSeasonWatchLoading(false)
    }
  }

  const handleStartEdit = (rev: ReviewItem) => {
    setIsEditingReview(true)
    setReviewText(rev.texto || '')
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
    if (!reviewText.trim() && !includeScore) return

    setSubmittingReview(true)
    try {
      const finalScore = includeScore ? Math.round(reviewScore * 2) / 2 : null
      const saved = await catalogService.addReview(titleId, reviewText.trim() || undefined, finalScore)
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

  // Helper to check if a date is strictly in the future within 15 days
  const isWithin15Days = (dStr?: string | null, todayStrVal?: string) => {
    if (!dStr) return false
    const nowStr = todayStrVal || new Date().toISOString().split('T')[0]
    if (dStr <= nowStr) return false
    const target = new Date(dStr)
    const today = new Date(nowStr)
    const diffDays = (target.getTime() - today.getTime()) / (1000 * 3600 * 24)
    return diffDays > 0 && diffDays <= 15
  }

  // Render semantic status badge based on season progress, release dates and TMDB status
  const renderStatusBadge = () => {
    if (!title.status_tmdb) return null
    const st = title.status_tmdb.toLowerCase()
    const todayStr = new Date().toISOString().split('T')[0]

    // 1. Películas (tipo === 'movie')
    if (title.tipo === 'movie') {
      const movieDate = title.fecha_estreno
      const isSoon = isWithin15Days(movieDate, todayStr)

      if (isSoon) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/60 text-cyan-300 text-xs font-bold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span>{language === 'es' ? 'Muy Pronto' : 'Coming Soon'} — {language === 'es' ? `Estreno el ${movieDate}` : `Release on ${movieDate}`}</span>
          </span>
        )
      }

      if (st.includes('post')) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-950/80 border border-indigo-500/60 text-indigo-300 text-xs font-bold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-indigo-400" />
            <span>{language === 'es' ? 'Postproducción' : 'Post-Production'}{movieDate ? (language === 'es' ? ` — Estreno el ${movieDate}` : ` — Release on ${movieDate}`) : ' (TBA)'}</span>
          </span>
        )
      }

      // 1.c: En Producción (Teal - sobrio, familia del cian)
      if (st.includes('production')) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-950/80 border border-teal-500/60 text-teal-300 text-xs font-bold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-teal-400" />
            <span>{language === 'es' ? 'En Producción' : 'In Production'}{movieDate ? (language === 'es' ? ` — Estreno el ${movieDate}` : ` — Release on ${movieDate}`) : ' (TBA)'}</span>
          </span>
        )
      }

      // 1.d: Planificada (Slate)
      if (st.includes('planned')) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-700 text-slate-300 text-xs font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            <span>{language === 'es' ? 'Planificada' : 'Planned'}{movieDate ? (language === 'es' ? ` — Estreno el ${movieDate}` : ` — Release on ${movieDate}`) : ' (TBA)'}</span>
          </span>
        )
      }

      // 1.e: Próximo Estreno con fecha lejana (> 15 días)
      if (movieDate && movieDate > todayStr) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-600/50 text-amber-300 text-xs font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>{language === 'es' ? 'Próximo Estreno' : 'Upcoming Release'} — {language === 'es' ? `el ${movieDate}` : `on ${movieDate}`}</span>
          </span>
        )
      }

      // 1.f: Película ya estrenada (Verde esmeralda)
      if (st.includes('released') || (movieDate && movieDate <= todayStr)) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 text-xs font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>{language === 'es' ? 'Estrenada' : 'Released'}</span>
          </span>
        )
      }

      return null
    }

    // 2. Series (tipo === 'tv')
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

    // Detectar avance de temporadas y episodios
    let inProgressSeason: { seasonNum: number; nextEpDate?: string } | null = null
    let upcomingSeasonWithDate: { seasonNum: number; startDate: string } | null = null
    let confirmedSeasonDateless: { seasonNum: number } | null = null
    let totalAiredEpisodesCount = 0
    let latestAiredEpisodeDate: string | null = null

    if (title.temporadas && title.temporadas.length > 0) {
      const sortedSeasons = [...title.temporadas].sort((a, b) => a.numero - b.numero)

      for (const season of sortedSeasons) {
        const eps = season.episodios || []
        const airedEpisodes = eps.filter(
          (ep) =>
            ep.fecha_estreno &&
            (title.proximo_episodio_fecha && title.proximo_episodio_fecha > todayStr
              ? ep.fecha_estreno < title.proximo_episodio_fecha && ep.fecha_estreno <= todayStr
              : ep.fecha_estreno <= todayStr)
        )
        totalAiredEpisodesCount += airedEpisodes.length

        for (const ep of airedEpisodes) {
          if (ep.fecha_estreno && (!latestAiredEpisodeDate || ep.fecha_estreno > latestAiredEpisodeDate)) {
            latestAiredEpisodeDate = ep.fecha_estreno
          }
        }

        const unreleasedEpisodes = eps
          .filter(
            (ep) =>
              !ep.fecha_estreno ||
              ep.fecha_estreno > todayStr ||
              (title.proximo_episodio_fecha && title.proximo_episodio_fecha > todayStr && ep.fecha_estreno && ep.fecha_estreno >= title.proximo_episodio_fecha)
          )
          .sort((a, b) => {
            if (!a.fecha_estreno) return 1
            if (!b.fecha_estreno) return -1
            return a.fecha_estreno > b.fecha_estreno ? 1 : -1
          })

        if (airedEpisodes.length > 0 && unreleasedEpisodes.length > 0) {
          inProgressSeason = {
            seasonNum: season.numero,
            nextEpDate: (unreleasedEpisodes[0]?.fecha_estreno && unreleasedEpisodes[0].fecha_estreno > todayStr)
              ? unreleasedEpisodes[0].fecha_estreno
              : (title.proximo_episodio_fecha && title.proximo_episodio_fecha > todayStr ? title.proximo_episodio_fecha : undefined),
          }
          break
        }

        // Temporada que aún no comenzó
        if (airedEpisodes.length === 0) {
          const firstDated = unreleasedEpisodes.find((e) => e.fecha_estreno)
          if (firstDated) {
            if (!upcomingSeasonWithDate) {
              upcomingSeasonWithDate = {
                seasonNum: season.numero,
                startDate: firstDated.fecha_estreno!,
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
            if (!confirmedSeasonDateless) {
              confirmedSeasonDateless = {
                seasonNum: season.numero,
              }
            }
          }
        }
      }
    }

    const nextDate = title.proximo_episodio_fecha

    // State 1: Temporada activa en emisión -> Currently Airing (Pulso verde)
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

    // State 2: La serie AÚN NO HA ESTRENADO ningún episodio (Season 1 o totalAiredEpisodesCount === 0)
    const isShowUnreleased = totalAiredEpisodesCount === 0 || (upcomingSeasonWithDate && upcomingSeasonWithDate.seasonNum === 1) || (title.fecha_estreno && title.fecha_estreno > todayStr)
    if (isShowUnreleased) {
      const premiereDate = upcomingSeasonWithDate?.startDate || (nextDate && nextDate > todayStr ? nextDate : undefined) || title.fecha_estreno
      const isSoon = isWithin15Days(premiereDate, todayStr)

      // 2.a: Fecha confirmada en <= 15 días -> Muy Pronto / Coming Soon (Cian)
      if (isSoon && premiereDate) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/60 text-cyan-300 text-xs font-bold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span>{language === 'es' ? 'Muy Pronto' : 'Coming Soon'} — {language === 'es' ? `Estreno el ${premiereDate}` : `Series Premiere on ${premiereDate}`}</span>
          </span>
        )
      }

      // 2.b: TMDB status En Producción (Teal - sobrio, familia del cian)
      if (st.includes('production')) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-950/80 border border-teal-500/60 text-teal-300 text-xs font-bold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-teal-400" />
            <span>{language === 'es' ? 'En Producción' : 'In Production'}{premiereDate ? (language === 'es' ? ` — Estreno el ${premiereDate}` : ` — Premiere on ${premiereDate}`) : ' (TBA)'}</span>
          </span>
        )
      }

      // 2.c: TMDB status Planificada (Gris/Slate)
      if (st.includes('planned')) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-700 text-slate-300 text-xs font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            <span>{language === 'es' ? 'Planificada' : 'Planned'}{premiereDate ? (language === 'es' ? ` — Estreno el ${premiereDate}` : ` — Premiere on ${premiereDate}`) : ' (TBA)'}</span>
          </span>
        )
      }

      // 2.d: Fecha lejana (> 15 días)
      if (premiereDate && premiereDate > todayStr) {
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-600/50 text-amber-300 text-xs font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>{language === 'es' ? 'Próximo Estreno' : 'Upcoming Premiere'} — {language === 'es' ? `el ${premiereDate}` : `on ${premiereDate}`}</span>
          </span>
        )
      }
    }

    // State 3: Serie activa con temporadas previas que estrena NUEVA temporada en el calendario (Temporada > 1)
    if (upcomingSeasonWithDate) {
      const dateStr = upcomingSeasonWithDate.startDate
      const label = language === 'es' ? `Temporada ${upcomingSeasonWithDate.seasonNum}` : `Season ${upcomingSeasonWithDate.seasonNum}`

      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-950/80 border border-blue-500/60 text-blue-300 text-xs font-bold shadow-sm">
          <span className="w-2 h-2 rounded-full bg-blue-400" />
          <span>{language === 'es' ? 'Renovada' : 'Renewed'} — {label}{dateStr ? (language === 'es' ? ` el ${dateStr}` : ` on ${dateStr}`) : ''}</span>
        </span>
      )
    }

    // State 4: Renovación confirmada sin fecha fijada aún (o In Production / Planned para serie con temporadas previas)
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

    // State 4.b: Tratamiento excepcional para temporadas incompletas en TMDB
    // Solo aplica si la temporada más reciente tiene apenas 1 o 2 episodios cargados en total (ej. S.W.A.T. con solo el piloto),
    // todos ya se emitieron, y el estreno del PRIMER episodio fue reciente (<= 14 días).
    // Si la temporada tiene una grilla normal (>= 3 episodios) o si ya concluyó su ciclo, pasa de inmediato a Entre Temporadas.
    const isRecentIncompleteSeasonPremiere = (() => {
      if (st.includes('ended') || st.includes('cancel')) return false
      if (!title.temporadas || title.temporadas.length === 0) return false
      const sorted = [...title.temporadas].sort((a, b) => a.numero - b.numero)
      const latestSeason = sorted[sorted.length - 1]
      const eps = latestSeason?.episodios || []
      // Solo para temporadas con grilla trunca o incompleta en TMDB (1 o 2 episodios cargados en total)
      if (eps.length === 0 || eps.length > 2) return false

      // Todos los episodios cargados (1 o 2) ya se emitieron
      const aired = eps.filter((e) => e.fecha_estreno && e.fecha_estreno <= todayStr)
      if (aired.length !== eps.length) return false

      // La ventana de 14 días se cuenta estrictamente desde el PRIMER episodio de la temporada
      const firstEp = eps[0]
      const premiereDateStr = firstEp?.fecha_estreno || latestSeason.fecha_estreno
      if (!premiereDateStr) return false

      const premiereDate = new Date(premiereDateStr)
      const today = new Date(todayStr)
      const diffDays = (today.getTime() - premiereDate.getTime()) / (1000 * 3600 * 24)
      return diffDays >= 0 && diffDays <= 14
    })()

    if (isRecentIncompleteSeasonPremiere) {
      const nextDateStr =
        nextDate && nextDate > todayStr
          ? language === 'es'
            ? ` — Próximo ep. el ${nextDate}`
            : ` — Next ep on ${nextDate}`
          : ''
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 text-xs font-bold shadow-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>{language === 'es' ? 'En Emisión' : 'Currently Airing'}{nextDateStr}</span>
        </span>
      )
    }

    // State 5: Temporada concluida, show activo sin fecha futura anunciada -> Pending Renewal (Ámbar)
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
                  <span
                    title={language === 'es' ? `Percentil de popularidad: ${percentilNum}% (en base al catálogo)` : `Popularity percentile: ${percentilNum}% (based on catalog)`}
                    className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 font-bold text-xs cursor-default"
                  >
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
                <div
                  title={
                    language === 'es'
                      ? `Calificación de la comunidad: ${title.vote_average_tmdb.toFixed(1)} (${title.vote_count_tmdb} votos)`
                      : `Community rating: ${title.vote_average_tmdb.toFixed(1)} (${title.vote_count_tmdb} votes)`
                  }
                  className="flex items-center gap-1.5 text-amber-400 font-bold bg-amber-400/10 px-2.5 py-1 rounded-lg border border-amber-400/20 cursor-default"
                >
                  <Star className="w-4 h-4 fill-amber-400" />
                  <span>{title.vote_average_tmdb.toFixed(1)}</span>
                  <span className="text-[11px] text-gray-400 font-normal">
                    ({title.vote_count_tmdb} {language === 'es' ? 'votos' : 'votes'})
                  </span>
                </div>

                {userPersonalScore !== null && (
                  <div
                    title={language === 'es' ? `Tu puntaje: ${userPersonalScore.toFixed(1)}` : `Your score: ${userPersonalScore.toFixed(1)}`}
                    className="flex items-center gap-1.5 text-sky-400 font-bold bg-sky-950/40 px-2.5 py-1 rounded-lg border border-sky-500/40 shadow-sm cursor-default"
                  >
                    <Star className="w-4 h-4 fill-sky-400 text-sky-400" />
                    <span>{userPersonalScore.toFixed(1)}</span>
                    <span className="text-[11px] text-sky-300/80 font-normal">
                      ({language === 'es' ? 'tu puntaje' : 'your score'})
                    </span>
                  </div>
                )}

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
                    // Desglose de duplas al clickear un género (Sci-Fi & Fantasy -> Sci-Fi + Fantasy OR)
                    const norm = gName.trim().toLowerCase()
                    const genreUrl =
                      norm === 'sci-fi & fantasy' || norm === 'science fiction & fantasy'
                        ? '/catalog?generos=Sci-Fi,Fantasy&genre_op=or'
                        : norm === 'action & adventure'
                        ? '/catalog?generos=Action,Adventure&genre_op=or'
                        : norm === 'war & politics'
                        ? '/catalog?generos=War'
                        : `/catalog?generos=${encodeURIComponent(gName.trim())}`

                    return (
                      <Link
                        key={gName}
                        to={genreUrl}
                        className="px-2.5 py-1 rounded-md bg-gray-800/80 hover:bg-gray-700/80 border border-gray-700/60 text-xs text-gray-300 transition-colors"
                      >
                        {translateGenreName(gName)}
                      </Link>
                    )
                  })}
                </div>
              )}

              {/* 4 Action Icons */}
              {(() => {
                const favUnfilled = isFavorite && isFavHovered && !justToggledFav
                const wlUnfilled = userEstado === 'watchlist' && isWlHovered && !justToggledWl
                const isWatched = userEstado === 'vista'
                const effectiveHoverWatched = isWatchedHovered && !justToggledWatched
                const showingWatched = effectiveHoverWatched ? !isWatched : isWatched

                return (
                  <div className="pt-4 border-t border-gray-800 flex flex-wrap items-center gap-3">
                    {/* 1. Favorite button */}
                    <button
                      onClick={handleFavoriteToggle}
                      onMouseEnter={() => setIsFavHovered(true)}
                      onMouseLeave={() => {
                        setIsFavHovered(false)
                        setJustToggledFav(false)
                      }}
                      title={
                        isFavorite
                          ? (language === 'es' ? 'Quitar de favoritos' : 'Remove from favorites')
                          : (language === 'es' ? 'Agregar a favoritos' : 'Add to favorites')
                      }
                      className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                        isFavorite
                          ? 'bg-rose-900/40 border-rose-500 text-rose-300 hover:bg-rose-900/60 hover:border-rose-400 shadow-md'
                          : 'bg-[#141414] border-[#262626] text-gray-300 hover:bg-rose-950/30 hover:border-rose-500/40 hover:text-rose-300'
                      }`}
                    >
                      <Heart
                        className={`w-4 h-4 transition-all ${
                          isFavorite && !favUnfilled ? 'fill-current' : ''
                        }`}
                      />
                      <span>{language === 'es' ? 'Favorito' : 'Favorite'}</span>
                    </button>

                    {/* 2. Watched button (muestra Not Watched en reposo si no está vista, Vista al posar el mouse) */}
                    <button
                      onClick={handleWatchedToggle}
                      onMouseEnter={() => setIsWatchedHovered(true)}
                      onMouseLeave={() => {
                        setIsWatchedHovered(false)
                        setJustToggledWatched(false)
                      }}
                      title={
                        isWatched
                          ? (language === 'es' ? 'Marcar como no vista' : 'Mark as unwatched')
                          : (language === 'es' ? 'Marcar como vista' : 'Mark as watched')
                      }
                      className={`flex items-center justify-center gap-1.5 min-w-[124px] px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                        showingWatched
                          ? 'bg-emerald-900/40 border-emerald-500 text-emerald-300 shadow-md'
                          : isWatched && effectiveHoverWatched
                          ? 'bg-[#18261e] border-emerald-600/70 text-emerald-300 shadow-sm'
                          : effectiveHoverWatched
                          ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                          : 'bg-[#141414] border-[#262626] text-gray-400 hover:border-emerald-500/40'
                      }`}
                    >
                      {showingWatched ? (
                        <Eye className="w-4 h-4 text-emerald-300 transition-colors" />
                      ) : (
                        <EyeOff
                          className={`w-4 h-4 transition-colors ${
                            isWatched && effectiveHoverWatched
                              ? 'text-emerald-400'
                              : 'text-gray-400'
                          }`}
                        />
                      )}
                      <span>
                        {showingWatched
                          ? (language === 'es' ? 'Vista' : 'Watched')
                          : (language === 'es' ? 'No vista' : 'Not watched')}
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
                            onMouseEnter={() => setIsWlHovered(true)}
                            onMouseLeave={() => {
                              setIsWlHovered(false)
                              setJustToggledWl(false)
                            }}
                            title={
                              userEstado === 'watchlist'
                                ? (language === 'es' ? 'Quitar de lista de seguimiento' : 'Remove from watchlist')
                                : (language === 'es' ? 'Agregar a lista de seguimiento' : 'Add to watchlist')
                            }
                            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                              userEstado === 'watchlist'
                                ? 'bg-amber-500/20 border-amber-500 text-amber-300 hover:bg-amber-500/30 hover:border-amber-400 shadow-md'
                                : 'bg-[#141414] border-[#262626] text-gray-300 hover:bg-amber-500/10 hover:border-amber-500/40 hover:text-amber-300'
                            }`}
                          >
                            <Bookmark
                              className={`w-4 h-4 transition-all ${
                                userEstado === 'watchlist' && !wlUnfilled ? 'fill-current' : ''
                              }`}
                            />
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
                      onMouseEnter={() => setIsWlHovered(true)}
                      onMouseLeave={() => {
                        setIsWlHovered(false)
                        setJustToggledWl(false)
                      }}
                      title={
                        userEstado === 'watchlist'
                          ? (language === 'es' ? 'Quitar de lista de seguimiento' : 'Remove from watchlist')
                          : (language === 'es' ? 'Agregar a lista de seguimiento' : 'Add to watchlist')
                      }
                      className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                        userEstado === 'watchlist'
                          ? 'bg-amber-500/20 border-amber-500 text-amber-300 hover:bg-amber-500/30 hover:border-amber-400 shadow-md'
                        : 'bg-[#141414] border-[#262626] text-gray-300 hover:bg-amber-500/10 hover:border-amber-500/40 hover:text-amber-300'
                      }`}
                    >
                      <Bookmark
                        className={`w-4 h-4 transition-all ${
                          userEstado === 'watchlist' && !wlUnfilled ? 'fill-current' : ''
                        }`}
                      />
                      <span>{language === 'es' ? 'Lista de seguimiento' : 'Watchlist'}</span>
                    </button>
                  )
                )}
              </div>
            )
          })()}
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

            {(() => {
              const displayedCast = showAllCast ? title.elenco : title.elenco.slice(0, 12)
              return (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 sm:gap-4">
                    {displayedCast.map((actor) => (
                      <Link
                        key={`${actor.actor_id}-${actor.orden}`}
                        to={`/catalog?actor=${encodeURIComponent(actor.nombre)}`}
                        className="p-3 rounded-2xl bg-[#141414] border border-[#262626] hover:border-amber-500/40 transition-all flex flex-col items-center text-center space-y-2.5 group shadow-sm block"
                      >
                        {/* Foto de perfil del actor con fallback e iniciales completas */}
                        <ActorAvatar nombre={actor.nombre} fotoUrl={actor.foto_url} />

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

                  {title.elenco.length > 12 && (
                    <div className="flex justify-center pt-2">
                      <button
                        type="button"
                        onClick={() => setShowAllCast(!showAllCast)}
                        className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold bg-[#141414] hover:bg-[#1a1a1a] border border-[#262626] hover:border-amber-500/40 text-gray-300 hover:text-amber-400 transition-all shadow-sm active:scale-95"
                      >
                        {showAllCast ? (
                          <>
                            <span>{language === 'es' ? 'Ver menos' : 'Show less'}</span>
                            <ChevronUp className="w-3.5 h-3.5 text-amber-500" />
                          </>
                        ) : (
                          <>
                            <span>
                              {language === 'es'
                                ? `Ver reparto completo (+${title.elenco.length - 12})`
                                : `Show all cast (+${title.elenco.length - 12})`}
                            </span>
                            <ChevronDown className="w-3.5 h-3.5 text-amber-500" />
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </>
              )
            })()}
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
                    const isTitleEnded = !!(
                      title?.status_tmdb &&
                      (title.status_tmdb.toLowerCase().includes('ended') || title.status_tmdb.toLowerCase().includes('cancel'))
                    )
                    const isUnreleased = !isTitleEnded && !!(
                      !ep.fecha_estreno ||
                      ep.fecha_estreno > todayStr ||
                      (title?.proximo_episodio_fecha && title.proximo_episodio_fecha > todayStr && ep.fecha_estreno && ep.fecha_estreno >= title.proximo_episodio_fecha)
                    )

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
                                ? (language === 'es' ? (ep.fecha_estreno ? `Sin estrenar (estreno: ${ep.fecha_estreno})` : 'Sin estrenar (fecha por anunciar)') : (ep.fecha_estreno ? `Unreleased (air date: ${ep.fecha_estreno})` : 'Unreleased (TBA)'))
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
                                <span className={isUnreleased ? 'text-amber-400/80 italic font-medium' : 'text-gray-500'}>
                                  {language === 'es' ? 'Fecha de estreno: Por anunciar (TBA)' : 'Air Date: TBA'}
                                </span>
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

                    {userReview.texto ? (
                      <p className="text-xs sm:text-sm text-gray-200 leading-relaxed whitespace-pre-line">
                        {userReview.texto}
                      </p>
                    ) : (
                      <p className="text-xs text-gray-400 italic">
                        {language === 'es' ? 'Sin reseña escrita (solo calificación)' : 'No written review (rating only)'}
                      </p>
                    )}

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
                      disabled={submittingReview || (!reviewText.trim() && !includeScore)}
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

                      {rev.texto ? (
                        <p className="text-xs sm:text-sm text-gray-300 leading-relaxed whitespace-pre-line">
                          {rev.texto}
                        </p>
                      ) : (
                        <p className="text-xs text-gray-500 italic">
                          {language === 'es' ? 'Sin reseña escrita (solo calificación)' : 'No written review (rating only)'}
                        </p>
                      )}
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
