/**
 * Utilidades para manejo de banderas, países e idiomas
 */

export function getFlagEmoji(countryCode?: string | null): string {
  if (!countryCode || countryCode.trim() === '' || countryCode === '-') return ''
  const code = countryCode.trim().toUpperCase()
  if (code.length === 2 && /^[A-Z]{2}$/.test(code)) {
    const codePoints = [...code].map((c) => 127397 + c.charCodeAt(0))
    return String.fromCodePoint(...codePoints)
  }
  return ''
}

export function getCountryName(countryCode?: string | null, locale = 'en'): string {
  if (!countryCode || countryCode.trim() === '' || countryCode === '-') return '-'
  const code = countryCode.trim().toUpperCase()
  if (code.length === 2) {
    try {
      const displayNames = new Intl.DisplayNames([locale], { type: 'region' })
      const name = displayNames.of(code)
      return name || code
    } catch {
      return code
    }
  }
  return countryCode
}

export function getLanguageName(langCode?: string | null, locale = 'en'): string {
  if (!langCode || langCode.trim() === '' || langCode === '-') return '-'
  const code = langCode.trim().toLowerCase()
  try {
    const displayNames = new Intl.DisplayNames([locale], { type: 'language' })
    const name = displayNames.of(code)
    if (name) {
      // Capitalizar primera letra
      return name.charAt(0).toUpperCase() + name.slice(1)
    }
    return code.toUpperCase()
  } catch {
    return code.toUpperCase()
  }
}
