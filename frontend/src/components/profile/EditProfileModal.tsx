import React, { useState } from 'react'
import { X, User as UserIcon, MapPin, FileText, Image as ImageIcon, AlertCircle } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { authService } from '@/services/authService'

interface EditProfileModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export const EditProfileModal: React.FC<EditProfileModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { user, updateUser } = useAuth()

  const [country, setCountry] = useState(user?.pais || '')
  const [city, setCity] = useState(user?.ciudad || '')
  const [bio, setBio] = useState(user?.descripcion || '')
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen || !user) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const updatedUser = await authService.updateProfile({
        pais: country.trim() || null,
        ciudad: city.trim() || null,
        descripcion: bio.trim() || null,
        avatar_url: avatarUrl.trim() || null,
      })

      updateUser(updatedUser)
      onSuccess?.()
      onClose()
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Failed to update profile. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="relative w-full max-w-lg bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl p-6 sm:p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
          <div>
            <h3 className="text-xl font-bold text-white">Edit Profile</h3>
            <p className="text-xs text-gray-400 mt-0.5">Update your personal details and avatar</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#202020] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 flex items-center gap-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Avatar Preview & URL */}
          <div className="flex items-center gap-4 p-3.5 rounded-xl bg-[#0d0d0d] border border-[#262626]">
            <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-amber-500/50 bg-[#1f1f1f] flex items-center justify-center shrink-0 shadow-lg">
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt="Avatar preview"
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to initial if image fails
                    ;(e.target as HTMLElement).style.display = 'none'
                  }}
                />
              ) : (
                <span className="text-xl font-extrabold text-amber-400">
                  {user.nombre_usuario.charAt(0).toUpperCase()}
                </span>
              )}
            </div>
            <div className="flex-1 space-y-1">
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                Avatar Image URL
              </label>
              <div className="relative">
                <ImageIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="url"
                  placeholder="https://example.com/your-photo.jpg"
                  value={avatarUrl}
                  onChange={(e) => setAvatarUrl(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
                />
              </div>
            </div>
          </div>

          {/* Username (Locked / Non-editable) */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">
              Username <span className="text-[10px] text-gray-500">(cannot be modified)</span>
            </label>
            <div className="relative">
              <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
              <input
                type="text"
                disabled
                value={user.nombre_usuario}
                className="w-full pl-9 pr-3 py-2 bg-[#111111] border border-[#222222] rounded-lg text-xs text-gray-400 cursor-not-allowed"
              />
            </div>
          </div>

          {/* Location: Country & City */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Country</label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="e.g. Argentina"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">City</label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="e.g. Buenos Aires"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
                />
              </div>
            </div>
          </div>

          {/* Bio / Description */}
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Bio / About You</label>
            <div className="relative">
              <FileText className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
              <textarea
                rows={3}
                placeholder="Tell the community about your taste in movies and series..."
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                maxLength={500}
                className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60 resize-none"
              />
            </div>
            <div className="text-right text-[10px] text-gray-500 mt-1">
              {bio.length}/500
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#262626]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-white hover:bg-[#202020] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
