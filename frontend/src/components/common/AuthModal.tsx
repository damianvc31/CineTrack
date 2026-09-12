import React, { useState, useEffect } from 'react'
import { X, Lock, User as UserIcon, MapPin, FileText, Image as ImageIcon, AlertCircle } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  initialMode?: 'login' | 'register'
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, initialMode = 'login' }) => {
  const { login, register } = useAuth()
  const [isRegisterMode, setIsRegisterMode] = useState(initialMode === 'register')
  const [nombreUsuario, setNombreUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [pais, setPais] = useState('')
  const [ciudad, setCiudad] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setIsRegisterMode(initialMode === 'register')
      setError(null)
    }
  }, [isOpen, initialMode])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!nombreUsuario.trim()) {
      setError('Username is required.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      if (isRegisterMode) {
        await register({
          nombre_usuario: nombreUsuario.trim(),
          password,
          pais: pais.trim() || undefined,
          ciudad: ciudad.trim() || undefined,
          descripcion: descripcion.trim() || undefined,
          avatar_url: avatarUrl.trim() || undefined,
        })
      } else {
        await login({
          nombre_usuario: nombreUsuario.trim(),
          password,
        })
      }
      onClose()
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Authentication error. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="relative w-full max-w-md bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl p-6 sm:p-8 space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#202020] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Title */}
        <div className="text-center">
          <h3 className="text-2xl font-bold text-white tracking-tight">
            {isRegisterMode ? 'Create an Account' : 'Sign In'}
          </h3>
          <p className="text-xs text-gray-400 mt-1">
            {isRegisterMode
              ? 'Join CineTrack to save favorites, track episodes, and write reviews'
              : 'Enter your credentials to access your personal watchlist and profile'}
          </p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 flex items-center gap-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Username</label>
            <div className="relative">
              <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                required
                autoFocus
                value={nombreUsuario}
                onChange={(e) => setNombreUsuario(e.target.value)}
                placeholder="e.g. damian, cinephile99"
                className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 6 characters"
                className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
              />
            </div>
          </div>

          {isRegisterMode && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Country</label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input
                      type="text"
                      value={pais}
                      onChange={(e) => setPais(e.target.value)}
                      placeholder="e.g. Argentina"
                      className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">City</label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input
                      type="text"
                      value={ciudad}
                      onChange={(e) => setCiudad(e.target.value)}
                      placeholder="e.g. Córdoba"
                      className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Bio / About You</label>
                <div className="relative">
                  <FileText className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
                  <textarea
                    rows={2}
                    value={descripcion}
                    onChange={(e) => setDescripcion(e.target.value)}
                    placeholder="Short bio about your movie taste"
                    className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60 resize-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Avatar URL</label>
                <div className="relative">
                  <ImageIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="url"
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                    placeholder="https://example.com/avatar.jpg"
                    className="w-full pl-9 pr-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
                  />
                </div>
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 active:scale-[0.99] font-bold text-xs text-black shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2 mt-4 disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-block w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
            ) : isRegisterMode ? (
              'Create Account'
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="pt-3 border-t border-[#262626] text-center text-xs text-gray-400">
          {isRegisterMode ? (
            <p>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setIsRegisterMode(false)
                  setError(null)
                }}
                className="text-amber-400 hover:text-amber-300 font-bold ml-1"
              >
                Sign in here
              </button>
            </p>
          ) : (
            <p>
              Don't have an account yet?{' '}
              <button
                type="button"
                onClick={() => {
                  setIsRegisterMode(true)
                  setError(null)
                }}
                className="text-amber-400 hover:text-amber-300 font-bold ml-1"
              >
                Create an account
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
