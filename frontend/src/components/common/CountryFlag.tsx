import React, { useState } from 'react'
import { getCountryName, getFlagEmoji } from '@/utils/countryUtils'

interface CountryFlagProps {
  code?: string | null
  showName?: boolean
  className?: string
  nameClassName?: string
}

export const CountryFlag: React.FC<CountryFlagProps> = ({
  code,
  showName = false,
  className = 'w-4 h-3',
  nameClassName = 'text-gray-300',
}) => {
  const [imgError, setImgError] = useState(false)

  if (!code || code.trim() === '' || code === '-') {
    return <span className="text-gray-500">-</span>
  }

  const cleanCode = code.trim().toUpperCase()
  if (cleanCode.length !== 2) {
    return <span className="text-gray-500">-</span>
  }

  const countryName = getCountryName(cleanCode)
  const flagEmoji = getFlagEmoji(cleanCode)

  const flagElement = imgError ? (
    <span className="inline-block text-xs leading-none" title={countryName}>
      {flagEmoji || '-'}
    </span>
  ) : (
    <img
      src={`https://flagcdn.com/24x18/${cleanCode.toLowerCase()}.png`}
      alt={countryName}
      title={countryName}
      onError={() => setImgError(true)}
      className={`${className} object-cover rounded-[2px] inline-block shadow-xs align-middle`}
      loading="lazy"
    />
  )

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
