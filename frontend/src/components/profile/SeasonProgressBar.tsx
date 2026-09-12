import React from 'react'
import type { SeasonProgress } from '@/types/catalog'

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
  if (!seasons || seasons.length === 0) {
    return null
  }

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

          return (
            <div
              key={s.numero}
              className="flex-1 h-full rounded-full bg-[#262626] overflow-hidden relative"
              title={`Season ${s.numero}: ${s.episodios_vistos}/${s.total_episodios} watched (${isCompleted ? 'Completed' : isInProgress ? 'In Progress' : 'Unwatched'})`}
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
      {statusText && (
        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 font-medium">
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
              statusText.includes('in progress')
                ? 'bg-amber-400 animate-pulse'
                : statusText.includes('watchlist')
                ? 'bg-amber-500/70'
                : 'bg-emerald-400'
            }`}
          />
          <span className="truncate">{statusText}</span>
        </div>
      )}
    </div>
  )
}
