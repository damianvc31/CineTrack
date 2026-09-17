import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Search, Compass, Sparkles, User as UserIcon, LogOut, Menu, X, Heart, MessageSquare, Settings, Bell, Bookmark, Eye, PlaySquare } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import tmdbLogo from '@/assets/branding/tmdb-logo.svg'
import cinetrackLogo from '@/assets/branding/cinetrack-logo.svg'
import { getAvatarUrl } from '@/utils/avatarUtils'

interface HeaderProps {
  onOpenAuth?: (mode?: 'login' | 'register') => void
}

export const Header: React.FC<HeaderProps> = ({ onOpenAuth }) => {
  const { user, logout } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const isCatalog = location.pathname === '/catalog'
  const isHome = location.pathname === '/'

  const [searchQuery, setSearchQuery] = useState('')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [userDropdownOpen, setUserDropdownOpen] = useState(false)

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/catalog?q=${encodeURIComponent(searchQuery.trim())}`)
      setMobileMenuOpen(false)
      setSearchQuery('')
    }
  }

  return (
    <header className="sticky top-0 z-50 bg-[#0d0d0d]/95 backdrop-blur-md border-b border-[#262626] transition-all">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="relative flex items-center justify-between h-16 gap-4">
          {/* Logo CineTrack + Atribución TMDB */}
          <div className="flex items-center gap-3 shrink-0 z-10">
            <Link to="/" className="flex items-center gap-2.5 group">
              <img src={cinetrackLogo} alt="CineTrack" className="w-8 h-8 rounded-lg group-hover:scale-105 transition-transform" />
              <span className="font-bold text-xl tracking-tight text-white">
                Cine<span className="text-amber-500">Track</span>
              </span>
            </Link>

            {/* Badge Powered by TMDB */}
            <a
              href="https://www.themoviedb.org"
              target="_blank"
              rel="noopener noreferrer"
              title="Data provided by The Movie Database"
              className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#171717] border border-[#262626] hover:border-[#333333] transition-colors text-[10px] text-gray-400 hover:text-gray-200"
            >
              <span>Powered by</span>
              <img src={tmdbLogo} alt="TMDB" className="h-2.5 w-auto object-contain" />
            </a>
          </div>

          {/* Área Central: Botón Explore + Barra de Búsqueda (Fija al centro, oculta en /catalog) */}
          {!isCatalog && (
            <div className="hidden md:flex items-center justify-center gap-3 absolute left-1/2 -translate-x-1/2 w-full max-w-sm md:max-w-md lg:max-w-lg pointer-events-auto z-10">
              {/* Botón Explore Catálogo */}
              <Link
                to="/catalog"
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#171717] hover:bg-[#222222] border border-[#262626] text-gray-300 hover:text-white transition-all shrink-0"
              >
                <Compass className="w-3.5 h-3.5 text-amber-500" />
                <span>{t('catalog')}</span>
              </Link>

              {/* Barra de Búsqueda con X de limpieza */}
              <form onSubmit={handleSearchSubmit} className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t('searchPlaceholder')}
                  className="w-full pl-9 pr-8 py-1.5 text-xs bg-[#171717] border border-[#262626] rounded-full text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-0.5"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </form>
            </div>
          )}

          {/* Acciones de Usuario a la derecha */}
          <div className="flex items-center gap-3 shrink-0 z-10 ml-auto">
            {user ? (
              // En Home con usuario logueado: el header queda limpio a la derecha (el menú está en la columna derecha de Home)
              // En otras pantallas: muestra avatar + campanita + dropdown
              !isHome ? (
                <div className="flex items-center gap-2.5">
                  <button
                    type="button"
                    className="p-2 rounded-full text-amber-400/80 hover:text-amber-400 hover:bg-[#171717] transition-colors"
                    title="Notifications"
                  >
                    <Bell className="w-4 h-4" />
                  </button>

                  <div className="relative">
                    <button
                      onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                      className="group flex items-center gap-2.5 p-1 rounded-full hover:bg-[#1a1a1a] transition-all duration-200 cursor-pointer focus:outline-none"
                    >
                      <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-amber-500/50 bg-[#181818] flex items-center justify-center text-black text-sm font-bold shadow-md shrink-0 transition-all duration-200 group-hover:scale-105 group-hover:ring-2 group-hover:ring-amber-400/80 group-hover:border-amber-400 group-hover:shadow-lg group-hover:shadow-amber-500/20">
                        {getAvatarUrl(user.avatar_url) ? (
                          <img
                            src={getAvatarUrl(user.avatar_url)!}
                            alt={user.nombre_usuario}
                            className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
                            onError={(e) => {
                              ;(e.target as HTMLElement).style.display = 'none'
                            }}
                          />
                        ) : (
                          <div className="w-full h-full bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-black text-sm font-black">
                            {user.nombre_usuario.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                      <span className="hidden lg:inline text-xs font-semibold text-gray-200 group-hover:text-amber-300 transition-colors">
                        {user.nombre_usuario}
                      </span>
                    </button>

                    {userDropdownOpen && (
                      <div
                        className="absolute right-0 mt-2 w-52 bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl py-1.5 z-50 text-xs animate-in fade-in slide-in-from-top-2"
                        onMouseLeave={() => setUserDropdownOpen(false)}
                      >
                        <div className="px-4 py-2 border-b border-[#262626] text-[11px] text-gray-400">
                          {t('signedInAs')} <strong className="text-gray-200 block truncate">@{user.nombre_usuario}</strong>
                        </div>
                        <Link
                          to="/profile"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-gray-300 hover:text-white hover:bg-[#1f1f1f]"
                        >
                          <UserIcon className="w-4 h-4 text-amber-500" /> {t('profile')}
                        </Link>
                        <Link
                          to="/library?tab=favoritos"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-gray-300 hover:text-white hover:bg-[#1f1f1f]"
                        >
                          <Heart className="w-4 h-4 text-red-400" /> {t('favorites')}
                        </Link>
                        <Link
                          to="/library?tab=watchlist"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-gray-300 hover:text-white hover:bg-[#1f1f1f]"
                        >
                          <Bookmark className="w-4 h-4 text-amber-400" /> {t('watchlist')}
                        </Link>
                        <Link
                          to="/library?tab=vistas"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-gray-300 hover:text-white hover:bg-[#1f1f1f]"
                        >
                          <Eye className="w-4 h-4 text-emerald-400" /> {t('watchHistory')}
                        </Link>
                        <Link
                          to="/library?tab=siguiendo"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-gray-300 hover:text-white hover:bg-[#1f1f1f]"
                        >
                          <PlaySquare className="w-4 h-4 text-blue-400" /> {t('following')}
                        </Link>
                        <Link
                          to="/reviews"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-gray-300 hover:text-white hover:bg-[#1f1f1f]"
                        >
                          <MessageSquare className="w-4 h-4 text-amber-400" /> {t('reviews')}
                        </Link>
                        <Link
                          to="/settings"
                          onClick={() => setUserDropdownOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-gray-300 hover:text-white hover:bg-[#1f1f1f]"
                        >
                          <Settings className="w-4 h-4 text-gray-400" /> {t('settings')}
                        </Link>
                        <div className="border-t border-[#262626] my-1"></div>
                        <button
                          onClick={() => {
                            logout()
                            setUserDropdownOpen(false)
                          }}
                          className="w-full flex items-center gap-2.5 px-4 py-2 text-left text-red-400 hover:text-red-300 hover:bg-red-950/20"
                        >
                          <LogOut className="w-4 h-4" /> {t('signOut')}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : null
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onOpenAuth?.('login')}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-full text-gray-300 hover:text-white hover:bg-[#181818] border border-[#2a2a2a] hover:border-[#3a3a3a] transition-all active:scale-95"
                >
                  {t('logIn')}
                </button>
                <button
                  onClick={() => onOpenAuth?.('register')}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-full bg-amber-500 hover:bg-amber-400 text-black shadow-md shadow-amber-500/20 transition-all active:scale-95"
                >
                  {t('signUp')}
                </button>
              </div>
            )}

            {/* Toggle mobile menu */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#171717] md:hidden focus:outline-none"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Menú Mobile desplegable */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#0d0d0d] border-b border-[#262626] px-4 pt-2 pb-6 space-y-3">
          {!isCatalog && (
            <form onSubmit={handleSearchSubmit} className="relative mt-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('searchPlaceholder')}
                className="w-full pl-9 pr-8 py-2 text-sm bg-[#171717] border border-[#262626] rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-500"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-0.5"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </form>
          )}

          <nav className="flex flex-col space-y-1 pt-2">
            <Link
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className="px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
            >
              {t('home')}
            </Link>
            <Link
              to="/catalog"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-amber-400 hover:text-white hover:bg-[#171717]"
            >
              <Compass className="w-4 h-4 text-amber-500" /> {t('exploreCatalog')}
            </Link>
            <Link
              to="/recommendations"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-indigo-300 hover:bg-[#171717]"
            >
              <Sparkles className="w-4 h-4 text-amber-500" /> {t('aiAssistant')}
            </Link>

            {user && (
              <>
                <div className="border-t border-[#262626] my-2 pt-2">
                  <span className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('account')}</span>
                </div>
                <Link
                  to="/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
                >
                  <UserIcon className="w-4 h-4 text-amber-500" /> {t('profile')}
                </Link>
                <Link
                  to="/library?tab=favoritos"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
                >
                  <Heart className="w-4 h-4 text-red-400" /> {t('favorites')}
                </Link>
                <Link
                  to="/library?tab=watchlist"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
                >
                  <Bookmark className="w-4 h-4 text-amber-400" /> {t('watchlist')}
                </Link>
                <Link
                  to="/library?tab=vistas"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
                >
                  <Eye className="w-4 h-4 text-emerald-400" /> {t('watchHistory')}
                </Link>
                <Link
                  to="/library?tab=siguiendo"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
                >
                  <PlaySquare className="w-4 h-4 text-blue-400" /> {t('following')}
                </Link>
                <Link
                  to="/reviews"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
                >
                  <MessageSquare className="w-4 h-4 text-amber-400" /> {t('reviews')}
                </Link>
                <Link
                  to="/settings"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#171717]"
                >
                  <Settings className="w-4 h-4 text-gray-400" /> {t('settings')}
                </Link>
                <button
                  onClick={() => {
                    logout()
                    setMobileMenuOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-red-400 hover:bg-red-950/20 text-left"
                >
                  <LogOut className="w-4 h-4" /> {t('signOut')}
                </button>
              </>
            )}

            {!user && (
              <div className="pt-2 border-t border-[#262626] flex flex-col gap-2">
                <button
                  onClick={() => {
                    setMobileMenuOpen(false)
                    onOpenAuth?.('login')
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold rounded-xl text-gray-200 bg-[#171717] hover:bg-[#202020] border border-[#2e2e2e] text-center transition-colors"
                >
                  {t('logIn')}
                </button>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false)
                    onOpenAuth?.('register')
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-bold text-center shadow-md shadow-amber-500/20 transition-colors"
                >
                  {t('signUpRegister')}
                </button>
              </div>
            )}
          </nav>

          <div className="pt-2 border-t border-[#262626] flex items-center justify-between">
            <span className="text-[11px] text-gray-400">Data provided by</span>
            <img src={tmdbLogo} alt="TMDB" className="h-3 w-auto object-contain" />
          </div>
        </div>
      )}
    </header>
  )
}
