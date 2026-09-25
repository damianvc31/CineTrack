import React, { useState } from 'react'
import { getCountryName, getFlagEmoji } from '@/utils/countryUtils'

interface CountryFlagProps {
  code?: string | null
  codes?: string[] | null
  showName?: boolean
  className?: string
  nameClassName?: string
}

const HISTORICAL_FLAGS: Record<string, React.FC<{ className?: string; countryName: string }>> = {
  // Unión Soviética (1922-1991)
  SU: ({ className = 'w-4 h-3', countryName }) => (
    <svg
      viewBox="0 0 24 18"
      className={`${className} object-cover rounded-[2px] inline-block shadow-xs align-middle`}
      aria-label={countryName}
    >
      <title>{countryName}</title>
      <rect width="24" height="18" fill="#cd0000" />
      {/* Estrella dorada */}
      <polygon
        points="5,2 5.5,3.5 7,3.5 5.8,4.4 6.2,5.8 5,4.9 3.8,5.8 4.2,4.4 3,3.5 4.5,3.5"
        fill="#ffd700"
      />
      {/* Hoz y martillo estilizados */}
      <path
        d="M3.2,7.8 C3.1,5.6 4.8,4.3 6.8,5 C6.9,5.7 6.4,6.4 5.7,6.4 C4.8,6.4 4.2,7.1 4.3,7.9 C4.4,8.6 5.1,9.1 5.9,8.9 L6.3,9.7 C4.8,10.2 3.3,9.3 3.2,7.8 Z"
        fill="#ffd700"
      />
      <path
        d="M3.5,9.5 L7.2,5.8 L7.8,6.4 L6.2,8 L7,8.8 L6.4,9.4 L5.6,8.6 L4.1,10.1 Z"
        fill="#ffd700"
      />
    </svg>
  ),
  // Yugoslavia (RFS de Yugoslavia 1945-1992)
  YU: ({ className = 'w-4 h-3', countryName }) => (
    <svg
      viewBox="0 0 24 18"
      className={`${className} object-cover rounded-[2px] inline-block shadow-xs align-middle`}
      aria-label={countryName}
    >
      <title>{countryName}</title>
      {/* Franja azul superior */}
      <rect width="24" height="6" fill="#003893" />
      {/* Franja blanca central */}
      <rect y="6" width="24" height="6" fill="#ffffff" />
      {/* Franja roja inferior */}
      <rect y="12" width="24" height="6" fill="#de0000" />
      {/* Estrella roja con borde dorado */}
      <polygon
        points="12,4.5 13.3,7.5 16.5,7.7 14,9.8 14.8,13 12,11.2 9.2,13 10,9.8 7.5,7.7 10.7,7.5"
        fill="#de0000"
        stroke="#ffd700"
        strokeWidth="0.8"
        strokeLinejoin="round"
      />
    </svg>
  ),
  // Checoslovaquia (1918-1992)
  CS: ({ className = 'w-4 h-3', countryName }) => (
    <svg
      viewBox="0 0 24 18"
      className={`${className} object-cover rounded-[2px] inline-block shadow-xs align-middle`}
      aria-label={countryName}
    >
      <title>{countryName}</title>
      <rect width="24" height="9" fill="#ffffff" />
      <rect y="9" width="24" height="9" fill="#d7141a" />
      <polygon points="0,0 12,9 0,18" fill="#11457e" />
    </svg>
  ),
}

const SingleFlag: React.FC<{
  cleanCode: string
  className?: string
  countryName: string
}> = ({ cleanCode, className = 'w-4 h-3', countryName }) => {
  const [imgError, setImgError] = useState(false)
  const flagEmoji = getFlagEmoji(cleanCode)

  const HistoricalFlag = HISTORICAL_FLAGS[cleanCode]
  if (HistoricalFlag) {
    return <HistoricalFlag className={className} countryName={countryName} />
  }

  if (imgError) {
    return (
      <span className="inline-block text-xs leading-none" title={countryName}>
        {flagEmoji || '-'}
      </span>
    )
  }

  return (
    <img
      src={`https://flagcdn.com/24x18/${cleanCode.toLowerCase()}.png`}
      alt={countryName}
      title={countryName}
      onError={() => setImgError(true)}
      className={`${className} object-cover rounded-[2px] inline-block shadow-xs align-middle`}
      loading="lazy"
    />
  )
}

export const CountryFlag: React.FC<CountryFlagProps> = ({
  code,
  codes: propCodes,
  showName = false,
  className = 'w-4 h-3',
  nameClassName = 'text-gray-300',
}) => {
  let list: string[] = []
  if (propCodes && propCodes.length > 0) {
    list = propCodes.map((c) => c.trim().toUpperCase()).filter((c) => c.length === 2)
  } else if (code && code.trim() !== '' && code !== '-') {
    list = code
      .split(',')
      .map((c) => c.trim().toUpperCase())
      .filter((c) => c.length === 2)
  }

  if (list.length === 0) {
    return <span className="text-gray-500">-</span>
  }

  if (list.length === 1) {
    const cleanCode = list[0]
    const countryName = getCountryName(cleanCode)
    const flagElement = <SingleFlag cleanCode={cleanCode} className={className} countryName={countryName} />

    if (showName) {
      return (
        <span className="inline-flex items-center gap-1.5" title={countryName}>
          {flagElement}
          <span className={nameClassName}>{countryName}</span>
        </span>
      )
    }

    return flagElement
  }

  // Múltiples países (coproducción)
  if (showName) {
    return (
      <span className="inline-flex flex-wrap items-center gap-2">
        {list.map((cleanCode, idx) => {
          const countryName = getCountryName(cleanCode)
          return (
            <span key={cleanCode} className="inline-flex items-center gap-1.5">
              <SingleFlag cleanCode={cleanCode} className={className} countryName={countryName} />
              <span className={nameClassName}>{countryName}</span>
              {idx < list.length - 1 && <span className="text-gray-500">,</span>}
            </span>
          )
        })}
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1">
      {list.slice(0, 3).map((cleanCode) => (
        <SingleFlag
          key={cleanCode}
          cleanCode={cleanCode}
          className={className}
          countryName={getCountryName(cleanCode)}
        />
      ))}
    </span>
  )
}
