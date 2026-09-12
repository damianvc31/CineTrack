import React from 'react'
import { Link } from 'react-router-dom'
import tmdbLogo from '@/assets/branding/tmdb-logo.svg'
import cinetrackLogo from '@/assets/branding/cinetrack-logo.svg'

export const Footer: React.FC = () => {
  return (
    <footer className="bg-[#080b12] border-t border-gray-800/60 mt-16 py-12 text-sm text-gray-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Col 1: CineTrack Brand */}
          <div className="space-y-3">
            <div className="flex items-center gap-2.5">
              <img src={cinetrackLogo} alt="CineTrack" className="w-7 h-7 rounded-md" />
              <span className="font-bold text-lg text-white">CineTrack</span>
            </div>
            <p className="text-xs text-gray-400 leading-relaxed">
              Tu centro definitivo de seguimiento de películas y series, con recomendaciones inteligentes potenciadas por IA.
            </p>
          </div>

          {/* Col 2: Explorar */}
          <div>
            <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider mb-3">Explorar</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/catalog?tipo=movie" className="hover:text-purple-400 transition-colors">
                  Películas
                </Link>
              </li>
              <li>
                <Link to="/catalog?tipo=tv" className="hover:text-purple-400 transition-colors">
                  Series de TV
                </Link>
              </li>
              <li>
                <Link to="/catalog?section=trending" className="hover:text-purple-400 transition-colors">
                  Tendencias
                </Link>
              </li>
              <li>
                <Link to="/catalog?section=classics" className="hover:text-purple-400 transition-colors">
                  Joyas y Clásicos
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Mi Espacio */}
          <div>
            <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider mb-3">Mi Espacio</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/library" className="hover:text-purple-400 transition-colors">
                  Mi Biblioteca
                </Link>
              </li>
              <li>
                <Link to="/library?tab=watchlist" className="hover:text-purple-400 transition-colors">
                  Por Ver (Watchlist)
                </Link>
              </li>
              <li>
                <Link to="/library?tab=favoritos" className="hover:text-purple-400 transition-colors">
                  Favoritos
                </Link>
              </li>
              <li>
                <Link to="/profile" className="hover:text-purple-400 transition-colors">
                  Estadísticas y Reseñas
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Atribución TMDB Obligatoria */}
          <div className="space-y-3 bg-gray-900/40 p-4 rounded-xl border border-gray-800/80">
            <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer" className="inline-block">
              <img src={tmdbLogo} alt="The Movie Database (TMDB)" className="h-4 w-auto object-contain" />
            </a>
            <p className="text-[11px] text-gray-400 leading-snug">
              This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.
            </p>
            <p className="text-[10px] text-gray-500">
              Todos los metadatos, pósters e imágenes son propiedad de sus respectivos dueños.
            </p>
          </div>
        </div>

        <div className="pt-6 border-t border-gray-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-500">
          <p>© {new Date().getFullYear()} CineTrack. Proyecto desarrollado para UTN E-Learning.</p>
          <div className="flex items-center gap-4">
            <span>React 19 + FastAPI</span>
            <span>•</span>
            <span>Mobile-First Responsive</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
