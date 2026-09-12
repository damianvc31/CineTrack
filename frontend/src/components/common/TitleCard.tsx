import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Star, Heart, Bookmark, Eye, Play, X } from 'lucide-react'
import type { TitleCard as TitleCardType } from '@/types/catalog'
import { catalogService } from '@/services/catalogService'
import { useAuth } from '@/context/AuthContext'
import posterFallback from '@/assets/placeholders/poster-empty.svg'
import { CountryFlag } from '@/components/common/CountryFlag'

interface TitleCardProps {
  title: TitleCardType
  onStateChange?: (action: 'favorite' | 'watchlist' | 'watched', titleId: number) => void
  onOpenAuth?: () => void
}

export const TitleCard: React.FC<TitleCardProps> = ({ title, onStateChange, onOpenAuth }) => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [imgError, setImgError] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const [isFavorite, setIsFavorite] = useState(title.user_favorito ?? false)
  const [userEstado, setUserEstado] = useState(title.user_estado ?? null)

  React.useEffect(() => {
    setIsFavorite(title.user_favorito ?? false)
    setUserEstado(title.user_estado ?? null)
  }, [title.user_favorito, title.user_estado])

  // Formato para series: "N seasons | AAAA-AAAA" (el último año se omite si la serie está en curso)
  let subInfo = ''
  if (title.tipo === 'tv') {
    const seasonsCount = title.total_seasons || 1
    const seasonsText = `${seasonsCount} ${seasonsCount === 1 ? 'season' : 'seasons'}`
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
      } else if (action === 'watchlist') {
        const res = await catalogService.toggleWatchlist(title.id)
        setUserEstado(res.nuevo_estado ?? null)
      } else if (action === 'watched') {
        const res = await catalogService.toggleWatched(title.id)
        setUserEstado(res.nuevo_estado ?? null)
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
          <div className="absolute top-2 left-2 z-10 flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-black/80 backdrop-blur-md border border-[#333333] text-[10px] font-bold text-amber-400 shadow-md">
            <span>🔥</span>
            <span>{percentilNum}</span>
          </div>
        )}

        {/* Barra inferior de acciones (❤️ 👁 🔖) pegada al pie del póster */}
        <div className="absolute inset-x-0 bottom-0 py-1.5 px-2 bg-gradient-to-t from-black/95 via-black/80 to-transparent flex items-center justify-around gap-1 z-10">
          {/* Botón Favorito */}
          <button
            onClick={(e) => handleQuickAction(e, 'favorite')}
            disabled={isUpdating}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
            className={`p-1.5 rounded-full transition-all ${
              isFavorite
                ? 'text-red-500 bg-red-500/20'
                : 'text-gray-400 hover:text-red-400 hover:bg-black/60'
            }`}
          >
            <Heart className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
          </button>

          {/* Botón Visto */}
          <button
            onClick={(e) => handleQuickAction(e, 'watched')}
            disabled={isUpdating}
            title={isWatched ? 'Mark as unwatched' : 'Mark as watched'}
            className={`p-1.5 rounded-full transition-all ${
              isWatched
                ? 'text-amber-400 bg-amber-400/20'
                : 'text-gray-400 hover:text-amber-400 hover:bg-black/60'
            }`}
          >
            <Eye className={`w-4 h-4 ${isWatched ? 'fill-current' : ''}`} />
          </button>

          {/* Botón Watchlist / Siguiendo / Abandonada */}
          {isSiguiendo ? (
            <span
              title="Following series"
              className="p-1.5 rounded-full text-blue-400 bg-blue-500/20"
            >
              <Play className="w-4 h-4 fill-current" />
            </span>
          ) : isAbandonada ? (
            <span
              title="Dropped series - Click to view details and resume"
              className="p-1.5 rounded-full text-red-400 bg-red-500/20 hover:bg-red-500/30 transition-colors"
            >
              <X className="w-4 h-4" />
            </span>
          ) : !isWatched ? (
            <button
              onClick={(e) => handleQuickAction(e, 'watchlist')}
              disabled={isUpdating}
              title={isWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
              className={`p-1.5 rounded-full transition-all ${
                isWatchlist
                  ? 'text-amber-400 bg-amber-400/20'
                  : 'text-gray-400 hover:text-white hover:bg-black/60'
              }`}
            >
              <Bookmark className={`w-4 h-4 ${isWatchlist ? 'fill-current' : ''}`} />
            </button>
          ) : null}
        </div>
      </div>

      {/* Info Card Body */}
      <div className="p-2.5 flex flex-col justify-between flex-1 gap-1">
        <h3
          title={title.nombre}
          className="text-xs sm:text-sm font-bold text-white group-hover:text-amber-400 transition-colors line-clamp-1"
        >
          {title.nombre}
        </h3>

        <div className="flex items-center justify-between text-[11px] text-gray-400 gap-1">
          <div className="flex items-center gap-1 min-w-0 flex-1">
            <CountryFlag code={title.pais} />
            <span className="text-gray-600 text-[10px]">•</span>
            <span className="truncate text-[10px] tracking-tight">{subInfo || '-'}</span>
          </div>

          {title.vote_average_tmdb > 0 && (
            <div className="flex items-center gap-1 text-amber-400 font-semibold shrink-0 text-[11px]">
              <Star className="w-3 h-3 fill-amber-400" />
              <span>{title.vote_average_tmdb.toFixed(1)}</span>
              {title.vote_count_tmdb > 0 && (
                <span className="text-[9px] text-gray-500 font-normal">
                  ({title.vote_count_tmdb >= 1000 ? `${(title.vote_count_tmdb / 1000).toFixed(1)}k` : title.vote_count_tmdb})
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
