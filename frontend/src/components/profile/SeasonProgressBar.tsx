import React from 'react'
import type { SeasonProgress } from '@/types/catalog'
import { useLanguage } from '@/context/LanguageContext'

interface SeasonProgressBarProps {
  seasons?: SeasonProgress[] | null
  statusText?: string | null
  className?: string
}

export const SeasonProgressBar: React.FC<SeasonProgressBarProps> = ({
  seasons,
  statusText,
  className = '',
}) => {
  const { language } = useLanguage()

  if (!seasons || seasons.length === 0) {
    return null
  }

  // Localizar texto de estado (S1 in progress -> T1 En curso, S1 pending -> T1 Pendiente, etc.)
  const formatStatus = (raw: string): string => {
    if (language === 'es') {
      if (raw.toLowerCase().includes('all caught up') || raw.toLowerCase().includes('al día')) return 'Al día'
      const matchProg = raw.match(/s(\d+)\s+in\s+progress/i)
      if (matchProg) return `T${matchProg[1]} En curso`
      const matchPend = raw.match(/s(\d+)\s+(?:pending|watchlist)/i)
      if (matchPend) return `T${matchPend[1]} Pendiente`
      return raw.replace(/^S(\d+)/i, 'T$1')
    } else {
      if (raw.toLowerCase().includes('all caught up') || raw.toLowerCase().includes('al día')) return 'All caught up'
      const matchProg = raw.match(/s(\d+)\s+in\s+progress/i)
      if (matchProg) return `S${matchProg[1]} In progress`
      const matchPend = raw.match(/s(\d+)\s+(?:pending|watchlist)/i)
      if (matchPend) return `S${matchPend[1]} Pending`
      return raw
    }
  }

  const localizedStatus = statusText ? formatStatus(statusText) : null

  return (
    <div className={`space-y-1.5 ${className}`}>
      {/* Segmented bar per season */}
      <div className="flex items-center gap-1.5 w-full h-1.5 sm:h-2">
        {seasons.map((s) => {
          const isCompleted = s.estado === 'completed'
          const isInProgress = s.estado === 'in_progress'
          const progressPercent = s.total_episodios > 0
            ? Math.round((s.episodios_vistos / s.total_episodios) * 100)
            : 0

          const tooltipText = language === 'es'
            ? `Temporada ${s.numero}: ${s.episodios_vistos}/${s.total_episodios} vistos (${isCompleted ? 'Completada' : isInProgress ? 'En curso' : 'Sin ver'})`
            : `Season ${s.numero}: ${s.episodios_vistos}/${s.total_episodios} watched (${isCompleted ? 'Completed' : isInProgress ? 'In Progress' : 'Unwatched'})`

          return (
            <div
              key={s.numero}
              className="flex-1 h-full rounded-full bg-[#262626] overflow-hidden relative"
              title={tooltipText}
            >
              {isCompleted ? (
                <div className="w-full h-full bg-[#f59e0b]" />
              ) : isInProgress ? (
                <div
                  className="h-full bg-[#f59e0b] rounded-full transition-all"
                  style={{ width: `${Math.max(15, progressPercent)}%` }}
                />
              ) : null}
            </div>
          )
        })}
      </div>

      {/* Legend & status label */}
      {localizedStatus && (
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 font-medium">
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
              statusText?.toLowerCase().includes('in progress')
                ? 'bg-amber-400 animate-pulse'
                : statusText?.toLowerCase().includes('pending') || statusText?.toLowerCase().includes('watchlist')
                ? 'bg-amber-500/70'
                : 'bg-emerald-400'
            }`}
          />
          <span className="truncate">{localizedStatus}</span>
        </div>
      )}
    </div>
  )
}
