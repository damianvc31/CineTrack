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
  User as UserIcon,
  MessageSquare,
  Send,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from 'lucide-react'
import { catalogService } from '@/services/catalogService'
import type { TitleDetail, ReviewItem, SeasonItem } from '@/types/catalog'
import { useAuth } from '@/context/AuthContext'
import posterFallback from '@/assets/placeholders/poster-empty.svg'
import { CountryFlag } from '@/components/common/CountryFlag'
import { getLanguageName } from '@/utils/countryUtils'

interface OutletContextType {
  openAuth: () => void
}

export const TitleDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { openAuth } = useOutletContext<OutletContextType>()

  const [title, setTitle] = useState<TitleDetail | null>(null)
  const [reviews, setReviews] = useState<ReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Estado de interacción de usuario
  const [isFavorite, setIsFavorite] = useState(false)
  const [userEstado, setUserEstado] = useState<string | null>(null)
  const [selectedSeason, setSelectedSeason] = useState<number>(1)
  const [newReviewText, setNewReviewText] = useState('')
  const [newReviewRating, setNewReviewRating] = useState<number>(8)
  const [submittingReview, setSubmittingReview] = useState(false)
  const [reviewSuccess, setReviewSuccess] = useState(false)
  const [seasonWatchLoading, setSeasonWatchLoading] = useState(false)
  const [episodeNotice, setEpisodeNotice] = useState<string | null>(null)

  const titleId = parseInt(id || '0', 10)

  const loadData = useCallback(async (showSpinner = true) => {
    if (!titleId) return
    if (showSpinner) setLoading(true)
    setError(null)
    try {
      const [titleRes, reviewsRes] = await Promise.all([
        catalogService.getTitleDetail(titleId),
        catalogService.getReviews(titleId).catch(() => ({ items: [], total: 0 })),
      ])
      setTitle(titleRes)
      setIsFavorite(titleRes.user_favorito ?? false)
      setUserEstado(titleRes.user_estado ?? null)
      setReviews(reviewsRes.items || [])

      if (titleRes.tipo === 'tv' && titleRes.temporadas && titleRes.temporadas.length > 0) {
        setSelectedSeason((prev) => {
          const exists = titleRes.temporadas.some((t) => t.numero === prev)
          return exists ? prev : titleRes.temporadas[0].numero
        })
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Error al cargar la información del título.')
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
      console.error('Error alternando favorito:', err)
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
      console.error('Error alternando watchlist:', err)
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
      console.error('Error alternando visto:', err)
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
      console.error('Error abandonando serie:', err)
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
      setEpisodeNotice(`El episodio E${episodeNum} aún no se ha estrenado. Solo es posible marcar episodios emitidos.`)
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
        setEpisodeNotice('Error al actualizar el episodio.')
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

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) {
      openAuth()
      return
    }
    if (!newReviewText.trim()) return

    setSubmittingReview(true)
    try {
      const created = await catalogService.addReview(titleId, newReviewText.trim(), newReviewRating)
      setReviews([created, ...reviews])
      setNewReviewText('')
      setReviewSuccess(true)
      setTimeout(() => setReviewSuccess(false), 4000)
    } catch (err) {
      console.error('Error enviando reseña:', err)
    } finally {
      setSubmittingReview(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3">
        <div className="w-12 h-12 border-4 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
        <p className="text-xs text-gray-400">Loading title details...</p>
      </div>
    )
  }

  if (error || !title) {
    return (
      <div className="max-w-md mx-auto my-20 p-6 bg-[#141414] border border-[#262626] rounded-2xl text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-white mb-2">Title Not Found</h3>
        <p className="text-xs text-gray-400 mb-6">{error || 'The requested title does not exist or was removed.'}</p>
        <Link
          to="/"
          className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md transition-all"
        >
          Back to Home
        </Link>
      </div>
    )
  }

  const currentSeasonData: SeasonItem | undefined =
    title.tipo === 'tv'
      ? title.temporadas.find((s) => s.numero === selectedSeason)
      : undefined

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
  const seasonsLabel = `${title.total_seasons || 1} ${title.total_seasons === 1 ? 'temporada' : 'temporadas'}`

  // Renderizar tag semántico de estado de serie
  const renderStatusBadge = () => {
    if (title.tipo !== 'tv' || !title.status_tmdb) return null
    const st = title.status_tmdb.toLowerCase()

    if (st.includes('returning') || st.includes('emisión') || st.includes('emision')) {
      const nextDate = title.proximo_episodio_fecha
        ? ` — nueva temporada el ${title.proximo_episodio_fecha}`
        : ' — en emisión'
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 text-xs font-bold shadow-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Renovada{nextDate}</span>
        </span>
      )
    }

    if (st.includes('ended') || st.includes('finaliz')) {
      return (
        <span className="px-3 py-1 rounded-full bg-gray-800/90 border border-gray-600 text-gray-300 text-xs font-semibold">
          Finalizada
        </span>
      )
    }

    if (st.includes('cancel')) {
      return (
        <span className="px-3 py-1 rounded-full bg-red-950/80 border border-red-600/70 text-red-300 text-xs font-bold">
          Cancelada
        </span>
      )
    }

    return (
      <span className="px-3 py-1 rounded-full bg-gray-800 border border-gray-700 text-gray-300 text-xs">
        {title.status_tmdb}
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
                  {title.tipo === 'movie' ? 'Movie' : 'TV Series'}
                </span>

                {percentilNum > 0 && (
                  <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 font-bold text-xs">
                    <span>🔥</span> {percentilNum}% Popularity
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
                    ({title.vote_count_tmdb} votes)
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
                    {title.tipo === 'movie' ? 'Director:' : 'Creator:'}
                  </span>{' '}
                  <strong className="text-gray-200">{title.director || '-'}</strong>
                </div>

                <div>
                  <span className="text-gray-500 font-medium">Writer:</span>{' '}
                  <strong className="text-gray-200">{title.guionista || '-'}</strong>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-gray-500 font-medium">Country:</span>{' '}
                  <CountryFlag code={title.pais} showName={true} />
                </div>

                <div>
                  <span className="text-gray-500 font-medium">Original Language:</span>{' '}
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
                        {gName}
                      </Link>
                    )
                  })}
                </div>
              )}

              {/* 4 Íconos de Acción según el Wireframe */}
              <div className="pt-4 border-t border-gray-800 flex flex-wrap items-center gap-3">
                {/* 1. Botón Favorito ❤️ */}
                <button
                  onClick={handleFavoriteToggle}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                    isFavorite
                      ? 'bg-rose-900/40 border-rose-500 text-rose-300 shadow-md'
                      : 'bg-gray-900 border-gray-700 text-gray-300 hover:bg-rose-950/30 hover:border-rose-500/40 hover:text-rose-300'
                  }`}
                >
                  <Heart className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
                  <span>Favorito</span>
                </button>

                {/* 2. Botón Visto 👁️ */}
                <button
                  onClick={handleWatchedToggle}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                    userEstado === 'vista'
                      ? 'bg-emerald-900/40 border-emerald-500 text-emerald-300 shadow-md'
                      : 'bg-gray-900 border-gray-700 text-gray-300 hover:bg-emerald-950/30 hover:border-emerald-500/40 hover:text-emerald-300'
                  }`}
                >
                  <Eye className="w-4 h-4" />
                  <span>{userEstado === 'vista' ? 'Vista' : 'Marcar Vista'}</span>
                </button>

                {/* 3 & 4. Lógica de Series: Siguiendo ▶️ / Abandonar ❌ vs Watchlist 🔖 */}
                {title.tipo === 'tv' ? (
                  <>
                    {userEstado === 'siguiendo' && (
                      <>
                        {/* Badge Siguiendo (no interactuable / activo) */}
                        <span className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-blue-900/40 border border-blue-500 text-blue-300 cursor-default shadow-md">
                          <Play className="w-4 h-4 fill-current" />
                          <span>Siguiendo</span>
                        </span>

                        {/* Botón Abandonar serie ❌ */}
                        <button
                          onClick={handleUnfollow}
                          title="Abandonar serie conservando episodios vistos"
                          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-red-950/40 border border-red-700/80 text-red-300 hover:bg-red-900/50 hover:border-red-500 transition-all"
                        >
                          <X className="w-4 h-4" />
                          <span>Abandonar</span>
                        </button>
                      </>
                    )}

                    {userEstado === 'abandonada' && (
                      <span className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-gray-900 border border-gray-700 text-gray-400">
                        <X className="w-4 h-4 text-red-400" />
                        <span>Serie Abandonada</span>
                      </span>
                    )}

                    {/* Si no está siguiendo ni en vista ni abandonada, se muestra Watchlist */}
                    {userEstado !== 'siguiendo' && userEstado !== 'vista' && userEstado !== 'abandonada' && (
                      <button
                        onClick={handleWatchlistToggle}
                        className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                          userEstado === 'watchlist'
                            ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-md'
                            : 'bg-[#141414] border-[#262626] text-gray-300 hover:bg-amber-500/10 hover:border-amber-500/40 hover:text-amber-300'
                        }`}
                      >
                        <Bookmark className={`w-4 h-4 ${userEstado === 'watchlist' ? 'fill-current' : ''}`} />
                        <span>Watchlist</span>
                      </button>
                    )}
                  </>
                ) : (
                  /* Para Películas: Watchlist estándar */
                  <button
                    onClick={handleWatchlistToggle}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                      userEstado === 'watchlist'
                        ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-md'
                        : 'bg-[#141414] border-[#262626] text-gray-300 hover:bg-amber-500/10 hover:border-amber-500/40 hover:text-amber-300'
                    }`}
                  >
                    <Bookmark className={`w-4 h-4 ${userEstado === 'watchlist' ? 'fill-current' : ''}`} />
                    <span>Watchlist</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Contenido Detallado */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
        {/* Sinopsis */}
        {title.sinopsis && (
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">Sinopsis</h2>
            <p className="text-sm sm:text-base text-gray-300 leading-relaxed max-w-4xl">
              {title.sinopsis}
            </p>
          </section>
        )}

        {/* Elenco Principal */}
        {title.elenco && title.elenco.length > 0 && (
          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white tracking-tight">Reparto Principal</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {title.elenco.slice(0, 12).map((actor) => (
                <Link
                  key={actor.actor_id}
                  to={`/catalog?actor=${encodeURIComponent(actor.nombre)}`}
                  className="flex flex-col items-center p-3 rounded-xl bg-[#141414] border border-[#262626] hover:border-amber-500/40 transition-colors text-center group"
                >
                  <div className="w-16 h-16 rounded-full overflow-hidden mb-2 bg-[#1c1c1c] border border-[#262626] flex items-center justify-center text-gray-500">
                    <UserIcon className="w-7 h-7" />
                  </div>
                  <span className="text-xs font-semibold text-gray-200 group-hover:text-amber-400 transition-colors line-clamp-1">
                    {actor.nombre}
                  </span>
                  {actor.personaje && (
                    <span className="text-[11px] text-gray-400 line-clamp-1 mt-0.5">
                      {actor.personaje}
                    </span>
                  )}
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Acordeón y Gestión de Temporadas / Episodios (Solo Series) */}
        {title.tipo === 'tv' && title.temporadas && title.temporadas.length > 0 && (
          <section className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <Tv className="w-5 h-5 text-amber-400" /> Seasons & Episodes
              </h2>

              {/* Selector de Temporadas Híbrido: Tabs si <= 5 temporadas, Combobox con stepper si > 5 */}
              {title.temporadas.length <= 5 ? (
                <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
                  {title.temporadas.map((t) => {
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
                        <span>Season {t.numero}</span>
                        {t.temporada_vista && (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-500 text-black uppercase font-extrabold">
                            WATCHED
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
                      {title.temporadas.map((t) => (
                        <option key={t.id} value={t.numero} className="bg-[#141414] text-white">
                          Season {t.numero} {t.temporada_vista ? '— ✓ WATCHED' : `(${t.episodios_vistos || 0}/${t.cantidad_episodios})`}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="w-4 h-4 text-gray-400 absolute right-2.5 pointer-events-none" />
                  </div>

                  {/* Botones de navegación rápida anterior / siguiente */}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => {
                        const seasons = title.temporadas.map((t) => t.numero)
                        const currIdx = seasons.indexOf(selectedSeason)
                        if (currIdx > 0) setSelectedSeason(seasons[currIdx - 1])
                      }}
                      disabled={selectedSeason === title.temporadas[0].numero}
                      title="Temporada anterior"
                      className="p-2 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        const seasons = title.temporadas.map((t) => t.numero)
                        const currIdx = seasons.indexOf(selectedSeason)
                        if (currIdx < seasons.length - 1) setSelectedSeason(seasons[currIdx + 1])
                      }}
                      disabled={selectedSeason === title.temporadas[title.temporadas.length - 1].numero}
                      title="Temporada siguiente"
                      className="p-2 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Notificación de aviso al usuario (ej. episodio futuro) */}
            {episodeNotice && (
              <div className="p-3.5 rounded-xl bg-amber-950/60 border border-amber-600/60 text-amber-200 text-xs flex items-center gap-2.5 animate-fadeIn shadow-lg">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>{episodeNotice}</span>
              </div>
            )}

            {/* Cabecera y botón de temporada completa */}
            {currentSeasonData && (
              <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Temporada {currentSeasonData.numero} ({currentSeasonData.cantidad_episodios} episodios)
                  </h3>
                  {currentSeasonData.sinopsis && (
                    <p className="text-xs text-gray-400 mt-1 max-w-3xl leading-relaxed">
                      {currentSeasonData.sinopsis}
                    </p>
                  )}
                </div>

                <button
                  onClick={() => handleToggleSeasonWatched(currentSeasonData.numero)}
                  disabled={seasonWatchLoading}
                  className={`shrink-0 flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                    currentSeasonData.temporada_vista
                      ? 'bg-emerald-950/80 border-emerald-500/70 text-emerald-300'
                      : 'bg-gray-800/80 border-gray-700 text-gray-300 hover:bg-emerald-950/40 hover:border-emerald-600 hover:text-emerald-300'
                  }`}
                >
                  <CheckCheck className="w-4 h-4" />
                  <span>
                    {currentSeasonData.temporada_vista
                      ? 'Temporada Vista'
                      : 'Marcar toda la temporada'}
                  </span>
                </button>
              </div>
            )}

            {/* Lista de Episodios de la Temporada Seleccionada */}
            {currentSeasonData && currentSeasonData.episodios && (
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
                              ? 'Marcar como no visto'
                              : isUnreleased
                              ? `No estrenado (estreno: ${ep.fecha_estreno})`
                              : 'Marcar como visto'
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
                                <Clock className="w-3 h-3" /> No estrenado
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-3 text-[11px] text-gray-500">
                            {ep.fecha_estreno ? (
                              <span className={isUnreleased ? 'text-amber-400/80 font-medium' : ''}>
                                Estreno: {ep.fecha_estreno}
                              </span>
                            ) : (
                              <span>Estreno: -</span>
                            )}
                            <span>• {ep.duracion && ep.duracion > 0 ? `${ep.duracion} min` : '-'}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </section>
        )}

        {/* Sección de Reseñas */}
        <section className="space-y-6 pt-6 border-t border-gray-800">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-amber-400" /> Reviews & Opinions
            </h2>
            <span className="text-xs text-gray-400">{reviews.length} reviews</span>
          </div>

          {/* Formulario de nueva reseña */}
          {user ? (
            <form
              onSubmit={handleReviewSubmit}
              className="p-5 rounded-2xl bg-[#141414] border border-[#262626] space-y-4"
            >
              <h3 className="text-xs font-semibold text-gray-200 uppercase tracking-wider">
                Leave your review
              </h3>

              {reviewSuccess && (
                <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/80 text-xs text-emerald-300">
                  Your review was published successfully and unified rating has been updated!
                </div>
              )}

              <div className="flex items-center gap-3">
                <label className="text-xs text-gray-400">Rating:</label>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((star) => (
                    <button
                      type="button"
                      key={star}
                      onClick={() => setNewReviewRating(star)}
                      className="p-1 focus:outline-none"
                    >
                      <Star
                        className={`w-4 h-4 ${
                          star <= newReviewRating
                            ? 'fill-amber-400 text-amber-400'
                            : 'text-gray-600'
                        }`}
                      />
                    </button>
                  ))}
                  <span className="text-xs font-bold text-amber-400 ml-2">
                    {newReviewRating}/10
                  </span>
                </div>
              </div>

              <textarea
                required
                rows={3}
                value={newReviewText}
                onChange={(e) => setNewReviewText(e.target.value)}
                placeholder="What did you think of this title? Share your thoughts without spoilers..."
                className="w-full p-3 text-sm bg-[#0d0d0d] border border-[#262626] rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
              />

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={submittingReview}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  {submittingReview ? 'Publishing...' : 'Post Review'}
                </button>
              </div>
            </form>
          ) : (
            <div className="p-6 rounded-2xl bg-[#141414] border border-[#262626] text-center space-y-2">
              <p className="text-xs text-gray-400">Sign in to rate and leave a review.</p>
              <button
                onClick={openAuth}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md transition-all"
              >
                Sign In to Review
              </button>
            </div>
          )}

          {/* Listado de reseñas */}
          <div className="space-y-4">
            {reviews.length === 0 ? (
              <p className="text-xs text-gray-500 italic">No reviews for this title yet. Be the first to share your thoughts!</p>
            ) : (
              reviews.map((rev) => (
                <div
                  key={rev.id}
                  className="p-4 rounded-xl bg-[#141414] border border-[#262626] space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-xs font-bold text-amber-300">
                        {rev.nombre_usuario ? rev.nombre_usuario.charAt(0).toUpperCase() : rev.autor_tmdb ? rev.autor_tmdb.charAt(0).toUpperCase() : 'U'}
                      </div>
                      <span className="text-xs font-semibold text-gray-200">
                        {rev.nombre_usuario || rev.autor_tmdb || 'User'}
                      </span>
                      {rev.autor_tmdb && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#202020] text-amber-400/90 border border-amber-500/30 font-semibold">
                          TMDB
                        </span>
                      )}
                    </div>

                    {rev.puntaje && (
                      <div className="flex items-center gap-1 text-yellow-400 text-xs font-bold">
                        <Star className="w-3 h-3 fill-current" />
                        <span>{rev.puntaje}</span>
                      </div>
                    )}
                  </div>

                  <p className="text-xs sm:text-sm text-gray-300 leading-relaxed">{rev.texto}</p>
                  <span className="text-[10px] text-gray-500 block">
                    {rev.fecha ? new Date(rev.fecha).toLocaleDateString() : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
