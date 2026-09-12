import React from 'react'
import { translateGenre } from '@/utils/genreTranslations'

interface DonutGenreChartProps {
  genresDistribution?: Record<string, number>
  totalTitles?: number
  lang?: 'en' | 'es'
}

const PALETTE = [
  '#f59e0b', // Amber
  '#06b6d4', // Cyan
  '#10b981', // Emerald
  '#a855f7', // Purple
  '#f43f5e', // Rose
  '#3b82f6', // Blue
  '#f97316', // Orange
  '#84cc16', // Lime
  '#71717a', // Zinc
]

export const DonutGenreChart: React.FC<DonutGenreChartProps> = ({
  genresDistribution = {},
  totalTitles = 0,
  lang = 'en',
}) => {
  const entries = Object.entries(genresDistribution).sort((a, b) => b[1] - a[1])
  const totalGenreCounts = entries.reduce((acc, [, count]) => acc + count, 0)

  // Top 6 genres + Other
  const topGenres: Array<{ name: string; count: number; percent: number; color: string }> = []
  let otherCount = 0

  entries.forEach(([name, count], idx) => {
    if (idx < 6) {
      const percent = totalGenreCounts > 0 ? Math.round((count / totalGenreCounts) * 100) : 0
      topGenres.push({
        name: translateGenre(name, lang),
        count,
        percent,
        color: PALETTE[idx % PALETTE.length],
      })
    } else {
      otherCount += count
    }
  })

  if (otherCount > 0) {
    const otherPercent = totalGenreCounts > 0 ? Math.round((otherCount / totalGenreCounts) * 100) : 0
    topGenres.push({
      name: lang === 'es' ? 'Otros' : 'Other',
      count: otherCount,
      percent: otherPercent,
      color: '#71717a',
    })
  }

  // SVG Donut calculation
  const radius = 38
  const circumference = 2 * Math.PI * radius
  let accumulatedPercent = 0

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-6 py-2">
      {/* Donut SVG */}
      <div className="relative w-36 h-36 shrink-0 flex items-center justify-center">
        <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
          {/* Background track */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="transparent"
            stroke="#1f1f1f"
            strokeWidth="11"
          />

          {totalGenreCounts > 0 &&
            topGenres.map((g) => {
              const strokeDasharray = `${(g.percent / 100) * circumference} ${circumference}`
              const strokeDashoffset = -((accumulatedPercent / 100) * circumference)
              accumulatedPercent += g.percent

              return (
                <circle
                  key={g.name}
                  cx="50"
                  cy="50"
                  r={radius}
                  fill="transparent"
                  stroke={g.color}
                  strokeWidth="11"
                  strokeDasharray={strokeDasharray}
                  strokeDashoffset={strokeDashoffset}
                  className="transition-all duration-500 ease-out"
                />
              )
            })}
        </svg>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
          <span className="text-2xl font-black text-white leading-none tracking-tight">
            {totalTitles}
          </span>
          <span className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold mt-0.5">
            {lang === 'es' ? 'títulos' : 'titles'}
          </span>
        </div>
      </div>

      {/* Legend list */}
      <div className="flex-1 w-full grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        {topGenres.length > 0 ? (
          topGenres.map((g) => (
            <div key={g.name} className="flex items-center justify-between gap-2 min-w-0">
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ backgroundColor: g.color }}
                />
                <span className="text-gray-300 truncate text-[11px]">{g.name}</span>
              </div>
              <span className="font-bold text-gray-200 text-[11px] shrink-0">
                {g.percent}%
              </span>
            </div>
          ))
        ) : (
          <p className="col-span-2 text-xs text-gray-500 italic">
            {lang === 'es' ? 'No hay registros de géneros vistos' : 'No watched titles recorded yet'}
          </p>
        )}
      </div>
    </div>
  )
}
