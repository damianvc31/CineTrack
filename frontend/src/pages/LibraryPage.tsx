import React, { useEffect, useState, useCallback } from 'react'
import { useSearchParams, Link, useOutletContext } from 'react-router-dom'
import { Bookmark, Heart, Play, CheckCircle2, AlertCircle } from 'lucide-react'
import { catalogService } from '@/services/catalogService'
import { useAuth } from '@/context/AuthContext'
import { TitleCard } from '@/components/common/TitleCard'
import type { UserLibrary, TitleCard as TitleCardType } from '@/types/catalog'

interface OutletContextType {
  openAuth: () => void
}

export const LibraryPage: React.FC = () => {
  const { user } = useAuth()
  const { openAuth } = useOutletContext<OutletContextType>()
  const [searchParams, setSearchParams] = useSearchParams()

  const tab = searchParams.get('tab') || 'favoritos'
  const [data, setData] = useState<UserLibrary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadLibrary = useCallback(async () => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const res = await catalogService.getLibrary()
      setData(res)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Error al cargar la biblioteca.')
      }
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (!user) {
      setLoading(false)
    } else {
      loadLibrary()
    }
  }, [user, loadLibrary])

  const setTab = (newTab: string) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', newTab)
    setSearchParams(next)
  }

  if (!user) {
    return (
      <div className="max-w-md mx-auto my-24 p-8 bg-[#111827] border border-gray-800 rounded-2xl text-center space-y-4">
        <Bookmark className="w-12 h-12 text-purple-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Inicia sesión para ver tu biblioteca</h2>
        <p className="text-xs text-gray-400">
          Guarda tus títulos favoritos, administra tus listas de seguimiento y sincroniza tu progreso en todos tus dispositivos.
        </p>
        <button
          onClick={openAuth}
          className="px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30"
        >
          Iniciar Sesión
        </button>
      </div>
    )
  }

  // Determinar los items de la pestaña activa
  let currentItems: TitleCardType[] = []
  if (data) {
    if (tab === 'favoritos') currentItems = data.favorites || []
    else if (tab === 'watchlist') currentItems = data.watchlist || []
    else if (tab === 'siguiendo') currentItems = data.following || []
    else if (tab === 'vistas') currentItems = data.recently_watched || []
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Encabezado */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <Bookmark className="w-7 h-7 text-purple-400" /> Mi Biblioteca
        </h1>
        <p className="text-xs text-gray-400 mt-1">Gestiona tus películas y series guardadas</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-800 pb-3 mb-8 overflow-x-auto no-scrollbar">
        {[
          { id: 'favoritos', label: `Favoritos (${data?.favorites?.length || 0})`, icon: Heart },
          { id: 'watchlist', label: `Por Ver (${data?.watchlist?.length || 0})`, icon: Bookmark },
          { id: 'siguiendo', label: `Siguiendo (${data?.following?.length || 0})`, icon: Play },
          { id: 'vistas', label: `Vistas (${data?.recently_watched?.length || 0})`, icon: CheckCircle2 },
        ].map((t) => {
          const Icon = t.icon
          const active = tab === t.id
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                active
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-600/20'
                  : 'bg-gray-900 text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{t.label}</span>
            </button>
          )
        })}
      </div>

      {/* Contenido */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <div className="w-10 h-10 border-4 border-purple-500/20 border-t-purple-500 rounded-full animate-spin" />
          <p className="text-xs text-gray-400">Cargando títulos de tu biblioteca...</p>
        </div>
      ) : error ? (
        <div className="p-8 text-center bg-gray-900/50 rounded-2xl border border-gray-800">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm text-gray-300">{error}</p>
        </div>
      ) : currentItems.length === 0 ? (
        <div className="p-16 text-center bg-gray-900/30 rounded-2xl border border-gray-800/60 max-w-lg mx-auto">
          <Bookmark className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white mb-1">No tienes títulos en esta sección</h3>
          <p className="text-xs text-gray-400 mb-6">
            Explora el catálogo o las tendencias para agregar producciones a tu lista.
          </p>
          <Link
            to="/catalog"
            className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30"
          >
            Explorar Catálogo
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 sm:gap-6">
          {currentItems.map((item) => (
            <div key={`${item.tipo}-${item.id}`} className="flex justify-center">
              <TitleCard
                title={item}
                onStateChange={loadLibrary}
                onOpenAuth={openAuth}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
