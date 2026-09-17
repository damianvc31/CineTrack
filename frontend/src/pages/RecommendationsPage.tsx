import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Sparkles, Wand2, RefreshCw, AlertCircle, Clapperboard, Tv, Lightbulb, Film, ArrowRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import { recommendationService } from '@/services/recommendationService'
import type { RecommendationResponse } from '@/services/recommendationService'
import { TitleCard } from '@/components/common/TitleCard'

const PRESETS = [
  { label: '🚀 Ciencia ficción y paradojas temporales', prompt: 'Películas de ciencia ficción espacial o con paradojas temporales y giros inesperados' },
  { label: '😱 Terror psicológico reciente', prompt: 'Terror psicológico moderno con atmósfera inquietante y buen suspenso' },
  { label: '🍿 Comedia inteligente para desconectar', prompt: 'Comedia divertida e inteligente para desconectar el fin de semana' },
  { label: '✨ Sorpréndeme con lo mejor valorado', prompt: 'Sorpréndeme con los títulos mejor valorados y aclamados del catálogo' },
  { label: '📺 Serie adictiva ya terminada', prompt: 'Una serie adictiva que ya esté terminada para hacer maratón sin esperar temporadas' },
  { label: '🕵️ Thriller policial o misterio', prompt: 'Película o serie de suspenso policial, investigación o detectives con trama atrapante' },
]

