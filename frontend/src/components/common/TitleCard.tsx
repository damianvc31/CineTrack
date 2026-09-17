import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Star, Heart, Bookmark, Eye, EyeOff, Play, X } from 'lucide-react'
import type { TitleCard as TitleCardType } from '@/types/catalog'
import { catalogService } from '@/services/catalogService'
import { useAuth } from '@/context/AuthContext'
import posterFallback from '@/assets/placeholders/poster-empty.svg'
import { CountryFlag } from '@/components/common/CountryFlag'
import { SeasonProgressBar } from '@/components/profile/SeasonProgressBar'
import { useLanguage } from '@/context/LanguageContext'

interface TitleCardProps {
  title: TitleCardType
  onStateChange?: (action: 'favorite' | 'watchlist' | 'watched', titleId: number) => void
  onOpenAuth?: (mode?: 'login' | 'register') => void
}

export const TitleCard: React.FC<TitleCardProps> = ({ title, onStateChange, onOpenAuth }) => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { language } = useLanguage()
  const [imgError, setImgError] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const [isFavorite, setIsFavorite] = useState(title.user_favorito ?? false)
  const [userEstado, setUserEstado] = useState(title.user_estado ?? null)

  // Estados de hover y supresión de inversión inmediata post-click
  const [isFavHovered, setIsFavHovered] = useState(false)
  const [justToggledFav, setJustToggledFav] = useState(false)

  const [isWlHovered, setIsWlHovered] = useState(false)
  const [justToggledWl, setJustToggledWl] = useState(false)

  const [isWatchedHovered, setIsWatchedHovered] = useState(false)
  const [justToggledWatched, setJustToggledWatched] = useState(false)

  React.useEffect(() => {
    setIsFavorite(title.user_favorito ?? false)
    setUserEstado(title.user_estado ?? null)
  }, [title.user_favorito, title.user_estado])

  // Formato para series: "N temporadas | AAAA-AAAA" (el último año se omite si la serie está en curso)
  let subInfo = ''
  if (title.tipo === 'tv') {
    const seasonsCount = title.total_seasons || 1
    const seasonWord = language === 'es'
      ? (seasonsCount === 1 ? 'temporada' : 'temporadas')
      : (seasonsCount === 1 ? 'season' : 'seasons')
    const seasonsText = `${seasonsCount} ${seasonWord}`
    const startYear = title.anio_estreno || (title.fecha_estreno ? title.fecha_estreno.substring(0, 4) : '')
    const endYear = title.anio_fin || (title.fecha_fin ? title.fecha_fin.substring(0, 4) : '')
    const yearPart = endYear ? `${startYear}-${endYear}` : `${startYear}-`
    subInfo = `${seasonsText} | ${yearPart}`
  } else {
    // Películas: solo año de estreno simple
    subInfo = title.anio_estreno?.toString() || (title.fecha_estreno ? title.fecha_estreno.substring(0, 4) : '')
  }

  // Imagen de portada
  const imagenUrl = imgError || (!title.portada_url && !title.poster_url)
    ? posterFallback
    : (title.portada_url || title.poster_url)!

  // Popularidad en porcentaje (backend devuelve 0.0 a 1.0)
  const percentilNum =
    title.popularidad_percentil > 1
      ? Math.round(title.popularidad_percentil)
      : Math.round(title.popularidad_percentil * 100)

  const handleCardClick = () => {
    navigate(`/titles/${title.id}`)
  }

  const handleQuickAction = async (e: React.MouseEvent, action: 'favorite' | 'watchlist' | 'watched') => {
    e.stopPropagation()
    if (!user) {
      if (onOpenAuth) onOpenAuth()
      return
    }

    setIsUpdating(true)
    try {
      if (action === 'favorite') {
        const res = await catalogService.toggleFavorite(title.id)
        setIsFavorite(res.favorito)
        setJustToggledFav(true)
      } else if (action === 'watchlist') {
        const res = await catalogService.toggleWatchlist(title.id)
        setUserEstado(res.nuevo_estado ?? null)
        setJustToggledWl(true)
      } else if (action === 'watched') {
        const res = await catalogService.toggleWatched(title.id)
        setUserEstado(res.nuevo_estado ?? null)
        setJustToggledWatched(true)
      }
      if (onStateChange) onStateChange(action, title.id)
    } catch (err) {
      console.error('Error al actualizar estado:', err)
    } finally {
      setIsUpdating(false)
    }
  }

  const isWatched = userEstado === 'vista'
  const isSiguiendo = userEstado === 'siguiendo'
  const isWatchlist = userEstado === 'watchlist'
  const isAbandonada = userEstado === 'abandonada'

  const favUnfilled = isFavorite && isFavHovered && !justToggledFav
  const wlUnfilled = isWatchlist && isWlHovered && !justToggledWl

  const effectiveHoverWatched = isWatchedHovered && !justToggledWatched
  const showingWatched = effectiveHoverWatched ? !isWatched : isWatched

  return (
    <div
      onClick={handleCardClick}
      className="group relative flex flex-col rounded-2xl overflow-hidden bg-[#141414] border border-[#262626] hover:border-[#3a3a3a] transition-all duration-300 cursor-pointer select-none shrink-0 w-36 sm:w-44 md:w-48 lg:w-52 shadow-lg"
    >
      {/* Contenedor del Póster (Aspect Ratio 2:3) */}
      <div className="relative aspect-[2/3] w-full overflow-hidden bg-[#181818]">
        <img
          src={imagenUrl}
          alt={title.nombre}
          loading="lazy"
          onError={() => setImgError(true)}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
        />

        {/* Badge Popularidad (🔥 xx%) */}
        {percentilNum > 0 && (
          <div
            title={language === 'es' ? `Percentil de popularidad: ${percentilNum}%` : `Popularity percentile: ${percentilNum}%`}
            className="absolute top-2 left-2 z-10 flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-black/80 backdrop-blur-md border border-[#333333] text-[10px] font-bold text-amber-400 shadow-md cursor-default"
          >
            <span>🔥</span>
            <span>{percentilNum}</span>
          </div>
        )}

        {/* Badges de Ratings (Calificación de la Comunidad arriba, Puntaje Personal del usuario justo debajo) */}
        <div className="absolute top-2 right-2 z-10 flex flex-col items-end gap-1">
          {title.vote_average_tmdb > 0 && (
            <div
              title={
                language === 'es'
                  ? `Calificación de la comunidad: ${title.vote_average_tmdb.toFixed(1)}${title.vote_count_tmdb > 0 ? ` (${title.vote_count_tmdb} votos)` : ''}`
                  : `Community rating: ${title.vote_average_tmdb.toFixed(1)}${title.vote_count_tmdb > 0 ? ` (${title.vote_count_tmdb} votes)` : ''}`
              }
              className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-black/80 backdrop-blur-md border border-[#333333] text-[10px] font-bold text-amber-400 shadow-md cursor-default"
            >
              <Star className="w-2.5 h-2.5 fill-amber-400 text-amber-400" />
              <span>{title.vote_average_tmdb.toFixed(1)}</span>
              {title.vote_count_tmdb > 0 && (
                <span className="text-[9px] text-amber-200/70 font-normal">
                  ({title.vote_count_tmdb >= 1000 ? `${(title.vote_count_tmdb / 1000).toFixed(1)}k` : title.vote_count_tmdb})
                </span>
              )}
            </div>
          )}

          {title.user_rating != null && (
            <div
              title={`${language === 'es' ? 'Tu puntaje' : 'Your score'}: ${title.user_rating.toFixed(1)}`}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-black/80 backdrop-blur-md border border-sky-500/50 text-[10px] font-bold text-sky-400 shadow-md cursor-default"
            >
              <Star className="w-2.5 h-2.5 fill-sky-400 text-sky-400" />
              <span>{title.user_rating.toFixed(1)}</span>
            </div>
          )}
        </div>

        {/* Barra inferior de acciones (❤️ 👁 🔖) pegada al pie del póster */}
        <div className="absolute inset-x-0 bottom-0 py-1.5 px-2 bg-gradient-to-t from-black/95 via-black/80 to-transparent flex items-center justify-around gap-1 z-10">
          {/* Botón Favorito con hover de desrellenado y supresión post-click */}
          <button
            onClick={(e) => handleQuickAction(e, 'favorite')}
            onMouseEnter={() => setIsFavHovered(true)}
            onMouseLeave={() => {
              setIsFavHovered(false)
              setJustToggledFav(false)
            }}
            disabled={isUpdating}
            title={
              isFavorite
                ? (language === 'es' ? 'Quitar de favoritos' : 'Remove from favorites')
                : (language === 'es' ? 'Agregar a favoritos' : 'Add to favorites')
            }
            className={`p-1.5 rounded-full transition-all ${
              isFavorite
                ? 'text-red-500 bg-red-500/20 hover:bg-red-500/30'
                : 'text-gray-400 hover:text-red-400 hover:bg-black/60'
            }`}
          >
            <Heart className={`w-4 h-4 transition-all ${isFavorite && !favUnfilled ? 'fill-current' : ''}`} />
          </button>

          {/* Botón Visto con inversión dinámica en hover y supresión post-click */}
          <button
            onClick={(e) => handleQuickAction(e, 'watched')}
            onMouseEnter={() => setIsWatchedHovered(true)}
            onMouseLeave={() => {
              setIsWatchedHovered(false)
              setJustToggledWatched(false)
            }}
            disabled={isUpdating}
            title={
              isWatched
                ? (language === 'es' ? 'Marcar como no vista' : 'Mark as unwatched')
                : (language === 'es' ? 'Marcar como vista' : 'Mark as watched')
            }
            className={`p-1.5 rounded-full transition-all ${
              showingWatched
                ? 'text-emerald-400 bg-emerald-500/20 border border-emerald-500/40 hover:bg-emerald-500/30'
                : isWatched && effectiveHoverWatched
                ? 'text-emerald-300 bg-[#18261e] border border-emerald-600/70'
                : effectiveHoverWatched
                ? 'text-emerald-300 bg-emerald-950/40 border border-emerald-500/40'
                : 'text-gray-400 hover:text-emerald-400 hover:bg-black/60'
            }`}
          >
            {showingWatched ? (
              <Eye className="w-4 h-4 stroke-[2.2]" />
            ) : (
              <EyeOff className={`w-4 h-4 ${isWatched && effectiveHoverWatched ? 'text-emerald-300' : ''}`} />
            )}
          </button>

          {/* Botón Watchlist / Siguiendo / Abandonada */}
          {isSiguiendo ? (
            <span
              title={language === 'es' ? 'Siguiendo serie' : 'Following series'}
              className="p-1.5 rounded-full text-blue-400 bg-blue-500/20"
            >
              <Play className="w-4 h-4 fill-current" />
            </span>
          ) : isAbandonada ? (
            <span
              title={language === 'es' ? 'Serie abandonada — Click para ver detalles y reanudar' : 'Dropped series — Click to view details and resume'}
              className="p-1.5 rounded-full text-red-400 bg-red-500/20 hover:bg-red-500/30 transition-colors"
            >
              <X className="w-4 h-4" />
            </span>
          ) : !isWatched ? (
            <button
              onClick={(e) => handleQuickAction(e, 'watchlist')}
              onMouseEnter={() => setIsWlHovered(true)}
              onMouseLeave={() => {
                setIsWlHovered(false)
                setJustToggledWl(false)
              }}
              disabled={isUpdating}
              title={
                isWatchlist
                  ? (language === 'es' ? 'Quitar de lista de seguimiento' : 'Remove from watchlist')
                  : (language === 'es' ? 'Agregar a lista de seguimiento' : 'Add to watchlist')
              }
              className={`p-1.5 rounded-full transition-all ${
                isWatchlist
                  ? 'text-amber-400 bg-amber-400/20 hover:bg-amber-400/30'
                  : 'text-gray-400 hover:text-white hover:bg-black/60'
              }`}
            >
              <Bookmark className={`w-4 h-4 transition-all ${isWatchlist && !wlUnfilled ? 'fill-current' : ''}`} />
            </button>
          ) : null}
        </div>
      </div>

      {/* Info Card Body */}
      <div className="p-2.5 flex flex-col justify-between flex-1 gap-1">
        <div className="relative group/title">
          <h3
            aria-label={title.nombre}
            className="text-xs sm:text-sm font-bold text-white group-hover:text-amber-400 transition-colors line-clamp-1"
          >
            {title.nombre}
          </h3>
          {/* Tooltip instantáneo para títulos largos */}
          <div className="absolute left-0 bottom-full mb-1.5 hidden group-hover/title:block z-30 px-2.5 py-1 bg-[#171717]/95 backdrop-blur-md border border-[#383838] rounded-lg shadow-2xl text-xs font-semibold text-amber-200 whitespace-normal max-w-[220px] pointer-events-none animate-in fade-in zoom-in-95 duration-150">
            {title.nombre}
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 min-w-0">
          <CountryFlag code={title.pais} />
          <span className="text-gray-600 text-[10px]">•</span>
          <span className="truncate text-[10px] sm:text-[11px] tracking-tight text-gray-300 font-medium">
            {subInfo || '-'}
          </span>
        </div>

        {title.seasons_progress && title.seasons_progress.length > 0 && (
          <div className="pt-1.5 border-t border-[#262626]">
            <SeasonProgressBar
              seasons={title.seasons_progress}
              statusText={title.following_status_text}
            />
          </div>
        )}
      </div>
    </div>
  )
}
