const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, '')

/**
 * Resuelve la URL canonica para un avatar de usuario.
 * Si es una ruta relativa (ej. /api/v1/users/1/avatar), le antepone el host del backend.
 * Si ya es una URL absoluta o Data URI, la devuelve tal cual.
 */
export function getAvatarUrl(avatarUrl: string | null | undefined): string | null {
  if (!avatarUrl || !avatarUrl.trim()) return null

  const trimmed = avatarUrl.trim()
  if (trimmed.startsWith('data:') || trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed
  }

  // Ruta relativa del backend
  const cleanPath = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  return `${API_ORIGIN}${cleanPath}`
}
