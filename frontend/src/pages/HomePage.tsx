import React, { useState, useMemo } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bot,
  Sparkles,
  Film,
  Tv,
  Layers,
  AlertCircle,
  RefreshCw,
  TrendingUp,
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
  Gem,
  Zap,
  Theater,
  Skull,
  Rocket,
  Map,
  Laugh,
  PocketKnife,
  CassetteTape,
  Palette,
  Paintbrush,
  Users,
  ScrollText,
  Music,
  Search,
  Footprints,
  Swords,
  Sunset,
  Baby,
  Newspaper,
  Rose,
  Mic,
  Dices,
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

interface SidebarPreset {
  label: { es: string; en: string }
  prompt: { es: string; en: string }
}

const HOME_SIDEBAR_PRESETS: SidebarPreset[] = [
  {
    label: { es: '🚀 Ciencia Ficción', en: '🚀 Sci-Fi' },
    prompt: {
      es: 'Películas y series de ciencia ficción fascinantes con viajes espaciales, futuros distópicos o alta tecnología',
      en: 'Fascinating sci-fi movies and TV series featuring space exploration, dystopian futures, or high technology',
    },
  },
  {
    label: { es: '🔪 Terror & Suspenso', en: '🔪 Suspense & Horror' },
    prompt: {
      es: 'Obras oscuras de terror y suspenso psicológico que mantengan una atmósfera inquietante e inmersiva',
      en: 'Dark horror and psychological suspense stories with an unsettling and immersive atmosphere',
    },
  },
  {
    label: { es: '🏦 Robos (Heist)', en: '🏦 Clever Heists' },
    prompt: {
      es: 'Películas de atracos, robos ingeniosos y planes maestros con giros inesperados',
      en: 'Clever heist and robbery movies with intricate planning and twists',
    },
  },
  {
    label: { es: '🎬 Nolan & Villeneuve', en: '🎬 Nolan & Villeneuve' },
    prompt: {
      es: 'Obras maestras dirigidas por Christopher Nolan o Denis Villeneuve',
      en: 'Masterpieces directed by Christopher Nolan or Denis Villeneuve',
    },
  },
  {
    label: { es: '🏛️ Tarantino & Scorsese', en: '🏛️ Tarantino & Scorsese' },
    prompt: {
      es: 'Películas de autor con crimen, tensión dramática y diálogos icónicos dirigidas por Tarantino o Scorsese',
      en: 'Masterclass auteur cinema featuring sharp dialogue, crime, and dramatic tension by Tarantino or Scorsese',
    },
  },
  {
    label: { es: '🌌 Paradojas temporales', en: '🌌 Time Travel' },
    prompt: {
      es: 'Obras fascinantes sobre bucles temporales, paradojas y viajes en el tiempo',
      en: 'Fascinating stories exploring time loops, temporal paradoxes, and time travel',
    },
  },
  {
    label: { es: '📼 Clásicos 80s/90s', en: '📼 80s & 90s' },
    prompt: {
      es: 'Clásicos de culto inolvidables de las décadas de 1980 y 1990',
      en: 'Unforgettable 80s and 90s cult classics',
    },
  },
  {
    label: { es: '☕ Feel-good', en: '☕ Feel-good' },
    prompt: {
      es: 'Una película cálida, reconfortante y optimista que te deje de buen ánimo',
      en: 'A warm, uplifting, feel-good comfort movie',
    },
  },
  {
    label: { es: '💎 Joyas Ocultas', en: '💎 Hidden Gems' },
    prompt: {
      es: 'Películas o series poco conocidas pero con excelente calificación y críticas',
      en: 'Underrated movies or series that flew under the radar yet received critical acclaim',
    },
  },
  {
    label: { es: '⭐ Aclamadas (+8.5★)', en: '⭐ Top Rated (+8.5★)' },
    prompt: {
      es: 'Obras maestras con más de 8.5 estrellas aclamadas por la comunidad',
      en: 'Universally acclaimed cinema masterpieces rated 8.5 stars and above',
    },
  },
  {
    label: { es: '🔁 Volver a ver', en: '🔁 Rewatch' },
    prompt: {
      es: 'Recomiéndame una gran obra destacada de los títulos que ya vi que valga la pena revivir hoy',
      en: 'Recommend a standout title from what I have already watched that is well worth rewatching today',
    },
  },
]

