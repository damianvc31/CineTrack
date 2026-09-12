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
              Your ultimate movie and TV series tracker, with intelligent AI-powered recommendations.
            </p>
          </div>

          {/* Col 2: Explore */}
          <div>
            <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider mb-3">Explore</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/catalog?tipo=movie" className="hover:text-amber-400 transition-colors">
                  Movies
                </Link>
              </li>
              <li>
                <Link to="/catalog?tipo=tv" className="hover:text-amber-400 transition-colors">
                  TV Series
                </Link>
              </li>
              <li>
                <Link to="/catalog?section=trending" className="hover:text-amber-400 transition-colors">
                  Trending
                </Link>
              </li>
              <li>
                <Link to="/catalog?section=classics" className="hover:text-amber-400 transition-colors">
                  Gems & Classics
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: My Space */}
          <div>
            <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider mb-3">My Space</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/library" className="hover:text-amber-400 transition-colors">
                  My Library
                </Link>
              </li>
              <li>
                <Link to="/library?tab=watchlist" className="hover:text-amber-400 transition-colors">
                  Watchlist
                </Link>
              </li>
              <li>
                <Link to="/library?tab=favoritos" className="hover:text-amber-400 transition-colors">
                  Favorites
                </Link>
              </li>
              <li>
                <Link to="/profile" className="hover:text-amber-400 transition-colors">
                  Stats & Profile
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Mandatory TMDB Attribution */}
          <div className="space-y-3 bg-gray-900/40 p-4 rounded-xl border border-gray-800/80">
            <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer" className="inline-block">
              <img src={tmdbLogo} alt="The Movie Database (TMDB)" className="h-4 w-auto object-contain" />
            </a>
            <p className="text-[11px] text-gray-400 leading-snug">
              This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.
            </p>
            <p className="text-[10px] text-gray-500">
              All metadata, posters and images are the property of their respective owners.
            </p>
          </div>
        </div>

        <div className="pt-6 border-t border-gray-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-500">
          <p>© {new Date().getFullYear()} CineTrack. Project developed for UTN E-Learning.</p>
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
