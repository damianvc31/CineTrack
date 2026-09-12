import React, { useState, useRef } from 'react'
import {
  X,
  User as UserIcon,
  MapPin,
  FileText,
  Image as ImageIcon,
  AlertCircle,
  Upload,
  ZoomIn,
  ZoomOut,
  Move,
  Check,
  RotateCcw,
  Trash2,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import { authService } from '@/services/authService'
import { getAvatarUrl } from '@/utils/avatarUtils'

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
  const { language } = useLanguage()

  const [country, setCountry] = useState(user?.pais || '')
  const [city, setCity] = useState(user?.ciudad || '')
  const [bio, setBio] = useState(user?.descripcion || '')
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imgError, setImgError] = useState(false)

  // Cropper / Centering interactive state
  const [cropMode, setCropMode] = useState(false)
  const [imageToCrop, setImageToCrop] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [baseDimensions, setBaseDimensions] = useState({ w: 200, h: 200 })
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  if (!isOpen || !user) return null

  // Manejar selección de archivo desde la PC
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setError(
        language === 'es'
          ? 'Por favor selecciona un archivo de imagen válido.'
          : 'Please select a valid image file.'
      )
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const dataUri = reader.result as string
      const tempImg = new Image()
      tempImg.onload = () => {
        const nw = tempImg.naturalWidth || 200
        const nh = tempImg.naturalHeight || 200
        setNaturalSize({ w: nw, h: nh })

        // Escala base: la imagen completa entra holgadamente en el círculo de 200px con zoom = 1.0
        const baseScale = 200 / Math.max(nw, nh)
        setBaseDimensions({
          w: Math.max(1, nw * baseScale),
          h: Math.max(1, nh * baseScale),
        })
        setZoom(1.0)
        setPan({ x: 0, y: 0 })
        setImageToCrop(dataUri)
        setCropMode(true)
        setError(null)
      }
      tempImg.src = dataUri
    }
    reader.readAsDataURL(file)
  }

  // Re-encuadrar imagen existente
  const handleRecenter = (url: string) => {
    const canonical = getAvatarUrl(url) || url
    const tempImg = new Image()
    tempImg.crossOrigin = 'anonymous'
    tempImg.onload = () => {
      const nw = tempImg.naturalWidth || 200
      const nh = tempImg.naturalHeight || 200
      setNaturalSize({ w: nw, h: nh })
      const baseScale = 200 / Math.max(nw, nh)
      setBaseDimensions({
        w: Math.max(1, nw * baseScale),
        h: Math.max(1, nh * baseScale),
      })
      setZoom(1.0)
      setPan({ x: 0, y: 0 })
      setImageToCrop(canonical)
      setCropMode(true)
      setError(null)
    }
    tempImg.onerror = () => {
      setError(language === 'es' ? 'No se pudo cargar la imagen para re-encuadrar.' : 'Could not load image to re-center.')
    }
    tempImg.src = canonical
  }

  // Restablecer al avatar por defecto
  const handleResetToDefault = async () => {
    setLoading(true)
    setError(null)
    try {
      const updated = await authService.deleteAvatar()
      updateUser(updated)
      setAvatarUrl('')
      setImageToCrop(null)
      setCropMode(false)
      setImgError(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al restablecer el avatar.')
    } finally {
      setLoading(false)
    }
  }

  // Mouse / Touch Dragging handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      setIsDragging(true)
      setDragStart({ x: e.touches[0].clientX - pan.x, y: e.touches[0].clientY - pan.y })
    }
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging || e.touches.length !== 1) return
    setPan({
      x: e.touches[0].clientX - dragStart.x,
      y: e.touches[0].clientY - dragStart.y,
    })
  }

  // Aplicar recorte y centrado en canvas 256x256 y subir a backend
  const handleApplyCrop = async () => {
    if (!imageRef.current) return
    setLoading(true)
    setError(null)

    try {
      const img = imageRef.current
      const canvas = document.createElement('canvas')
      canvas.width = 256
      canvas.height = 256
      const ctx = canvas.getContext('2d')

      if (!ctx) throw new Error('Could not initialize canvas context')

      // Relleno oscuro de respaldo para márgenes en caso de zoom out
      ctx.fillStyle = '#141414'
      ctx.fillRect(0, 0, 256, 256)

      // Relación exacta entre viewport (200x200) y canvas (256x256)
      const factor = 256 / 200
      const renderW = baseDimensions.w * zoom * factor
      const renderH = baseDimensions.h * zoom * factor
      const renderX = 128 + pan.x * factor - renderW / 2
      const renderY = 128 + pan.y * factor - renderH / 2

      ctx.drawImage(img, renderX, renderY, renderW, renderH)

      const croppedDataUri = canvas.toDataURL('image/jpeg', 0.92)

      // Guardar avatar vía endpoint dedicado
      const updated = await authService.uploadAvatar(croppedDataUri)
      updateUser(updated)
      setAvatarUrl(updated.avatar_url || croppedDataUri)
      setCropMode(false)
      setImageToCrop(null)
      setImgError(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al procesar el avatar.')
    } finally {
      setLoading(false)
    }
  }

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

  const canonicalCurrentAvatar = getAvatarUrl(avatarUrl)

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

        {cropMode && imageToCrop ? (
          <div className="space-y-4 animate-in fade-in">
            <div className="text-center space-y-1">
              <h4 className="text-sm font-bold text-white">
                {language === 'es' ? 'Ajustar y Centrar Avatar' : 'Adjust & Center Avatar'}
              </h4>
              <p className="text-xs text-gray-400">
                {language === 'es'
                  ? 'Arrastra la imagen para posicionarla y usa el zoom (in/out) para encuadrarla a gusto.'
                  : 'Drag the image to position and use zoom (in/out) to frame your avatar.'}
              </p>
            </div>

            {/* Viewport circular 200x200 con imagen escalada exactamente */}
            <div className="flex justify-center my-3">
              <div
                className="relative w-[200px] h-[200px] rounded-full overflow-hidden border-4 border-amber-500 shadow-2xl bg-[#0a0a0a] cursor-grab active:cursor-grabbing select-none shrink-0"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleMouseUp}
              >
                <img
                  ref={imageRef}
                  src={imageToCrop}
                  alt="Crop preview"
                  draggable={false}
                  className="absolute max-w-none pointer-events-none select-none"
                  style={{
                    width: `${baseDimensions.w * zoom}px`,
                    height: `${baseDimensions.h * zoom}px`,
                    left: '50%',
                    top: '50%',
                    transform: `translate(-50%, -50%) translate(${pan.x}px, ${pan.y}px)`,
                  }}
                />
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center border border-white/10 rounded-full">
                  <Move className="w-6 h-6 text-white/20" />
                </div>
              </div>
            </div>

            {/* Zoom Slider and Quick Presets */}
            <div className="space-y-2.5 max-w-sm mx-auto">
              <div className="flex items-center justify-center gap-3 px-4 py-2 bg-[#0d0d0d] border border-[#262626] rounded-xl">
                <button
                  type="button"
                  onClick={() => setZoom(Math.max(0.2, +(zoom - 0.15).toFixed(2)))}
                  className="text-gray-400 hover:text-white p-1 transition-colors"
                  title="Zoom out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <input
                  type="range"
                  min="0.2"
                  max="3.0"
                  step="0.05"
                  value={zoom}
                  onChange={(e) => setZoom(parseFloat(e.target.value))}
                  className="flex-1 accent-amber-500 cursor-pointer h-1.5 bg-[#262626] rounded-lg"
                />
                <button
                  type="button"
                  onClick={() => setZoom(Math.min(3.0, +(zoom + 0.15).toFixed(2)))}
                  className="text-gray-400 hover:text-white p-1 transition-colors"
                  title="Zoom in"
                >
                  <ZoomIn className="w-4 h-4 text-amber-400" />
                </button>
                <span className="text-[11px] font-mono font-bold text-gray-300 w-10 text-right">
                  {zoom.toFixed(1)}x
                </span>
              </div>

              {/* Botones de ajuste rápido: Ajustar completa, Llenar círculo, Centrar */}
              <div className="flex items-center justify-center gap-2 flex-wrap text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setZoom(1.0)
                    setPan({ x: 0, y: 0 })
                  }}
                  className="px-2.5 py-1 rounded-lg bg-[#1a1a1a] hover:bg-[#262626] text-gray-300 border border-[#333] text-[11px] font-medium transition-colors"
                >
                  {language === 'es' ? 'Ajustar Completa (1.0x)' : 'Fit Entire Image'}
                </button>
                {naturalSize.w > 0 && naturalSize.h > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      const fillScale = 200 / Math.min(naturalSize.w, naturalSize.h)
                      const baseScale = 200 / Math.max(naturalSize.w, naturalSize.h)
                      setZoom(+(fillScale / baseScale).toFixed(2))
                      setPan({ x: 0, y: 0 })
                    }}
                    className="px-2.5 py-1 rounded-lg bg-[#1a1a1a] hover:bg-[#262626] text-gray-300 border border-[#333] text-[11px] font-medium transition-colors"
                  >
                    {language === 'es' ? 'Llenar Círculo' : 'Fill Circle'}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setPan({ x: 0, y: 0 })}
                  className="px-2.5 py-1 rounded-lg bg-[#1a1a1a] hover:bg-[#262626] text-gray-400 hover:text-gray-200 border border-[#2b2b2b] text-[11px] transition-colors"
                >
                  {language === 'es' ? 'Centrar' : 'Center'}
                </button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-center gap-3 pt-3 border-t border-[#262626]">
              <button
                type="button"
                onClick={() => {
                  setCropMode(false)
                  setImageToCrop(null)
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-400 hover:text-white bg-[#1a1a1a] hover:bg-[#252525] border border-[#333] transition-all"
              >
                {language === 'es' ? 'Cancelar' : 'Cancel'}
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleApplyCrop}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all active:scale-95 disabled:opacity-50"
              >
                <Check className="w-4 h-4" />
                {loading
                  ? (language === 'es' ? 'Procesando...' : 'Processing...')
                  : (language === 'es' ? 'Aplicar y Guardar' : 'Apply & Save')}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Input file invisible */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept="image/png,image/jpeg,image/webp,image/jpg"
              className="hidden"
            />

            {/* Avatar Preview & Selection */}
            <div className="p-3.5 rounded-xl bg-[#0d0d0d] border border-[#262626] space-y-3">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-amber-500/50 bg-[#1f1f1f] flex items-center justify-center shrink-0 shadow-lg">
                  {canonicalCurrentAvatar && !imgError ? (
                    <img
                      src={canonicalCurrentAvatar}
                      alt="Avatar preview"
                      className="w-full h-full object-cover"
                      onError={() => setImgError(true)}
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-black text-xl font-extrabold">
                      {user.nombre_usuario.charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>

                <div className="flex-1 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                      {language === 'es' ? 'Foto de Perfil' : 'Profile Picture'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md shadow-amber-500/10 transition-all active:scale-95"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span>{language === 'es' ? 'Subir de mi PC' : 'Upload from PC'}</span>
                    </button>

                    {avatarUrl && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleRecenter(avatarUrl)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#222222] hover:bg-[#2a2a2a] text-gray-300 hover:text-white border border-[#333333] text-xs font-semibold transition-all"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>{language === 'es' ? 'Re-encuadrar' : 'Re-center'}</span>
                        </button>

                        <button
                          type="button"
                          disabled={loading}
                          onClick={handleResetToDefault}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/60 text-red-300 hover:text-red-200 border border-red-800/40 text-xs font-semibold transition-all disabled:opacity-50"
                          title={language === 'es' ? 'Eliminar avatar y volver al predeterminado' : 'Remove avatar and use default'}
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>{language === 'es' ? 'Volver a Default' : 'Default Avatar'}</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* URL alternativo */}
              <div className="pt-2 border-t border-[#1f1f1f]">
                <label className="block text-[10px] text-gray-400 mb-1">
                  {language === 'es' ? 'O bien pega un enlace directo de imagen (URL)' : 'Or paste a direct image URL'}
                </label>
                <div className="relative">
                  <ImageIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="url"
                    placeholder="https://example.com/your-photo.jpg"
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 bg-[#181818] border border-[#333333] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
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
      )}
      </div>
    </div>
  )
}
