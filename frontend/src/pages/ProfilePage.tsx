import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Clock,
  Film,
  Tv,
  Flame,
  Star,
  Award,
  PieChart,
  TrendingUp,
  MapPin,
  Pencil,
  AlertCircle,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react'
import { catalogService } from '@/services/catalogService'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import type { UserLibrary, UserStats, TopTitleStatItem, TitleCard } from '@/types/catalog'
import { EditProfileModal } from '@/components/profile/EditProfileModal'
import { SeasonProgressBar } from '@/components/profile/SeasonProgressBar'
import { DonutGenreChart } from '@/components/profile/DonutGenreChart'

export const ProfilePage: React.FC = () => {
  const { user } = useAuth()
  const { t, language } = useLanguage()
  const navigate = useNavigate()

  const [stats, setStats] = useState<UserStats | null>(null)
  const [library, setLibrary] = useState<UserLibrary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsData, libData] = await Promise.all([
        catalogService.getStats(),
        catalogService.getLibrary(),
      ])
      setStats(statsData)
      setLibrary(libData)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Failed to fetch profile information.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!user) {
      navigate('/')
      return
    }
    fetchData()
  }, [user, navigate])

  if (!user) return null

  const formatTitleSubtitle = (item: TopTitleStatItem): string => {
    if (item.tipo === 'tv') {
      const seasons = item.total_seasons
        ? `${item.total_seasons} season${item.total_seasons > 1 ? 's' : ''}`
        : '1 season'
      const years = item.anio_fin && item.anio_fin !== item.anio_estreno
        ? `${item.anio_estreno || '?'}-${item.anio_fin}`
        : `${item.anio_estreno || ''}`
      return `${seasons} | ${years}`
    }
    return item.anio_estreno ? `${item.anio_estreno}` : ''
  }

  const memberSinceText = user.fecha_registro
    ? new Date(user.fecha_registro).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : 'Recently'

  const totalWatchedTitles = (stats?.movies_watched_count || 0) + (stats?.series_watched_count || 0)

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* ========================================================= */}
      {/* TOP SECTION: IDENTITY CARD & STATISTICS PANEL            */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: User Identity Card */}
        <aside className="lg:col-span-4 bg-[#141414] border border-[#262626] rounded-2xl p-6 sm:p-8 space-y-6 text-center lg:text-left relative shadow-xl">
          {/* Avatar Container */}
          <div className="relative mx-auto lg:mx-0 w-32 h-32 sm:w-36 sm:h-36 rounded-full overflow-hidden border-2 border-amber-500/50 bg-[#181818] shadow-2xl flex items-center justify-center group">
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.nombre_usuario}
                className="w-full h-full object-cover"
                onError={(e) => {
                  ;(e.target as HTMLElement).style.display = 'none'
                }}
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-black text-4xl sm:text-5xl font-black">
                {user.nombre_usuario.charAt(0).toUpperCase()}
              </div>
            )}

            {/* Pencil edit button on hover / touch */}
            <button
              onClick={() => setIsEditModalOpen(true)}
              className="absolute inset-0 bg-black/60 backdrop-blur-xs opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center text-amber-400 gap-1 text-xs font-semibold"
              title="Edit Profile"
            >
              <Pencil className="w-5 h-5" />
              <span>Edit</span>
            </button>
          </div>

          {/* User Name & Metadata */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-center lg:justify-start gap-2">
              <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                {user.nombre_usuario}
              </h1>
              {user.es_admin && (
                <span
                  className="p-1 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40"
                  title="Administrator"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400">{t('memberSince')} {memberSinceText}</p>
          </div>

          {/* Bio text */}
          <p className="text-xs text-gray-300 leading-relaxed italic">
            {user.descripcion || (language === 'es' ? 'Amante del cine y las series.' : 'Lover of cinema and series.')}
          </p>

          {/* Location */}
          {(user.ciudad || user.pais) && (
            <div className="flex items-center justify-center lg:justify-start gap-1.5 text-xs font-medium text-gray-400 pt-2 border-t border-[#262626]">
              <MapPin className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              <span>
                {user.ciudad ? `${user.ciudad}, ` : ''}
                {user.pais || ''}
              </span>
            </div>
          )}

          {/* Explicit Edit Button */}
          <button
            onClick={() => setIsEditModalOpen(true)}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl bg-[#1c1c1c] hover:bg-[#252525] border border-[#2f2f2f] text-gray-300 hover:text-white text-xs font-semibold transition-colors"
          >
            <Pencil className="w-3.5 h-3.5 text-amber-400" />
            <span>{t('editProfile')}</span>
          </button>
        </aside>

        {/* Right Column: Statistics Panel */}
        <section className="lg:col-span-8 bg-[#141414] border border-[#262626] rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
            <h2 className="text-xl font-bold text-white tracking-tight">{t('statistics')}</h2>
            <span className="px-2.5 py-1 rounded-full bg-[#1e1e1e] border border-[#2c2c2c] text-[10px] font-bold uppercase tracking-wider text-gray-300">
              {language === 'es' ? 'Histórico' : 'All Time'}
            </span>
          </div>

          {loading ? (
            <div className="py-16 text-center text-xs text-gray-400 animate-pulse">
              {language === 'es' ? 'Cargando métricas de usuario...' : 'Loading user metrics...'}
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 flex items-center gap-3 text-xs text-red-400">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : stats ? (
            <div className="space-y-6">
              {/* Row 1: Top 3 Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* Total Hours */}
                <div className="p-5 rounded-2xl bg-[#0d0d0d] border border-[#262626] space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <Clock className="w-4 h-4 text-amber-500" />
                    <span>{t('totalHours')}</span>
                  </div>
                  <div className="text-3xl sm:text-4xl font-black text-[#f59e0b] pt-1">
                    {Math.round(stats.total_hours)}h
                  </div>
                  <p className="text-[11px] text-gray-400 pt-0.5">
                    {t('moviesLabel')}: {Math.round(stats.movie_hours)}h • {t('seriesLabel')}: {Math.round(stats.tv_hours)}h
                  </p>
                </div>

                {/* Movies Watched */}
                <div className="p-5 rounded-2xl bg-[#0d0d0d] border border-[#262626] space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <Film className="w-4 h-4 text-amber-500" />
                    <span>{t('moviesWatched')}</span>
                  </div>
                  <div className="text-3xl sm:text-4xl font-black text-[#f59e0b] pt-1">
                    {stats.movies_watched_count}
                  </div>
                  <p className="text-[11px] text-gray-400 pt-0.5">
                    {language === 'es' ? 'Promedio' : 'Avg'}: {stats.avg_movies_per_week?.toFixed(1) || '0.0'} {t('avgMoviesPerWeek')}
                  </p>
                </div>

                {/* Series Watched */}
                <div className="p-5 rounded-2xl bg-[#0d0d0d] border border-[#262626] space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <Tv className="w-4 h-4 text-amber-500" />
                    <span>{t('seriesWatched')}</span>
                  </div>
                  <div className="text-3xl sm:text-4xl font-black text-[#f59e0b] pt-1">
                    {stats.series_watched_count}
                  </div>
                  <p className="text-[11px] text-gray-400 pt-0.5">
                    {language === 'es' ? 'Temporadas' : 'Seasons'}: {stats.seasons_completed_count || 0} {t('seasonsCompletedText')}
                  </p>
                </div>
              </div>

              {/* Row 2: Sub-columns */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-2">
                {/* Left Sub-column: Top 5 by Popularity & Genres Watched */}
                <div className="space-y-6">
                  {/* Top 5 by Popularity */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-300">
                      <Flame className="w-4 h-4 text-amber-500" />
                      <span>{t('top5Popularity')}</span>
                    </div>

                    <div className="space-y-2">
                      {stats.top_by_popularity.length > 0 ? (
                        stats.top_by_popularity.map((item, idx) => (
                          <div
                            key={item.id}
                            className="flex items-center justify-between gap-3 p-2 rounded-xl bg-[#0d0d0d] border border-[#1f1f1f] text-xs hover:border-[#333333] transition-colors"
                          >
                            <div className="relative group/rank flex items-center gap-2.5 min-w-0 flex-1">
                              <span className="text-[11px] font-bold text-gray-500 w-4 text-right shrink-0">
                                {idx + 1}
                              </span>
                              <Link
                                to={`/titles/${item.id}`}
                                aria-label={item.nombre}
                                className="font-semibold text-gray-200 hover:text-amber-400 transition-colors truncate"
                              >
                                {item.nombre}
                                <span className="text-[11px] font-normal text-gray-400 ml-1.5">
                                  · {formatTitleSubtitle(item)}
                                </span>
                              </Link>
                              {/* Floating instant tooltip */}
                              <div className="absolute left-6 bottom-full mb-1 hidden group-hover/rank:block z-30 px-2.5 py-1 bg-[#171717]/95 backdrop-blur-md border border-[#383838] rounded-lg shadow-2xl text-xs font-semibold text-amber-200 whitespace-normal max-w-[240px] pointer-events-none animate-in fade-in zoom-in-95 duration-150">
                                {item.nombre} <span className="text-[10px] text-gray-400 block font-normal">· {formatTitleSubtitle(item)}</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-1 text-emerald-400 text-[11px] font-bold shrink-0">
                              <TrendingUp className="w-3 h-3" />
                              <span>{Math.round(item.metric_value > 1 ? item.metric_value : item.metric_value * 100)}%</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-500 italic">{t('noWatchedTitles')}</p>
                      )}
                    </div>
                  </div>

                  <div className="border-t border-[#262626]" />

                  {/* Genres Watched Donut Chart */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-300">
                      <PieChart className="w-4 h-4 text-amber-500" />
                      <span>{t('genresWatched')}</span>
                    </div>

                    <DonutGenreChart
                      genresDistribution={stats.genres_distribution}
                      totalTitles={totalWatchedTitles}
                      lang={language}
                    />
                  </div>
                </div>

                {/* Right Sub-column: Community Rating & Personal Rating */}
                <div className="space-y-6">
                  {/* Top 5 by Average Rating */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-300">
                      <Award className="w-4 h-4 text-amber-500" />
                      <span>{t('top5Rating')}</span>
                    </div>

                    <div className="space-y-2">
                      {stats.top_by_community_rating.length > 0 ? (
                        stats.top_by_community_rating.map((item, idx) => (
                          <div
                            key={item.id}
                            className="flex items-center justify-between gap-3 p-2 rounded-xl bg-[#0d0d0d] border border-[#1f1f1f] text-xs hover:border-[#333333] transition-colors"
                          >
                            <div className="relative group/rank flex items-center gap-2.5 min-w-0 flex-1">
                              <span className="text-[11px] font-bold text-gray-500 w-4 text-right shrink-0">
                                {idx + 1}
                              </span>
                              <Link
                                to={`/titles/${item.id}`}
                                aria-label={item.nombre}
                                className="font-semibold text-gray-200 hover:text-amber-400 transition-colors truncate"
                              >
                                {item.nombre}
                                <span className="text-[11px] font-normal text-gray-400 ml-1.5">
                                  · {formatTitleSubtitle(item)}
                                </span>
                              </Link>
                              {/* Floating instant tooltip */}
                              <div className="absolute left-6 bottom-full mb-1 hidden group-hover/rank:block z-30 px-2.5 py-1 bg-[#171717]/95 backdrop-blur-md border border-[#383838] rounded-lg shadow-2xl text-xs font-semibold text-amber-200 whitespace-normal max-w-[240px] pointer-events-none animate-in fade-in zoom-in-95 duration-150">
                                {item.nombre} <span className="text-[10px] text-gray-400 block font-normal">· {formatTitleSubtitle(item)}</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-1 text-amber-400 text-[11px] font-bold shrink-0">
                              <Star className="w-3 h-3 fill-amber-400" />
                              <span>{item.metric_value.toFixed(1)}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-500 italic">{t('noWatchedTitles')}</p>
                      )}
                    </div>
                  </div>

                  {/* Top 5 by My Rating (Personal verified scores) */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-300">
                      <Star className="w-4 h-4 text-amber-500 fill-amber-500/20" />
                      <span>{t('top5MyRating')}</span>
                    </div>

                    <div className="space-y-2">
                      {stats.top_by_user_rating.length > 0 ? (
                        stats.top_by_user_rating.map((item, idx) => (
                          <div
                            key={item.id}
                            className="flex items-center justify-between gap-3 p-2 rounded-xl bg-[#0d0d0d] border border-[#1f1f1f] text-xs hover:border-[#333333] transition-colors"
                          >
                            <div className="relative group/rank flex items-center gap-2.5 min-w-0 flex-1">
                              <span className="text-[11px] font-bold text-gray-500 w-4 text-right shrink-0">
                                {idx + 1}
                              </span>
                              <Link
                                to={`/titles/${item.id}`}
                                aria-label={item.nombre}
                                className="font-semibold text-gray-200 hover:text-amber-400 transition-colors truncate"
                              >
                                {item.nombre}
                                <span className="text-[11px] font-normal text-gray-400 ml-1.5">
                                  · {formatTitleSubtitle(item)}
                                </span>
                              </Link>
                              {/* Floating instant tooltip */}
                              <div className="absolute left-6 bottom-full mb-1 hidden group-hover/rank:block z-30 px-2.5 py-1 bg-[#171717]/95 backdrop-blur-md border border-[#383838] rounded-lg shadow-2xl text-xs font-semibold text-amber-200 whitespace-normal max-w-[240px] pointer-events-none animate-in fade-in zoom-in-95 duration-150">
                                {item.nombre} <span className="text-[10px] text-gray-400 block font-normal">· {formatTitleSubtitle(item)}</span>
                              </div>
                            </div>

                            <div className="flex items-center gap-1 text-amber-400 text-[11px] font-bold shrink-0">
                              <Star className="w-3 h-3 fill-amber-400" />
                              <span>{item.metric_value.toFixed(1)}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-500 italic">
                          {t('noRatedTitles')}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      </div>

      {/* ========================================================= */}
      {/* SECTION 2: FOLLOWING (FULL WIDTH ROW)                     */}
      {/* ========================================================= */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <h2 className="text-xl font-bold text-white">{t('following')}</h2>
            <span className="text-xs font-semibold text-gray-500">
              ({library?.following.length || 0})
            </span>
          </div>

          <Link
            to="/library?tab=siguiendo"
            className="flex items-center gap-1 text-xs font-bold text-amber-500 hover:text-amber-400 transition-colors"
          >
            <span>{t('viewAll')}</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {library && library.following.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {library.following.slice(0, 3).map((item) => (
              <div
                key={item.id}
                className="group relative rounded-2xl bg-[#141414] border border-[#262626] overflow-hidden hover:border-amber-500/40 transition-all flex flex-col shadow-lg"
              >
                {/* Backdrop / Landscape image */}
                <Link to={`/titles/${item.id}`} className="relative aspect-video w-full overflow-hidden bg-[#1c1c1c] block">
                  {item.portada_url ? (
                    <img
                      src={item.portada_url}
                      alt={item.nombre}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-600">
                      <Tv className="w-10 h-10" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-[#141414] via-transparent to-transparent" />
                </Link>

                {/* Info & Progress */}
                <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
                  <Link
                    to={`/titles/${item.id}`}
                    className="text-sm font-bold text-white group-hover:text-amber-400 transition-colors truncate block"
                  >
                    {item.nombre}
                  </Link>

                  <SeasonProgressBar
                    seasons={item.seasons_progress}
                    statusText={item.following_status_text}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 rounded-2xl bg-[#141414] border border-[#262626] text-center text-xs text-gray-400">
            {language === 'es'
              ? 'No estás siguiendo ninguna serie activa. ¡Explora el catálogo para empezar a marcar episodios!'
              : 'You are not following any active series. Browse the catalog to start tracking episodes!'}
          </div>
        )}
      </section>

      {/* ========================================================= */}
      {/* SECTION 3: FAVORITES | WATCHLIST | RECENTLY WATCHED       */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Favorites */}
        <section className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#262626]">
            <div className="flex items-baseline gap-2">
              <h3 className="text-base font-bold text-white">{t('favorites')}</h3>
              <span className="text-xs font-semibold text-gray-500">
                ({library?.favorites.length || 0})
              </span>
            </div>
            <Link
              to="/library?tab=favoritos"
              className="flex items-center gap-0.5 text-xs font-bold text-amber-500 hover:text-amber-400 transition-colors"
            >
              <span>{t('viewAll')}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {library?.favorites.slice(0, 3).map((item) => (
              <ProfilePosterCard key={item.id} item={item} />
            ))}
            {(!library || library.favorites.length === 0) && (
              <p className="col-span-3 text-xs text-gray-500 italic py-4">
                {language === 'es' ? 'Aún no guardaste favoritos.' : 'No favorites saved yet.'}
              </p>
            )}
          </div>
        </section>

        {/* Watchlist */}
        <section className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#262626]">
            <div className="flex items-baseline gap-2">
              <h3 className="text-base font-bold text-white">{t('watchlist')}</h3>
              <span className="text-xs font-semibold text-gray-500">
                ({library?.watchlist.length || 0})
              </span>
            </div>
            <Link
              to="/library?tab=watchlist"
              className="flex items-center gap-0.5 text-xs font-bold text-amber-500 hover:text-amber-400 transition-colors"
            >
              <span>{t('viewAll')}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {library?.watchlist.slice(0, 3).map((item) => (
              <ProfilePosterCard key={item.id} item={item} />
            ))}
            {(!library || library.watchlist.length === 0) && (
              <p className="col-span-3 text-xs text-gray-500 italic py-4">
                {language === 'es' ? 'Tu lista está vacía.' : 'Watchlist is empty.'}
              </p>
            )}
          </div>
        </section>

        {/* Recently Watched */}
        <section className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#262626]">
            <div className="flex items-baseline gap-2">
              <h3 className="text-base font-bold text-white">{t('recentlyWatched')}</h3>
              <span className="text-xs font-semibold text-gray-500">
                ({library?.recently_watched.length || 0})
              </span>
            </div>
            <Link
              to="/library?tab=vistas"
              className="flex items-center gap-0.5 text-xs font-bold text-amber-500 hover:text-amber-400 transition-colors"
            >
              <span>{t('viewAll')}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {library?.recently_watched.slice(0, 3).map((item) => (
              <ProfilePosterCard key={item.id} item={item} showStatusBadge={item.tipo === 'tv'} />
            ))}
            {(!library || library.recently_watched.length === 0) && (
              <p className="col-span-3 text-xs text-gray-500 italic py-4">
                {language === 'es' ? 'Aún no hay títulos vistos.' : 'No watched titles yet.'}
              </p>
            )}
          </div>
        </section>
      </div>

      {/* Edit Profile Modal */}
      <EditProfileModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSuccess={fetchData}
      />
    </div>
  )
}

/**
 * Small poster card for bottom columns
 */
const ProfilePosterCard: React.FC<{ item: TitleCard; showStatusBadge?: boolean }> = ({
  item,
}) => {
  return (
    <Link to={`/titles/${item.id}`} className="group block space-y-1.5">
      <div className="relative aspect-2/3 rounded-xl overflow-hidden bg-[#181818] border border-[#262626] group-hover:border-amber-500/50 transition-all shadow-md">
        {item.portada_url ? (
          <img
            src={item.portada_url}
            alt={item.nombre}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600 text-xs">
            No image
          </div>
        )}
      </div>

      <div className="relative group/pcard space-y-0.5 min-w-0">
        <h4
          aria-label={item.nombre}
          className="text-xs font-bold text-white group-hover:text-amber-400 transition-colors truncate"
        >
          {item.nombre}
        </h4>
        {/* Instant floating tooltip for long title */}
        <div className="absolute left-0 bottom-full mb-1 hidden group-hover/pcard:block z-30 px-2 py-1 bg-[#171717]/95 backdrop-blur-md border border-[#383838] rounded-lg shadow-2xl text-xs font-semibold text-amber-200 whitespace-normal max-w-[180px] pointer-events-none animate-in fade-in zoom-in-95 duration-150">
          {item.nombre}
        </div>
        <div className="flex items-center justify-between text-[11px] text-gray-400">
          <span>{item.anio_estreno || ''}</span>
          <div className="flex items-center gap-1 text-amber-400 font-bold">
            <Star className="w-3 h-3 fill-amber-400" />
            <span>{item.rating_unificado?.toFixed(1) || '0.0'}</span>
          </div>
        </div>
      </div>
    </Link>
  )
}