export const HomePage: React.FC = () => {
  const { openAuth } = useOutletContext<OutletContextType>()
  const { user, logout, loading: authLoading } = useAuth()
  const { t, translateGenreName, language } = useLanguage()
  const navigate = useNavigate()

  const [activeTipo, setActiveTipo] = useState<'all' | 'movie' | 'tv'>('all')
  const [aiPrompt, setAiPrompt] = useState('')
  const [sidebarPresetOffset, setSidebarPresetOffset] = useState(0)

  const {
    data,
    isLoading: loading,
    error: queryError,
    refetch: reloadHome,
  } = useQuery<HomeSections>({
    queryKey: ['homeSections', activeTipo, user?.id],
    queryFn: () => catalogService.getHome(activeTipo !== 'all' ? { tipo: activeTipo } : undefined),
    enabled: !authLoading,
  })

  const error = queryError ? (queryError instanceof Error ? queryError.message : 'Could not connect to CineTrack catalog.') : null

  const visibleSidebarPresets = useMemo(() => {
    const total = HOME_SIDEBAR_PRESETS.length
    const size = 6
    const start = (sidebarPresetOffset * size) % total
    const slice = []
    for (let i = 0; i < size; i++) {
      slice.push(HOME_SIDEBAR_PRESETS[(start + i) % total])
    }
    return slice
  }, [sidebarPresetOffset])

  const handleTipoChange = (tipo: 'all' | 'movie' | 'tv') => {
    setActiveTipo(tipo)
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

    // Animación: composición artística Paleta + Pincel superpuesto
    if (lower.includes('anim')) {
      return (
        <div className="relative w-5 h-5 flex items-center justify-center">
          <Palette className="w-4 h-4 text-amber-400" />
          <Paintbrush className="w-2.5 h-2.5 text-amber-300 absolute -bottom-0.5 -right-0.5 drop-shadow" />
        </div>
      )
    }

    // Acción
    if (lower.includes('acc') || lower.includes('act')) return <Zap className="w-5 h-5 text-amber-400" />

    // Aventura
    if (lower.includes('avent') || lower.includes('advent')) return <Map className="w-5 h-5 text-amber-400" />

    // Comedia
    if (lower.includes('com') || lower.includes('humor')) return <Laugh className="w-5 h-5 text-amber-400" />

    // Crimen
    if (lower.includes('crim')) return <PocketKnife className="w-5 h-5 text-amber-400" />

    // Documental
    if (lower.includes('doc')) return <CassetteTape className="w-5 h-5 text-amber-400" />

    // Drama
    if (lower.includes('dram')) return <Theater className="w-5 h-5 text-amber-400" />

    // Familia
    if (lower.includes('fam')) return <Users className="w-5 h-5 text-amber-400" />

    // Fantasía
    if (lower.includes('fant')) return <Sparkles className="w-5 h-5 text-amber-400" />

    // Historia
    if (lower.includes('hist')) return <ScrollText className="w-5 h-5 text-amber-400" />

    // Terror
    if (lower.includes('terr') || lower.includes('horr')) return <Skull className="w-5 h-5 text-amber-400" />

    // Música
    if (lower.includes('mús') || lower.includes('mus')) return <Music className="w-5 h-5 text-amber-400" />

    // Misterio
    if (lower.includes('mis') || lower.includes('mys')) return <Search className="w-5 h-5 text-amber-400" />

    // Romance
    if (lower.includes('rom')) return <Heart className="w-5 h-5 text-amber-400" />

    // Ciencia Ficción
    if (lower.includes('cienc') || lower.includes('sci') || lower.includes('fic')) return <Rocket className="w-5 h-5 text-amber-400" />

    // Suspenso / Thriller
    if (lower.includes('susp') || lower.includes('thrill')) return <Footprints className="w-5 h-5 text-amber-400" />

    // Bélica / Guerra
    if (lower.includes('bél') || lower.includes('war') || lower.includes('guer')) return <Swords className="w-5 h-5 text-amber-400" />

    // Western
    if (lower.includes('west')) return <Sunset className="w-5 h-5 text-amber-400" />

    // Infantil (Kids - Series)
    if (lower.includes('kid') || lower.includes('infant')) return <Baby className="w-5 h-5 text-amber-400" />

    // Noticias (News - Series)
    if (lower.includes('notic') || lower.includes('news')) return <Newspaper className="w-5 h-5 text-amber-400" />

    // Reality (Series)
    if (lower.includes('real')) return <Users className="w-5 h-5 text-amber-400" />

    // Telenovela (Soap - Series)
    if (lower.includes('soap') || lower.includes('telenov')) return <Rose className="w-5 h-5 text-amber-400" />

    // Talk Show (Series)
    if (lower.includes('talk')) return <Mic className="w-5 h-5 text-amber-400" />

    return <Film className="w-5 h-5 text-amber-400" />
  }

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
          onClick={() => reloadHome()}
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
                <Bot className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white leading-tight">{t('aiAssistant')}</h3>
                <p className="text-[11px] text-gray-400">
                  {language === 'es' ? '¿Qué tienes ganas de ver?' : 'What are you in the mood for?'}
                </p>
              </div>
            </div>

            <form onSubmit={handleAiSubmit} className="space-y-3">
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder={
                  language === 'es'
                    ? 'Cuéntanos qué sientes o qué tipo de historia buscas...'
                    : "Tell us what you feel or what kind of story you're looking for..."
                }
                rows={4}
                className="w-full p-3 text-xs bg-[#0d0d0d] border border-[#262626] rounded-xl text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors resize-none leading-relaxed"
              />

              {/* Quick suggestions with rotation */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 block">
                    {t('aiIdeasHeader')}
                  </span>
                  <button
                    type="button"
                    onClick={() => setSidebarPresetOffset((prev) => prev + 1)}
                    className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
                    title={language === 'es' ? 'Mostrar más ideas' : 'Show more ideas'}
                  >
                    <Dices className="w-3 h-3" />
                    <span>{t('aiShufflePresets')}</span>
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {visibleSidebarPresets.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setPresetPrompt(item.prompt[language === 'en' ? 'en' : 'es'])}
                      className="px-2 py-1 rounded-lg bg-[#1c1c1c] hover:bg-amber-500/10 border border-[#262626] hover:border-amber-500/40 text-[10px] text-gray-300 hover:text-amber-300 transition-all text-left cursor-pointer"
                    >
                      {item.label[language === 'en' ? 'en' : 'es']}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2 active:scale-98 cursor-pointer"
              >
                <Bot className="w-3.5 h-3.5" /> {t('aiSubmitButton')}
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

          {/* Carousel 1: 📈 Trending */}
          <CarouselRow
            title={t('trendingNow')}
            subtitle={language === 'es' ? 'Los títulos más populares del momento' : 'The most popular titles people are talking about'}
            icon={<TrendingUp className="w-5 h-5 text-amber-400" />}
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
                  <PlaySquare className="w-4 h-4 text-blue-400" />
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