export const RecommendationsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()
  const { t, language } = useLanguage()

  const [prompt, setPrompt] = useState<string>(() => searchParams.get('prompt') || '')
  const [tipoFiltro, setTipoFiltro] = useState<'all' | 'movie' | 'tv'>('all')
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RecommendationResponse | null>(null)

  const executeRecommendation = useCallback(async (queryText: string, tipo: 'all' | 'movie' | 'tv' = tipoFiltro) => {
    const cleanQuery = queryText.trim()
    if (!cleanQuery) return

    setLoading(true)
    setError(null)
    setSearchParams(cleanQuery ? { prompt: cleanQuery } : {})

    try {
      const data = await recommendationService.getRecommendations({
        prompt: cleanQuery,
        tipo_filtro: tipo
      })
      setResult(data)
    } catch (err: unknown) {
      console.error('Error fetching recommendations:', err)
      setError(
        language === 'es'
          ? 'No se pudo conectar con el servicio de recomendaciones. Por favor, intenta de nuevo en unos momentos.'
          : 'Could not connect to recommendation service. Please try again in a moment.'
      )
    } finally {
      setLoading(false)
    }
  }, [tipoFiltro, language, setSearchParams])

  // Ejecutar automáticamente al montar si vino con query param ?prompt=...
  useEffect(() => {
    const initialPrompt = searchParams.get('prompt')
    if (initialPrompt && !result && !loading) {
      setPrompt(initialPrompt)
      executeRecommendation(initialPrompt, tipoFiltro)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (prompt.trim()) {
      executeRecommendation(prompt.trim(), tipoFiltro)
    }
  }

  const handleSelectPreset = (presetPrompt: string) => {
    setPrompt(presetPrompt)
    executeRecommendation(presetPrompt, tipoFiltro)
  }

  const handleTipoChange = (newTipo: 'all' | 'movie' | 'tv') => {
    setTipoFiltro(newTipo)
    if (prompt.trim() && result) {
      executeRecommendation(prompt.trim(), newTipo)
    }
  }

  const getProviderBadge = (provider: string) => {
    switch (provider) {
      case 'gemini':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <Sparkles className="w-3 h-3 text-purple-400" /> Google Gemini 2.0 Flash
          </span>
        )
      case 'groq':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <Sparkles className="w-3 h-3 text-amber-400" /> Groq (Llama-3.3-70B)
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Sparkles className="w-3 h-3 text-emerald-400" /> CineTrack Engine
          </span>
        )
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Hero Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-gradient-to-r from-purple-950/60 to-indigo-950/60 border border-purple-500/30 text-purple-300 text-xs font-semibold shadow-sm">
          <Sparkles className="w-4 h-4 text-purple-400 animate-pulse" />
          <span>{t('aiAssistant', 'Asistente IA')}</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          {t('aiRecommenderTitle', 'Recomendador Inteligente con IA')}
        </h1>
        <p className="text-sm sm:text-base text-gray-400 max-w-2xl mx-auto">
          {t('aiRecommenderSubtitle', 'Describe qué tienes ganas de ver y nuestra IA seleccionará las mejores opciones de nuestro catálogo.')}
        </p>
      </div>

      {/* Tip para usuarios invitados */}
      {!user && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-gradient-to-r from-purple-950/30 to-amber-950/20 border border-purple-900/40 flex items-center justify-between gap-4 text-xs text-purple-200">
          <div className="flex items-center gap-2.5">
            <Lightbulb className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{t('aiGuestTip', '¡Iniciá sesión o registrate para que CineTrack adapte las recomendaciones a tus favoritos e historial!')}</span>
          </div>
          <Link
            to="/catalog"
            className="shrink-0 text-amber-400 hover:text-amber-300 font-semibold underline underline-offset-4 hidden sm:inline"
          >
            {t('exploreCatalog')} &rarr;
          </Link>
        </div>
      )}

      {/* Input Box & Filtros */}
      <div className="p-5 sm:p-6 rounded-2xl bg-[#121212] border border-[#262626] shadow-xl space-y-4">
        {/* Selector de tipo */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#222222] pb-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-400">Tipo de contenido:</span>
            <div className="inline-flex p-1 bg-[#1a1a1a] rounded-xl border border-[#2e2e2e]">
              <button
                type="button"
                onClick={() => handleTipoChange('all')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  tipoFiltro === 'all'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {t('all', 'Todos')}
              </button>
              <button
                type="button"
                onClick={() => handleTipoChange('movie')}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  tipoFiltro === 'movie'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <Film className="w-3 h-3" /> {t('movies', 'Películas')}
              </button>
              <button
                type="button"
                onClick={() => handleTipoChange('tv')}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  tipoFiltro === 'tv'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <Tv className="w-3 h-3" /> {t('series', 'Series')}
              </button>
            </div>
          </div>

          {result && (
            <button
              type="button"
              onClick={() => {
                setPrompt('')
                setResult(null)
                setSearchParams({})
              }}
              className="text-xs text-gray-400 hover:text-gray-200 underline underline-offset-2"
            >
              Nueva consulta
            </button>
          )}
        </div>

        {/* Formulario de prompt */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative">
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ej: 'Quiero una película de ciencia ficción de viajes en el tiempo pero que sea emotiva como Interstellar o Arrival...'"
              className="w-full p-4 text-sm bg-[#181818] border border-[#2d2d2d] focus:border-purple-500 focus:ring-1 focus:ring-purple-500 rounded-xl text-white placeholder-gray-500 outline-none transition-all resize-none shadow-inner"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit(e)
                }
              }}
            />
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
            <span className="text-[11px] text-gray-500 hidden sm:inline">
              Presiona <kbd className="px-1.5 py-0.5 bg-[#222222] border border-[#333333] rounded text-gray-300">Enter</kbd> para buscar o prueba un ejemplo debajo.
            </span>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:from-gray-700 disabled:to-gray-800 disabled:text-gray-500 text-white text-xs sm:text-sm font-bold shadow-lg shadow-purple-950/40 transition-all hover:scale-102 active:scale-98 cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-purple-300" />
                  <span>Razonando...</span>
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  <span>Recomendar Títulos</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Chips de sugerencias predefinidas */}
        <div className="pt-2">
          <span className="text-xs font-semibold text-gray-400 block mb-2.5">
            Ideas y disparadores:
          </span>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectPreset(p.prompt)}
                className="px-3 py-1.5 rounded-lg bg-[#1a1a1a] hover:bg-[#252525] border border-[#2a2a2a] hover:border-purple-500/40 text-xs text-gray-300 hover:text-white transition-all text-left"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Estado de Carga */}
      {loading && (
        <div className="p-8 rounded-2xl bg-[#121212] border border-[#262626] text-center space-y-4 animate-pulse">
          <div className="w-12 h-12 mx-auto rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400">
            <Sparkles className="w-6 h-6 animate-spin" />
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-bold text-white">Consultando catálogo y ponderando preferencias...</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto">
              Analizando sinopsis, puntajes de la comunidad y tus gustos para formular una recomendación a medida.
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
            <p className="font-semibold">Ocurrió un inconveniente</p>
            <p className="text-xs text-red-300">{error}</p>
          </div>
        </div>
      )}

      {/* Resultados */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Tarjeta de Mensaje del Asistente */}
          <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-purple-950/30 via-[#141414] to-indigo-950/30 border border-purple-900/40 shadow-xl space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-purple-600/30 flex items-center justify-center text-purple-300 border border-purple-500/30">
                  <Sparkles className="w-4 h-4" />
                </div>
                <h2 className="text-sm font-bold text-white">CineTrack AI</h2>
              </div>
              {getProviderBadge(result.provider_used)}
            </div>

            <p className="text-sm text-gray-200 leading-relaxed font-medium">
              {result.message}
            </p>
          </div>

          {/* Caso 1: Clarification Needed (Incertidumbre / Ambiguo) */}
          {result.status === 'clarification_needed' && result.clarification_suggestions.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#121212] border border-[#262626] space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" /> ¿Buscamos por alguna de estas opciones?
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {result.clarification_suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setPrompt(suggestion)
                      executeRecommendation(suggestion, tipoFiltro)
                    }}
                    className="p-3.5 rounded-xl bg-[#181818] hover:bg-purple-950/30 border border-[#2d2d2d] hover:border-purple-500/50 text-left text-xs text-gray-200 hover:text-white transition-all flex items-center justify-between group shadow-sm"
                  >
                    <span>{suggestion}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-purple-400 group-hover:translate-x-1 transition-all" />
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
                  <span>Títulos Seleccionados ({result.recommendations.length})</span>
                </h3>
              </div>

              {/* Grid de títulos recomendados con su justificación */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {result.recommendations.map((item) => {
                  if (!item.title) return null
                  return (
                    <div
                      key={item.title_id}
                      className="flex flex-col bg-[#121212] border border-[#262626] hover:border-[#383838] rounded-2xl overflow-hidden transition-all duration-200 hover:shadow-2xl hover:shadow-purple-950/20"
                    >
                      {/* Tarjeta de Título */}
                      <div className="p-3 flex justify-center">
                        <TitleCard title={item.title} />
                      </div>

                      {/* Bloque de Justificación IA */}
                      <div className="p-4 bg-gradient-to-b from-[#161616] to-[#121212] border-t border-[#222222] flex-1 flex flex-col justify-between space-y-2">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-purple-400 uppercase tracking-wider">
                            <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                            <span>{t('aiWhyRecommended', 'Por qué te la recomendamos:')}</span>
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
