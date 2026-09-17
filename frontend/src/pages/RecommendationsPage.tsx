import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Bot, RefreshCw, AlertCircle, Clapperboard, Lightbulb, ArrowRight, CornerDownLeft, Film, Tv, Info, X, Dices } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import { recommendationService } from '@/services/recommendationService'
import type { RecommendationResponse, RecommendationItem } from '@/services/recommendationService'
import { catalogService } from '@/services/catalogService'
import { TitleCard } from '@/components/common/TitleCard'

interface PresetItem {
  badge: string
  label: string
  prompt: string
}

const CACHE_KEY = 'cinetrack_recs_cache'

const PRESETS: Record<'es' | 'en', PresetItem[]> = {
  es: [
    {
      badge: '🔁 Revivir',
      label: 'Volver a ver una joya de mis vistas',
      prompt: 'Recomiéndame una gran obra destacada de los títulos que ya vi en CineTrack que valga la pena volver a ver hoy',
    },
    {
      badge: '🚀 Género',
      label: 'Ciencia ficción y odiseas espaciales',
      prompt: 'Películas y series de ciencia ficción fascinantes con viajes espaciales, futuros distópicos o alta tecnología',
    },
    {
      badge: '🔪 Género',
      label: 'Terror y suspenso psicológico',
      prompt: 'Obras oscuras de terror y suspenso psicológico que mantengan una atmósfera inquietante e inmersiva',
    },
    {
      badge: '🕵️ Género',
      label: 'Intriga criminal, misterio y detectives',
      prompt: 'Historias de detectives, misterios sin resolver e investigaciones policiales con giros impactantes',
    },
    {
      badge: '🎬 Directores',
      label: 'Christopher Nolan o Denis Villeneuve',
      prompt: 'Obras maestras complejas, cerebrales y visualmente impactantes dirigidas por Christopher Nolan o Denis Villeneuve',
    },
    {
      badge: '🏛️ Directores',
      label: 'Quentin Tarantino o Martin Scorsese',
      prompt: 'Películas con diálogos memorables, personajes intensos, crimen y dirección magistral de Tarantino o Scorsese',
    },
    {
      badge: '🎭 Actores',
      label: 'Leonardo DiCaprio o Christian Bale',
      prompt: 'Películas con actuaciones inolvidables e intensas protagonizadas por Leonardo DiCaprio o Christian Bale',
    },
    {
      badge: '🏦 Temática',
      label: 'Robos ingeniosos y planes maestros (Heist)',
      prompt: 'Películas de atracos, robos ingeniosos y planes milimétricos con tensión y giros inesperados',
    },
    {
      badge: '🌌 Temática',
      label: 'Viajes en el tiempo y paradojas temporales',
      prompt: 'Obras complejas sobre bucles temporales, paradojas y líneas de tiempo alternativas',
    },
    {
      badge: '🧭 Temática',
      label: 'Supervivencia extrema y aislamiento',
      prompt: 'Historias intensas de supervivencia extrema contra la naturaleza, el espacio o el aislamiento humano',
    },
    {
      badge: '⚖️ Temática',
      label: 'Dilemas morales y juegos de poder',
      prompt: 'Películas o series con complejos dilemas morales, secretos, ambición y manipulación psicológica',
    },
    {
      badge: '📼 Época',
      label: 'Clásicos de culto de los 80s y 90s',
      prompt: 'Películas clásicas de culto de las décadas de 1980 y 1990 que marcaron época',
    },
    {
      badge: '👑 Época',
      label: 'Joyas del cine clásico dorado (50s a 70s)',
      prompt: 'Grandes obras maestras del cine clásico entre 1950 y 1979 que resisten el paso del tiempo',
    },
    {
      badge: '🕒 Época',
      label: 'Estrenos contemporáneos recientes',
      prompt: 'Películas o series recientes de los últimos 3 años que hayan sorprendido y cautivado a la audiencia',
    },
    {
      badge: '☕ Emoción',
      label: 'Feel-good / Reconfortante para desconectar',
      prompt: 'Una película cálida, reconfortante y optimista que te deje con una sonrisa y buen ánimo',
    },
    {
      badge: '⚡ Emoción',
      label: 'Tensión implacable y adrenalina constante',
      prompt: 'Tensión de principio a fin y ritmo vertiginoso donde no puedas levantarte del asiento',
    },
    {
      badge: '💎 Joyas',
      label: 'Joyas ocultas poco conocidas pero brillantes',
      prompt: 'Películas o series poco conocidas por el gran público pero con excelentes críticas y alto impacto',
    },
    {
      badge: '⭐ Comunidad',
      label: 'Aclamadas por la crítica y el público (+8.5★)',
      prompt: 'Obras maestras con más de 8.5 estrellas y reconocimiento unánime de la crítica y la comunidad',
    },
  ],
  en: [
    {
      badge: '🔁 Rewatch',
      label: 'Rewatch a standout from my watched list',
      prompt: 'Recommend a memorable title from what I have already watched in CineTrack that is worth rewatching today',
    },
    {
      badge: '🚀 Genre',
      label: 'Sci-Fi & space odysseys',
      prompt: 'Fascinating sci-fi movies and TV series featuring space exploration, dystopian futures, or high technology',
    },
    {
      badge: '🔪 Genre',
      label: 'Horror & psychological suspense',
      prompt: 'Dark horror and psychological suspense stories with an unsettling and immersive atmosphere',
    },
    {
      badge: '🕵️ Genre',
      label: 'Mystery, crime & detective noir',
      prompt: 'Gripping detective mysteries, unsolved investigations, and noir thrillers with jaw-dropping twists',
    },
    {
      badge: '🎬 Directors',
      label: 'Christopher Nolan or Denis Villeneuve',
      prompt: 'Complex, cerebral, and visually stunning cinematic masterpieces directed by Christopher Nolan or Denis Villeneuve',
    },
    {
      badge: '🏛️ Directors',
      label: 'Quentin Tarantino or Martin Scorsese',
      prompt: 'Films with iconic dialogue, sharp tension, crime, and masterclass directing by Tarantino or Scorsese',
    },
    {
      badge: '🎭 Actors',
      label: 'Leonardo DiCaprio or Christian Bale',
      prompt: 'Movies featuring intense, unforgettable performances starring Leonardo DiCaprio or Christian Bale',
    },
    {
      badge: '🏦 Theme',
      label: 'Clever heists & intricate master plans',
      prompt: 'Smart heist and robbery movies with high-stakes planning, tension, and unpredictable twists',
    },
    {
      badge: '🌌 Theme',
      label: 'Time travel & temporal paradoxes',
      prompt: 'Intricate mind-bending stories about time loops, paradoxes, and alternate timelines',
    },
    {
      badge: '🧭 Theme',
      label: 'Extreme survival & human isolation',
      prompt: 'Gripping survival stories against harsh nature, space wilderness, or extreme human isolation',
    },
    {
      badge: '⚖️ Theme',
      label: 'Moral dilemmas & power mind games',
      prompt: 'Engrossing movies or series exploring moral dilemmas, deception, ambition, and psychological power games',
    },
    {
      badge: '📼 Era',
      label: '80s and 90s iconic cult classics',
      prompt: 'Beloved cult classics from the 1980s and 1990s that defined modern cinema',
    },
    {
      badge: '👑 Era',
      label: 'Golden age timeless cinema (50s to 70s)',
      prompt: 'Timeless cinematic masterpieces released between 1950 and 1979 that stand the test of time',
    },
    {
      badge: '🕒 Era',
      label: 'Recent contemporary standouts',
      prompt: 'Standout movies or series released in the last 3 years that surprised and captivated audiences',
    },
    {
      badge: '☕ Mood',
      label: 'Heartwarming feel-good comfort movie',
      prompt: 'A warm, uplifting, feel-good comfort movie to leave you smiling, relaxed, and inspired',
    },
    {
      badge: '⚡ Mood',
      label: 'Heart-pounding non-stop tension',
      prompt: 'Edge-of-your-seat relentless tension and fast pacing with zero breathing room from start to finish',
    },
    {
      badge: '💎 Gems',
      label: 'Hidden gems & overlooked brilliance',
      prompt: 'Underrated movies or series that flew under the radar yet received critical acclaim and deep appreciation',
    },
    {
      badge: '⭐ Community',
      label: 'Universal acclaim & top rated (+8.5★)',
      prompt: 'Universally acclaimed cinema masterpieces rated 8.5 stars and above by both critics and community',
    },
  ],
}

