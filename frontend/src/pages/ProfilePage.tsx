import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Film,
  Tv,
  Clock,
  LogOut,
  AlertCircle,
  Play,
} from 'lucide-react'
import { catalogService } from '@/services/catalogService'
import { useAuth } from '@/context/AuthContext'
import type { UserStats } from '@/types/catalog'

export const ProfilePage: React.FC = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      navigate('/')
      return
    }

    const fetchStats = async () => {
      setLoading(true)
      try {
        const data = await catalogService.getStats()
        setStats(data)
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message)
        } else {
          setError('Error al obtener estadísticas del perfil')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [user, navigate])

  if (!user) return null

  const horasTotales = stats ? Math.round(stats.total_hours) : 0
  const diasTotales = (horasTotales / 24).toFixed(1)

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Header del Perfil */}
      <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 p-6 sm:p-8 rounded-2xl bg-[#111827] border border-gray-800">
        <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white text-3xl font-extrabold shadow-xl shadow-purple-900/30 shrink-0">
          {user.nombre_usuario.charAt(0).toUpperCase()}
        </div>

        <div className="flex-1 text-center sm:text-left space-y-2">
          <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-white">{user.nombre_usuario}</h1>
            {user.es_admin && (
              <span className="px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-[10px] font-bold uppercase tracking-wider">
                Administrador
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-gray-400">
            {user.pais ? `${user.ciudad ? `${user.ciudad}, ` : ''}${user.pais}` : 'Usuario Registrado'}
          </p>
          <p className="text-[11px] text-gray-500">
            Miembro desde {user.fecha_registro ? new Date(user.fecha_registro).toLocaleDateString() : 'reciente'}
          </p>
        </div>

        <button
          onClick={() => {
            logout()
            navigate('/')
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-950/40 hover:bg-red-900/50 border border-red-800/60 text-red-400 hover:text-red-300 text-xs font-semibold transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Cerrar sesión</span>
        </button>
      </div>

      {/* Grid de Estadísticas */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white">Tus Estadísticas de Reproducción</h2>

        {loading ? (
          <div className="p-12 text-center text-xs text-gray-400">Cargando métricas...</div>
        ) : error ? (
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800 flex items-center gap-3 text-xs text-red-400">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        ) : stats ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {/* Películas vistas */}
            <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800/80 space-y-1">
              <div className="flex items-center justify-between text-purple-400 mb-2">
                <Film className="w-5 h-5" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">Cine</span>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white">
                {stats.movies_watched_count}
              </div>
              <p className="text-xs text-gray-400">Películas vistas ({Math.round(stats.movie_hours)}h)</p>
            </div>

            {/* Episodios vistos */}
            <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800/80 space-y-1">
              <div className="flex items-center justify-between text-indigo-400 mb-2">
                <Tv className="w-5 h-5" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">TV</span>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white">
                {stats.episodes_watched_count}
              </div>
              <p className="text-xs text-gray-400">Episodios vistos ({Math.round(stats.tv_hours)}h)</p>
            </div>

            {/* Series completadas */}
            <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800/80 space-y-1">
              <div className="flex items-center justify-between text-emerald-400 mb-2">
                <Play className="w-5 h-5" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">Series</span>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white">
                {stats.series_watched_count}
              </div>
              <p className="text-xs text-gray-400">Series completadas</p>
            </div>

            {/* Tiempo invertido */}
            <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800/80 space-y-1">
              <div className="flex items-center justify-between text-amber-400 mb-2">
                <Clock className="w-5 h-5" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">Total</span>
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white">
                {horasTotales}h
              </div>
              <p className="text-xs text-gray-400">Aprox. {diasTotales} días de contenido</p>
            </div>
          </div>
        ) : null}
      </div>

      {/* Accesos Rápidos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          to="/library?tab=watchlist"
          className="p-5 rounded-2xl bg-[#111827] border border-gray-800 hover:border-purple-500/40 transition-colors flex items-center justify-between group"
        >
          <div>
            <h3 className="text-sm font-bold text-white group-hover:text-purple-400 transition-colors">
              Lista de Seguimiento (Watchlist)
            </h3>
            <p className="text-xs text-gray-400 mt-1">Revisa los títulos que tienes pendientes de ver</p>
          </div>
          <span className="text-xs font-semibold text-purple-400">Ver lista →</span>
        </Link>

        <Link
          to="/catalog"
          className="p-5 rounded-2xl bg-[#111827] border border-gray-800 hover:border-purple-500/40 transition-colors flex items-center justify-between group"
        >
          <div>
            <h3 className="text-sm font-bold text-white group-hover:text-purple-400 transition-colors">
              Explorar Catálogo General
            </h3>
            <p className="text-xs text-gray-400 mt-1">Descubre más películas y series para tu colección</p>
          </div>
          <span className="text-xs font-semibold text-purple-400">Explorar →</span>
        </Link>
      </div>
    </div>
  )
}
