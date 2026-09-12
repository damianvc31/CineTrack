import React, { useState } from 'react'
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
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  const entries = Object.entries(genresDistribution).sort((a, b) => b[1] - a[1])
  const totalGenreCounts = entries.reduce((acc, [, count]) => acc + count, 0)

  // Top 6 genres + Other
  const topGenres: Array<{
    name: string
    count: number
    percent: number
    color: string
    dasharray: string
    dashoffset: number
  }> = []

  const radius = 38
  const circumference = 2 * Math.PI * radius
  let accumulatedPercent = 0
  let otherCount = 0

  entries.forEach(([name, count], idx) => {
    if (idx < 6) {
      const percent = totalGenreCounts > 0 ? Math.round((count / totalGenreCounts) * 100) : 0
      const strokeDasharray = `${(percent / 100) * circumference} ${circumference}`
      const strokeDashoffset = -((accumulatedPercent / 100) * circumference)
      accumulatedPercent += percent

      topGenres.push({
        name: translateGenre(name, lang),
        count,
        percent,
        color: PALETTE[idx % PALETTE.length],
        dasharray: strokeDasharray,
        dashoffset: strokeDashoffset,
      })
    } else {
      otherCount += count
    }
  })

  if (otherCount > 0) {
    const otherPercent = totalGenreCounts > 0 ? Math.max(1, Math.round((otherCount / totalGenreCounts) * 100)) : 0
    const strokeDasharray = `${(otherPercent / 100) * circumference} ${circumference}`
    const strokeDashoffset = -((accumulatedPercent / 100) * circumference)

    topGenres.push({
      name: lang === 'es' ? 'Otros' : 'Other',
      count: otherCount,
      percent: otherPercent,
      color: '#71717a',
      dasharray: strokeDasharray,
      dashoffset: strokeDashoffset,
    })
  }

  const activeGenre = hoveredIdx !== null ? topGenres[hoveredIdx] : null

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-6 py-2">
      {/* Donut SVG */}
      <div className="relative w-36 h-36 shrink-0 flex items-center justify-center group">
        <svg className="w-full h-full -rotate-90 transform overflow-visible" viewBox="0 0 100 100">
          {/* Background track */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="transparent"
            stroke="#1a1a1a"
            strokeWidth="11"
          />

          {totalGenreCounts > 0 &&
            topGenres.map((g, idx) => {
              const isHovered = hoveredIdx === idx
              const hasAnyHover = hoveredIdx !== null

              return (
                <circle
                  key={g.name}
                  cx="50"
                  cy="50"
                  r={radius}
                  fill="transparent"
                  stroke={g.color}
                  strokeWidth={isHovered ? 14 : 11}
                  strokeDasharray={g.dasharray}
                  strokeDashoffset={g.dashoffset}
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  className="cursor-pointer transition-all duration-300 ease-out"
                  style={{
                    opacity: hasAnyHover && !isHovered ? 0.35 : 1,
                    filter: isHovered ? `drop-shadow(0 0 6px ${g.color}90)` : 'none',
                  }}
                />
              )
            })}
        </svg>

        {/* Center label (dynamic on hover) */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center p-2 transition-all duration-200">
          {activeGenre ? (
            <>
              <span
                className="text-xl font-black leading-none tracking-tight animate-in zoom-in-95 duration-150"
                style={{ color: activeGenre.color }}
              >
                {activeGenre.percent}%
              </span>
              <span className="text-[10px] font-bold text-gray-200 mt-1 leading-tight line-clamp-1 max-w-[85px]">
                {activeGenre.name}
              </span>
              <span className="text-[9px] text-gray-400 font-medium">
                {activeGenre.count} {lang === 'es' ? (activeGenre.count === 1 ? 'título' : 'títulos') : (activeGenre.count === 1 ? 'title' : 'titles')}
              </span>
            </>
          ) : (
            <>
              <span className="text-2xl font-black text-white leading-none tracking-tight">
                {totalTitles}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold mt-0.5">
                {lang === 'es' ? 'títulos' : 'titles'}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Legend list - Clean single-column layout preventing horizontal squash */}
      <div className="flex-1 w-full flex flex-col gap-1 text-xs min-w-0">
        {topGenres.length > 0 ? (
          topGenres.map((g, idx) => {
            const isHovered = hoveredIdx === idx
            return (
              <div
                key={g.name}
                title={g.name}
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
                className={`flex items-center justify-between gap-2 px-2 py-1 rounded-lg cursor-pointer transition-all ${
                  isHovered
                    ? 'bg-[#1f1f1f] shadow-sm'
                    : 'hover:bg-[#161616]'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span
                    className="w-2.5 h-2.5 rounded-sm shrink-0 transition-transform duration-200"
                    style={{
                      backgroundColor: g.color,
                      transform: isHovered ? 'scale(1.25)' : 'scale(1)',
                    }}
                  />
                  <span
                    className={`text-[11px] font-medium leading-tight truncate ${
                      isHovered ? 'text-white font-bold' : 'text-gray-300'
                    }`}
                  >
                    {g.name}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0 text-[11px]">
                  <span className="text-gray-500 font-normal">({g.count})</span>
                  <span
                    className="font-bold w-9 text-right"
                    style={{ color: isHovered ? g.color : '#e5e7eb' }}
                  >
                    {g.percent}%
                  </span>
                </div>
              </div>
            )
          })
        ) : (
          <p className="text-xs text-gray-500 italic py-2 text-center">
            {lang === 'es' ? 'No hay registros de géneros vistos' : 'No watched titles recorded yet'}
          </p>
        )}
      </div>
    </div>
  )
}
