import React, { useState } from 'react'
import { Sparkles, Bot, Compass, Wand2 } from 'lucide-react'

export const RecommendationsPage: React.FC = () => {
  const [mood, setMood] = useState<string>('emocionante')
  const [prompt, setPrompt] = useState<string>('')

  const moods = [
    { id: 'emocionante', label: '⚡ Emocionante y Adrenalina', color: 'from-amber-500/20 to-red-500/20' },
    { id: 'reflexivo', label: '🧠 Para pensar y reflexionar', color: 'from-blue-500/20 to-indigo-500/20' },
    { id: 'relajado', label: '🍿 Divertido y para desconectar', color: 'from-green-500/20 to-emerald-500/20' },
    { id: 'oscuro', label: '🌑 Misterio, Suspenso o Terror', color: 'from-purple-500/20 to-gray-900/40' },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Encabezado */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" /> Motor Inteligente de Sugerencias
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Recomendador por Inteligencia Artificial
        </h1>
        <p className="text-xs sm:text-sm text-gray-400 max-w-lg mx-auto">
          Encuentra exactamente qué ver según tu estado de ánimo, preferencias y títulos que ya te hayan fascinado.
        </p>
      </div>

      {/* Selector de Estado de Ánimo */}
      <div className="p-6 rounded-2xl bg-[#111827] border border-gray-800 space-y-4">
        <h3 className="text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
          <Compass className="w-4 h-4 text-purple-400" /> ¿Cómo te sientes hoy?
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {moods.map((m) => (
            <button
              key={m.id}
              onClick={() => setMood(m.id)}
              className={`p-4 rounded-xl border text-left text-xs sm:text-sm font-semibold transition-all ${
                mood === m.id
                  ? 'bg-gradient-to-r from-purple-900/60 to-indigo-900/60 border-purple-500 text-white shadow-lg shadow-purple-950/50'
                  : 'bg-gray-900/80 border-gray-800 text-gray-300 hover:border-gray-700 hover:text-white'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Prompt personalizado */}
        <div className="pt-3 space-y-2">
          <label className="block text-xs font-medium text-gray-300">
            O describe en tus propias palabras qué buscas:
          </label>
          <textarea
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ejemplo: 'Quiero una película de ciencia ficción de los 90s con giros inesperados similar a Matrix o Dark City...'"
            className="w-full p-3 text-sm bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
          />
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={() => alert('El recomendador con LLM local/hub se conectará en la Fase 6.')}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs sm:text-sm font-bold shadow-xl shadow-purple-950/40 transition-all hover:scale-105 active:scale-95"
          >
            <Wand2 className="w-4 h-4" /> Generar Recomendaciones
          </button>
        </div>
      </div>

      {/* Nota de Fase 6 */}
      <div className="p-4 rounded-xl bg-purple-950/30 border border-purple-900/40 flex items-start gap-3 text-xs text-purple-300">
        <Bot className="w-5 h-5 shrink-0 text-purple-400 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Fase 6 en camino:</strong> El backend conectará el recomendador con el motor de IA local (`Ollama` / Hubs) para cruzar tu historial de visualizaciones con embeddings y metadatos de los más de 2.000 títulos de la base de datos.
        </p>
      </div>
    </div>
  )
}
