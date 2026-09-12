import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import {
  Sparkles,
  Film,
  Tv,
  Layers,
  AlertCircle,
  RefreshCw,
  Flame,
  Clock,
  Award,
  Bell,
  User as UserIcon,
  Heart,
  Bookmark,
  Eye,
  PlaySquare,
  MessageSquare,
  Settings,
  LogOut,
  Send,
  Gem,
  Smile,
  Zap,
  Theater,
  Skull,
  Rocket,
  Compass,
  Video,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import { catalogService } from '@/services/catalogService'
import type { HomeSections } from '@/types/catalog'
import { CarouselRow } from '@/components/common/CarouselRow'
import { getAvatarUrl } from '@/utils/avatarUtils'

interface OutletContextType {
  openAuth: (mode?: 'login' | 'register') => void
}

export const HomePage: React.FC = () => {
  const { openAuth } = useOutletContext<OutletContextType>()
  const { user, logout } = useAuth()
  const { t, translateGenreName, language } = useLanguage()
  const navigate = useNavigate()

  const [data, setData] = useState<HomeSections | null>(null)
  const [loading, setLoading] = useState(true)
  const [filtering, setFiltering] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTipo, setActiveTipo] = useState<'all' | 'movie' | 'tv'>('all')
  const [aiPrompt, setAiPrompt] = useState('')

  const loadHome = async (tipo: 'all' | 'movie' | 'tv' = activeTipo, isFilterChange = false) => {
    if (isFilterChange) {
      setFiltering(true)
    } else {
      setLoading(true)
    }
    setError(null)
    try {
      const filters = tipo !== 'all' ? { tipo } : undefined
      const res = await catalogService.getHome(filters)
      setData(res)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Could not connect to CineTrack catalog.')
      }
    } finally {
      setLoading(false)
      setFiltering(false)
    }
  }

  const handleTipoChange = (tipo: 'all' | 'movie' | 'tv') => {
    if (tipo === activeTipo) return
    setActiveTipo(tipo)
    loadHome(tipo, true)
  }

  // Al marcar watched, dejamos el título en pantalla para no desvirtuar listas (actualiza atómicamente su tarjeta)
  const handleCardStateChange = () => {
    // No-op: TitleCard actualiza su propio estado visual reactivo
  }

  const handleAiSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (aiPrompt.trim()) {
      navigate(`/recommendations?prompt=${encodeURIComponent(aiPrompt.trim())}`)
    } else {
      navigate('/recommendations')
    }
  }

  const setPresetPrompt = (text: string) => {
    setAiPrompt(text)
  }

  const getGenreIcon = (name: string) => {
    const lower = name.toLowerCase()
    if (lower.includes('com') || lower.includes('humor')) return <Smile className="w-5 h-5 text-amber-400" />
    if (lower.includes('acc') || lower.includes('act') || lower.includes('war') || lower.includes('bél')) return <Zap className="w-5 h-5 text-amber-400" />
    if (lower.includes('dram')) return <Theater className="w-5 h-5 text-amber-400" />
    if (lower.includes('terr') || lower.includes('horr')) return <Skull className="w-5 h-5 text-amber-400" />
    if (lower.includes('cienc') || lower.includes('sci') || lower.includes('fic')) return <Rocket className="w-5 h-5 text-amber-400" />
    if (lower.includes('mis') || lower.includes('mys') || lower.includes('susp') || lower.includes('thrill')) return <Compass className="w-5 h-5 text-amber-400" />
    if (lower.includes('rom')) return <Heart className="w-5 h-5 text-amber-400" />
    if (lower.includes('anim')) return <Sparkles className="w-5 h-5 text-amber-400" />
    if (lower.includes('doc')) return <Video className="w-5 h-5 text-amber-400" />
    return <Film className="w-5 h-5 text-amber-400" />
  }

  useEffect(() => {
    loadHome(activeTipo)
  }, [user])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-10 h-10 border-3 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
        <p className="text-xs text-gray-400 font-medium">Loading movies and series...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-md mx-auto my-24 p-6 bg-[#141414] border border-[#262626] rounded-2xl text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-white mb-1">Failed to load content</h3>
        <p className="text-xs text-gray-400 mb-6">{error || 'An unexpected error occurred'}</p>
        <button
          onClick={() => loadHome(activeTipo)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      </div>
    )
  }

  const tipoParam = activeTipo !== 'all' ? `&tipo=${activeTipo}` : ''

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* ========================================================= */}
        {/* LEFT COLUMN: AI ASSISTANT (STICKY ON DESKTOP)            */}
        {/* ========================================================= */}
        <aside className="w-full lg:w-72 shrink-0 lg:sticky lg:top-20 space-y-4">
          <div className="p-5 rounded-2xl bg-[#141414] border border-[#262626] shadow-xl space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white leading-tight">AI Assistant</h3>
                <p className="text-[11px] text-gray-400">What are you in the mood for?</p>
              </div>
            </div>

            <form onSubmit={handleAiSubmit} className="space-y-3">
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="Tell us what you feel or what kind of story you're looking for..."
                rows={4}
                className="w-full p-3 text-xs bg-[#0d0d0d] border border-[#262626] rounded-xl text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors resize-none leading-relaxed"
              />

              {/* Quick suggestions */}
              <div className="space-y-1.5">
                <span className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 block">
                  Ideas to inspire you:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => setPresetPrompt('A gripping mystery movie with a mind-bending twist')}
                    className="px-2 py-1 rounded-lg bg-[#1c1c1c] hover:bg-amber-500/10 border border-[#262626] hover:border-amber-500/40 text-[10px] text-gray-300 hover:text-amber-300 transition-all text-left"
                  >
                    🔍 Gripping mystery
                  </button>
                  <button
                    type="button"
                    onClick={() => setPresetPrompt('Lighthearted and fun comedy to unwind on a Friday night')}
                    className="px-2 py-1 rounded-lg bg-[#1c1c1c] hover:bg-amber-500/10 border border-[#262626] hover:border-amber-500/40 text-[10px] text-gray-300 hover:text-amber-300 transition-all text-left"
                  >
                    😂 Light comedy
                  </button>
                  <button
                    type="button"
                    onClick={() => setPresetPrompt('A dystopian sci-fi series with complex, layered characters')}
                    className="px-2 py-1 rounded-lg bg-[#1c1c1c] hover:bg-amber-500/10 border border-[#262626] hover:border-amber-500/40 text-[10px] text-gray-300 hover:text-amber-300 transition-all text-left"
                  >
                    🚀 Deep Sci-Fi
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2 active:scale-98"
              >
                <Send className="w-3.5 h-3.5" /> Recommend
              </button>
            </form>
          </div>
        </aside>

        {/* ========================================================= */}
        {/* CENTER COLUMN: QUICK FILTER TOGGLE + CAROUSELS           */}
        {/* ========================================================= */}
        <main className="flex-1 min-w-0 space-y-6">
          {/* Quick Filter Toggle (All / Movies / Series) */}
          <div className="flex items-center justify-between p-2 rounded-2xl bg-[#141414] border border-[#262626]">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => handleTipoChange('all')}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  activeTipo === 'all'
                    ? 'bg-amber-500 text-black font-bold shadow-md'
                    : 'text-gray-400 hover:text-white hover:bg-[#202020]'
                }`}
              >
                <Layers className="w-3.5 h-3.5" /> {t('all')}
              </button>
              <button
                onClick={() => handleTipoChange('movie')}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  activeTipo === 'movie'
                    ? 'bg-amber-500 text-black font-bold shadow-md'
                    : 'text-gray-400 hover:text-white hover:bg-[#202020]'
                }`}
              >
                <Film className="w-3.5 h-3.5" /> {t('movies')}
              </button>
              <button
                onClick={() => handleTipoChange('tv')}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  activeTipo === 'tv'
                    ? 'bg-amber-500 text-black font-bold shadow-md'
                    : 'text-gray-400 hover:text-white hover:bg-[#202020]'
                }`}
              >
                <Tv className="w-3.5 h-3.5" /> {t('series')}
              </button>
            </div>
          </div>

          {/* Filtering indicator */}
          {filtering && (
            <div className="flex items-center justify-center py-6 gap-2 text-xs text-amber-400">
              <div className="w-4 h-4 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
              <span>Updating catalog...</span>
            </div>
          )}

          {/* Carousel 1: 🔥 Trending */}
          <CarouselRow
            title={t('trendingNow')}
            subtitle={language === 'es' ? 'Los títulos más populares del momento' : 'The most popular titles people are talking about'}
            icon={<Flame className="w-5 h-5 text-amber-400" />}
            titles={data.trending}
            viewMoreLink={`/catalog?section=trending${tipoParam}`}
            onOpenAuth={openAuth}
            onStateChange={handleCardStateChange}
          />

          {/* Carousel 2: 🕒 New Releases (last 30 days) */}
          <CarouselRow
            title={t('newReleases')}
            subtitle={language === 'es' ? 'Estrenos recientes de los últimos 30 días' : 'Fresh premieres from the last 30 days'}
            icon={<Clock className="w-5 h-5 text-amber-400" />}
            titles={data.new_releases}
            viewMoreLink={`/catalog?section=new_releases${tipoParam}`}
            onOpenAuth={openAuth}
            onStateChange={handleCardStateChange}
          />

          {/* Carousel 3: 💎 Classics (Gems) */}
          <CarouselRow
            title={t('allTimeClassics')}
            subtitle={language === 'es' ? 'Joyas aclamadas del cine y la televisión' : 'Time-tested gems and historic cinema'}
            icon={<Gem className="w-5 h-5 text-amber-400" />}
            titles={data.classics}
            viewMoreLink={`/catalog?section=classics${tipoParam}`}
            onOpenAuth={openAuth}
            onStateChange={handleCardStateChange}
          />

          {/* Carousel 4: ⭐ Top Rated */}
          <CarouselRow
            title={t('topRated')}
            subtitle={language === 'es' ? 'Títulos con las calificaciones más altas' : 'Critically acclaimed titles with the highest scores'}
            icon={<Award className="w-5 h-5 text-amber-400" />}
            titles={data.top_rated}
            viewMoreLink={`/catalog?section=top_rated${tipoParam}`}
            onOpenAuth={openAuth}
            onStateChange={handleCardStateChange}
          />

          {/* Dynamic Carousels by Genre */}
          {data.by_genre &&
            Object.entries(data.by_genre).map(([genreName, items]) => (
              <CarouselRow
                key={genreName}
                title={translateGenreName(genreName)}
                subtitle={language === 'es' ? `Selección destacada de ${translateGenreName(genreName)}` : `Top ${genreName} selections`}
                icon={getGenreIcon(genreName)}
                titles={items}
                viewMoreLink={`/catalog?genero=${encodeURIComponent(genreName)}${tipoParam}`}
                onOpenAuth={openAuth}
                onStateChange={handleCardStateChange}
              />
            ))}

          {/* Carousel: Other Collections */}
          {data.others && data.others.length > 0 && (
            <CarouselRow
              title="More Discoveries"
              subtitle="Hidden gems and diverse collections"
              icon={<Compass className="w-5 h-5 text-amber-400" />}
              titles={data.others}
              viewMoreLink={`/catalog?section=others${tipoParam}`}
              onOpenAuth={openAuth}
              onStateChange={handleCardStateChange}
            />
          )}
        </main>

        {/* ========================================================= */}
        {/* RIGHT COLUMN: USER PANEL (STICKY ON DESKTOP)              */}
        {/* ========================================================= */}
        <aside className="w-full lg:w-72 shrink-0 lg:sticky lg:top-20 space-y-4">
          {user ? (
            <div className="p-5 rounded-2xl bg-[#141414] border border-[#262626] shadow-xl space-y-4">
              {/* User Header: Avatar + Username + Bell */}
              <div className="flex items-center justify-between pb-4 border-b border-[#262626]">
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-14 h-14 rounded-full overflow-hidden border-2 border-amber-500/40 bg-[#181818] flex items-center justify-center text-black font-bold shadow-md shrink-0">
                    {getAvatarUrl(user.avatar_url) ? (
                      <img
                        src={getAvatarUrl(user.avatar_url)!}
                        alt={user.nombre_usuario}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          ;(e.target as HTMLElement).style.display = 'none'
                        }}
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center text-black text-lg font-black">
                        {user.nombre_usuario.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-bold text-white truncate leading-snug">
                      {user.nombre_usuario}
                    </h4>
                    <p className="text-[11px] text-gray-400 truncate">@{user.nombre_usuario}</p>
                  </div>
                </div>

                <div
                  className="p-2 rounded-xl bg-[#0d0d0d] border border-[#262626] text-gray-400 hover:text-amber-400 transition-colors"
                  title="Notifications"
                >
                  <Bell className="w-4 h-4" />
                </div>
              </div>

              {/* Wireframe Quick Access Menu */}
              <nav className="space-y-1 text-xs">
                <Link
                  to="/profile"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-gray-300 hover:text-white hover:bg-[#202020] transition-colors"
                >
                  <UserIcon className="w-4 h-4 text-amber-400" />
                  <span className="font-medium">{t('profile')}</span>
                </Link>

                <Link
                  to="/library?tab=favoritos"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-gray-300 hover:text-white hover:bg-[#202020] transition-colors"
                >
                  <Heart className="w-4 h-4 text-red-400" />
                  <span className="font-medium">{t('favorites')}</span>
                </Link>

                <Link
                  to="/library?tab=watchlist"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-gray-300 hover:text-white hover:bg-[#202020] transition-colors"
                >
                  <Bookmark className="w-4 h-4 text-amber-400" />
                  <span className="font-medium">{t('watchlist')}</span>
                </Link>

                <Link
                  to="/library?tab=vistas"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-gray-300 hover:text-white hover:bg-[#202020] transition-colors"
                >
                  <Eye className="w-4 h-4 text-emerald-400" />
                  <span className="font-medium">{t('watchHistory')}</span>
                </Link>

                <Link
                  to="/library?tab=siguiendo"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-gray-300 hover:text-white hover:bg-[#202020] transition-colors"
                >
                  <PlaySquare className="w-4 h-4 text-amber-400" />
                  <span className="font-medium">{t('following')}</span>
                </Link>

                <Link
                  to="/reviews"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-gray-300 hover:text-white hover:bg-[#202020] transition-colors"
                >
                  <MessageSquare className="w-4 h-4 text-amber-400" />
                  <span className="font-medium">{t('reviews')}</span>
                </Link>

                <Link
                  to="/settings"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-gray-300 hover:text-white hover:bg-[#202020] transition-colors"
                >
                  <Settings className="w-4 h-4 text-gray-400" />
                  <span className="font-medium">{t('settings')}</span>
                </Link>

                <div className="border-t border-[#262626] pt-2 mt-2">
                  <button
                    onClick={logout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-red-400 hover:text-red-300 hover:bg-red-950/20 transition-colors text-left"
                  >
                    <LogOut className="w-4 h-4" />
                    <span className="font-medium">{t('signOut')}</span>
                  </button>
                </div>
              </nav>
            </div>
          ) : (
            <div className="p-5 rounded-2xl bg-[#141414] border border-[#262626] shadow-xl space-y-4 text-center">
              <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto">
                <Heart className="w-6 h-6 text-amber-400" />
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-white">{t('yourPersonalCineTrack')}</h4>
                <p className="text-xs text-gray-400 leading-relaxed">
                  {t('signInPrompt')}
                </p>
              </div>
              <div className="flex flex-col gap-2 pt-1">
                <button
                  onClick={() => openAuth('register')}
                  className="w-full py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all active:scale-98"
                >
                  {t('createAccount')}
                </button>
                <button
                  onClick={() => openAuth('login')}
                  className="w-full py-2 px-4 rounded-xl bg-[#1a1a1a] hover:bg-[#222222] border border-[#333333] text-gray-200 text-xs font-semibold transition-all active:scale-98"
                >
                  {t('logIn')}
                </button>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