export const RecommendationsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()
  const { t, language } = useLanguage()

  const getInitialCache = () => {
    try {
      const raw = sessionStorage.getItem(CACHE_KEY)
      if (raw) return JSON.parse(raw)
    } catch {
      // ignore
    }
    return null
  }

  const cached = getInitialCache()
  const urlPrompt = searchParams.get('prompt')

  const [prompt, setPrompt] = useState<string>(() => urlPrompt || cached?.prompt || '')
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RecommendationResponse | null>(() => {
    if (urlPrompt && urlPrompt !== cached?.prompt) return null
    return cached?.result || null
  })

  const executeRecommendation = useCallback(async (queryText: string) => {
    const cleanQuery = queryText.trim()
    if (!cleanQuery) return

    setLoading(true)
    setError(null)
    setSearchParams(cleanQuery ? { prompt: cleanQuery } : {})

    try {
      const data = await recommendationService.getRecommendations({
        prompt: cleanQuery,
        tipo_filtro: 'all', // El prompt en lenguaje natural determina automáticamente el tipo
        language,
      })
      setResult(data)
      try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify({ prompt: cleanQuery, result: data }))
      } catch {
        // ignore
      }
    } catch (err: unknown) {
      console.error('Error fetching recommendations:', err)
      setError(t('aiErrorDesc', 'No se pudo conectar con el servicio de recomendaciones. Por favor, intenta de nuevo.'))
    } finally {
      setLoading(false)
    }
  }, [t, language, setSearchParams])

  // Ejecutar automáticamente al montar si vino con query param ?prompt=... y no coincide con el cache
  useEffect(() => {
    const initialPrompt = searchParams.get('prompt')
    if (initialPrompt && (!result || cached?.prompt !== initialPrompt) && !loading) {
      setPrompt(initialPrompt)
      executeRecommendation(initialPrompt)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (prompt.trim()) {
      executeRecommendation(prompt.trim())
    }
  }

  const handleSelectPreset = (presetPrompt: string) => {
    setPrompt(presetPrompt)
    executeRecommendation(presetPrompt)
  }

  const [presetOffset, setPresetOffset] = useState(0)

  const currentPresetsPool = PRESETS[language === 'en' ? 'en' : 'es']
  const visiblePresets = useMemo(() => {
    const total = currentPresetsPool.length
    const size = 9
    const start = (presetOffset * size) % total
    const slice = []
    for (let i = 0; i < size; i++) {
      slice.push(currentPresetsPool[(start + i) % total])
    }
    return slice
  }, [currentPresetsPool, presetOffset])

  const handleShufflePresets = () => {
    setPresetOffset((prev) => prev + 1)
  }

  const handleCardStateChange = (action: 'favorite' | 'watchlist' | 'watched', titleId: number) => {
    setResult((prev) => {
      if (!prev) return prev
      const updatedRecs = prev.recommendations.map((item) => {
        if (item.title_id !== titleId || !item.title) return item
        const updatedTitle = { ...item.title }
        if (action === 'favorite') {
          updatedTitle.user_favorito = !updatedTitle.user_favorito
        } else if (action === 'watchlist') {
          updatedTitle.user_estado = updatedTitle.user_estado === 'watchlist' ? null : 'watchlist'
        } else if (action === 'watched') {
          updatedTitle.user_estado = updatedTitle.user_estado === 'vista' ? null : 'vista'
        }
        return { ...item, title: updatedTitle }
      })
      const updated = { ...prev, recommendations: updatedRecs }
      try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify({ prompt, result: updated }))
      } catch {
        // ignore
      }
      return updated
    })
  }

  const syncFreshStates = useCallback(async () => {
    if (!user) return
    const current = result || cached?.result
    if (!current?.recommendations?.length) return

    try {
      const freshList = await Promise.all(
        current.recommendations.map(async (item: RecommendationItem) => {
          try {
            const st = await catalogService.getUserState(item.title_id)
            return { id: item.title_id, st }
          } catch {
            return null
          }
        })
      )

      setResult((prev) => {
        const target = prev || current
        if (!target) return prev
        let hasChanges = false
        const updatedRecs = target.recommendations.map((item: RecommendationItem) => {
          const fresh = freshList.find((f) => f && f.id === item.title_id)
          if (fresh && fresh.st && item.title) {
            if (
              item.title.user_favorito !== fresh.st.favorito ||
              item.title.user_estado !== fresh.st.estado
            ) {
              hasChanges = true
              return {
                ...item,
                title: {
                  ...item.title,
                  user_favorito: fresh.st.favorito,
                  user_estado: fresh.st.estado,
                },
              }
            }
          }
          return item
        })

        if (!hasChanges) return prev || current
        const updated = { ...target, recommendations: updatedRecs }
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify({ prompt, result: updated }))
        } catch {
          // ignore
        }
        return updated
      })
    } catch (err) {
      console.error('Error syncing recommendation user states:', err)
    }
  }, [user, prompt])

  // Sincronizar estados cuando el usuario cambia, al montar la página o al volver del detalle
  useEffect(() => {
    syncFreshStates()
    const handleFocus = () => syncFreshStates()
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [syncFreshStates])

  const handleClear = () => {
    setPrompt('')
    setResult(null)
    setSearchParams({})
    try {
      sessionStorage.removeItem(CACHE_KEY)
    } catch {
      // ignore
    }
  }

  const getProviderBadge = (provider: string, model?: string) => {
    let providerLabel = 'Google Gemini'
    let providerClass = 'bg-amber-500/10 text-amber-400 border-amber-500/30'
    let modelLabel = model || 'gemini-3.6-flash'
    let tooltip = language === 'es'
      ? `Respuesta generada mediante ${providerLabel} (${modelLabel}) evaluando sinopsis y contexto.`
      : `Generated via ${providerLabel} (${modelLabel}) analyzing synopses and context.`

    if (provider === 'groq') {
      providerLabel = 'Groq Cloud'
      providerClass = 'bg-orange-500/10 text-orange-400 border-orange-500/30'
      modelLabel = model || 'openai/gpt-oss-120b'
      tooltip = language === 'es'
        ? `Respuesta generada mediante ${providerLabel} (${modelLabel}) como respaldo de alta velocidad.`
        : `Generated via ${providerLabel} (${modelLabel}) as high-speed fallback.`
    } else if (provider === 'heuristic') {
      providerLabel = t('aiEngineLocal')
      providerClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
      modelLabel = language === 'es' ? 'Reglas Ponderadas de Catálogo' : 'Weighted Catalog Rules'
      tooltip = language === 'es'
        ? 'Generado localmente sin APIs externas mediante filtrado ponderado de catálogo (concordancia temática, puntaje unificado y volumen de votos).'
        : 'Generated locally without external APIs using weighted catalog filtering (thematic match, scores and vote count).'
    }

    return (
      <div
        title={tooltip}
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold border ${providerClass} cursor-help shadow-sm`}
      >
        <Bot className="w-3.5 h-3.5 shrink-0" />
        <span>{providerLabel}</span>
        <span className="text-gray-500">•</span>
        <span className="font-mono text-[10px] text-gray-300">{modelLabel}</span>
        <Info className="w-3 h-3 text-gray-400 ml-0.5 shrink-0" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Hero Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold shadow-sm">
          <Bot className="w-4 h-4 text-amber-400 animate-pulse" />
          <span>{t('aiAssistant')}</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          {t('aiRecommenderTitle')}
        </h1>
        <p className="text-sm sm:text-base text-gray-400 max-w-2xl mx-auto">
          {t('aiRecommenderSubtitle')}
        </p>
      </div>

      {/* Tip para usuarios invitados */}
      {!user && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-gradient-to-r from-amber-950/30 via-[#181818] to-amber-950/20 border border-amber-500/30 flex items-center justify-between gap-4 text-xs text-amber-200 shadow-md">
          <div className="flex items-center gap-2.5">
            <Lightbulb className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{t('aiGuestTip')}</span>
          </div>
          <Link
            to="/catalog"
            className="shrink-0 text-amber-400 hover:text-amber-300 font-semibold underline underline-offset-4 hidden sm:inline"
          >
            {t('exploreCatalog')} &rarr;
          </Link>
        </div>
      )}

      {/* Input Box & Presets */}
      <div className="p-5 sm:p-6 rounded-2xl bg-[#121212] border border-[#262626] shadow-xl space-y-4">
        {result && (
          <div className="flex justify-end border-b border-[#222222] pb-3">
            <button
              type="button"
              onClick={handleClear}
              className="inline-flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 font-semibold underline underline-offset-2 transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>{t('aiResetSearch')}</span>
            </button>
          </div>
        )}

        {/* Formulario de prompt */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative">
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t('aiPromptPlaceholder')}
              className="w-full p-4 text-sm bg-[#181818] border border-[#2d2d2d] focus:border-amber-500 focus:ring-1 focus:ring-amber-500 rounded-xl text-white placeholder-gray-500 outline-none transition-all resize-none shadow-inner"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit(e)
                }
              }}
            />
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
            <span className="text-[11px] text-gray-500 hidden sm:inline-flex items-center gap-1">
              {t('aiSearchHint')} <CornerDownLeft className="w-3 h-3 ml-0.5 text-gray-400" />
            </span>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:from-gray-700 disabled:to-gray-800 disabled:text-gray-500 text-black text-xs sm:text-sm font-bold shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-black" />
                  <span>{t('aiThinking')}</span>
                </>
              ) : (
                <>
                  <Bot className="w-4 h-4 text-black" />
                  <span>{t('aiSubmitButton')}</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Chips de sugerencias predefinidas categorizadas */}
        <div className="pt-2 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 block">
              {t('aiIdeasHeader')}
            </span>
            <button
              type="button"
              onClick={handleShufflePresets}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 border border-amber-500/30 transition-all cursor-pointer shadow-sm"
              title={language === 'es' ? 'Mostrar otras ideas sugeridas' : 'Show other idea suggestions'}
            >
              <Dices className="w-3.5 h-3.5" />
              <span>{t('aiShufflePresets')}</span>
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {visiblePresets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectPreset(p.prompt)}
                className="group p-2.5 rounded-xl bg-[#171717] hover:bg-[#202020] border border-[#262626] hover:border-amber-500/50 text-left transition-all cursor-pointer flex flex-col justify-between gap-1 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">
                    {p.badge}
                  </span>
                  <ArrowRight className="w-3 h-3 text-gray-600 group-hover:text-amber-400 group-hover:translate-x-0.5 transition-all shrink-0" />
                </div>
                <span className="text-xs text-gray-300 group-hover:text-white font-medium leading-snug">
                  {p.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Estado de Carga */}
      {loading && (
        <div className="p-8 rounded-2xl bg-[#121212] border border-[#262626] text-center space-y-4 animate-pulse">
          <div className="w-12 h-12 mx-auto rounded-full bg-amber-500/20 flex items-center justify-center text-amber-400 border border-amber-500/30 shadow-lg shadow-amber-500/10">
            <Bot className="w-6 h-6 animate-bounce" />
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-bold text-white">{t('aiLoadingTitle')}</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto">
              {t('aiLoadingDesc')}
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-80 bg-[#1a1a1a] rounded-xl border border-[#2a2a2a] animate-pulse" />
            ))}
          </div>
        </div>
      )}

      {/* Estado de Error */}
      {error && !loading && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-900/50 flex items-start gap-3 text-sm text-red-200">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">{t('aiErrorTitle')}</p>
            <p className="text-xs text-red-300">{error}</p>
          </div>
        </div>
      )}

      {/* Resultados */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Tarjeta de Mensaje del Asistente */}
          <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-amber-950/20 via-[#141414] to-[#121212] border border-amber-500/30 shadow-xl space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400 border border-amber-500/30">
                  <Bot className="w-4 h-4" />
                </div>
                <h2 className="text-sm font-bold text-white">{t('aiAssistant')}</h2>
              </div>
              {getProviderBadge(result.provider_used, result.model_used)}
            </div>

            <p className="text-sm text-gray-200 leading-relaxed font-medium">
              {result.message}
            </p>

            {result.provider_used === 'heuristic' && (
              <div className="pt-3 mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-amber-500/20 text-xs text-amber-200/80">
                <span>
                  {t('aiHeuristicNotice')}
                </span>
                <button
                  type="button"
                  onClick={() => executeRecommendation(prompt)}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 hover:text-amber-300 border border-amber-500/30 text-xs font-semibold transition-all cursor-pointer w-fit shrink-0 shadow-sm"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  <span>{t('aiRetryWithAi')}</span>
                </button>
              </div>
            )}
          </div>

          {/* Caso 1: Clarification Needed (Incertidumbre / Ambiguo) */}
          {result.status === 'clarification_needed' && result.clarification_suggestions.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#121212] border border-[#262626] space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" /> {t('aiClarificationTitle')}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {result.clarification_suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setPrompt(suggestion)
                      executeRecommendation(suggestion)
                    }}
                    className="p-3.5 rounded-xl bg-[#181818] hover:bg-amber-950/20 border border-[#2d2d2d] hover:border-amber-500/50 text-left text-xs text-gray-200 hover:text-white transition-all flex items-center justify-between group shadow-sm cursor-pointer"
                  >
                    <span>{suggestion}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-amber-400 group-hover:translate-x-1 transition-all" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Caso 2: Recomendaciones Exitosas */}
          {result.status === 'recommended' && result.recommendations.length > 0 && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                  <Clapperboard className="w-5 h-5 text-amber-500" />
                  <span>{t('aiSelectedTitles')} ({result.recommendations.length})</span>
                </h3>
              </div>

              {/* Grid de títulos recomendados con su justificación */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {result.recommendations.map((item) => {
                  if (!item.title) return null
                  const isTv = item.title.tipo === 'tv'
                  return (
                    <div
                      key={item.title_id}
                      className="flex flex-col bg-[#121212] border border-[#262626] hover:border-amber-500/40 rounded-2xl overflow-hidden transition-all duration-200 hover:shadow-2xl hover:shadow-amber-500/10"
                    >
                      {/* Header de la tarjeta con tipo de medio prominente (Película / Serie) y año */}
                      <div className="px-4 py-2.5 bg-[#171717] border-b border-[#242424] flex items-center justify-between">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold ${
                            isTv
                              ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                              : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {isTv ? <Tv className="w-3.5 h-3.5" /> : <Film className="w-3.5 h-3.5" />}
                          <span>{isTv ? t('aiSeries') : t('aiMovie')}</span>
                        </span>
                        {item.title.anio_estreno && (
                          <span className="text-xs font-semibold text-gray-400">
                            {item.title.anio_estreno}
                          </span>
                        )}
                      </div>

                      {/* Tarjeta de Título */}
                      <div className="p-3 flex justify-center">
                        <TitleCard title={item.title} onStateChange={handleCardStateChange} />
                      </div>

                      {/* Bloque de Justificación IA */}
                      <div className="p-4 bg-gradient-to-b from-[#161616] to-[#121212] border-t border-[#222222] flex-1 flex flex-col justify-between space-y-2">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-400 uppercase tracking-wider">
                            <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                            <span>{t('aiWhyRecommended')}</span>
                          </div>
                          <p className="text-xs text-gray-300 leading-relaxed">
                            {item.reason}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
