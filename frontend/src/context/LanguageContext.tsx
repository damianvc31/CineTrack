import React, { createContext, useContext, useState, useEffect } from 'react'
import { translateGenre } from '@/utils/genreTranslations'

export type Language = 'en' | 'es'

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string, defaultText?: string) => string
  translateGenreName: (genreName: string) => string
}

const UI_STRINGS: Record<string, { en: string; es: string }> = {
  // Navigation & Header
  home: { en: 'Home', es: 'Inicio' },
  movies: { en: 'Movies', es: 'Películas' },
  series: { en: 'Series', es: 'Series' },
  all: { en: 'All', es: 'Todos' },
  catalog: { en: 'Explore', es: 'Explorar' },
  exploreCatalog: { en: 'Explore', es: 'Explorar' },
  exploreCatalogHeading: { en: 'Explore Catalog', es: 'Explorar Catálogo' },
  aiAssistant: { en: 'AI Assistant', es: 'Asistente IA' },
  searchPlaceholder: {
    en: 'Search titles, actors, directors, writers...',
    es: 'Buscar títulos, actores, directores, guionistas...'
  },
  logIn: { en: 'Log In', es: 'Iniciar Sesión' },
  signUp: { en: 'Sign Up', es: 'Registrarse' },
  signUpRegister: { en: 'Sign Up / Register', es: 'Registrarse' },
  createAccount: { en: 'Create Account', es: 'Crear Cuenta' },
  signOut: { en: 'Sign Out', es: 'Cerrar Sesión' },
  signedInAs: { en: 'Signed in as', es: 'Conectado como' },
  account: { en: 'Account', es: 'Cuenta' },

  // Catalog Page
  titlesFound: { en: 'titles found', es: 'títulos encontrados' },
  filterAndDiscover: { en: 'Filter and discover', es: 'Filtra y descubre' },
  searchCatalogPlaceholder: {
    en: 'Search titles, actors, directors, writers...',
    es: 'Buscar títulos, actores, directores, guionistas...'
  },
  clearSearch: { en: 'Clear search', es: 'Limpiar búsqueda' },
  filtersLabel: { en: 'Filters:', es: 'Filtros:' },
  allTypes: { en: 'All types', es: 'Todos los tipos' },
  allGenres: { en: 'All genres', es: 'Todos los géneros' },
  allSections: { en: 'All sections', es: 'Todas las secciones' },
  sectionTrending: { en: '📈 Trending Now', es: '📈 Tendencias Ahora' },
  sectionNewReleases: { en: '🕒 New Releases', es: '🕒 Nuevos Lanzamientos' },
  sectionClassics: { en: '💎 Classics', es: '💎 Clásicos' },
  sectionTopRated: { en: '⭐ Top Rated', es: '⭐ Mejor Calificados' },
  sortPopularity: { en: 'Popularity', es: 'Popularidad' },
  sortRating: { en: 'Rating', es: 'Calificación' },
  sortReleaseDate: { en: 'Release Date', es: 'Fecha de estreno' },
  sortTitle: { en: 'Title (A-Z)', es: 'Título (A-Z)' },
  loadingResults: { en: 'Loading results...', es: 'Cargando resultados...' },
  noTitlesFound: { en: 'No titles found', es: 'No se encontraron títulos' },
  noTitlesFilterDesc: {
    en: 'No titles match the selected filters. Try resetting filters or searching with another term.',
    es: 'No hay títulos que coincidan con los filtros seleccionados. Intenta restablecer los filtros o buscar con otro término.'
  },
  clearFilters: { en: 'Clear filters', es: 'Restablecer filtros' },
  clearAll: { en: 'Clear all', es: 'Limpiar todo' },
  countriesFilter: { en: 'Country', es: 'País' },
  languagesFilter: { en: 'Language', es: 'Idioma' },
  genresFilter: { en: 'Genres', es: 'Géneros' },
  matchMode: { en: 'Match', es: 'Coincidir' },
  matchAny: { en: 'Any (OR)', es: 'Cualquiera (OR)' },
  matchAll: { en: 'All (AND)', es: 'Todos (AND)' },
  searchCountriesPlaceholder: { en: 'Search country...', es: 'Buscar país...' },
  searchLanguagesPlaceholder: { en: 'Search language...', es: 'Buscar idioma...' },
  searchGenresPlaceholder: { en: 'Search genre...', es: 'Buscar género...' },
  activeFilters: { en: 'Active filters', es: 'Filtros activos' },
  noOptionsFound: { en: 'No options found', es: 'No se encontraron opciones' },
  selectedCount: { en: 'selected', es: 'seleccionados' },
  previous: { en: 'Previous', es: 'Anterior' },
  next: { en: 'Next', es: 'Siguiente' },
  pageLabel: { en: 'Page', es: 'Página' },
  ofLabel: { en: 'of', es: 'de' },

  // Library & Profile 7 Sections
  profile: { en: 'Profile', es: 'Perfil' },
  favorites: { en: 'Favorites', es: 'Favoritos' },
  watchlist: { en: 'Watchlist', es: 'Lista de seguimiento' },
  watchHistory: { en: 'Watch History', es: 'Historial' },
  following: { en: 'Following', es: 'Siguiendo' },
  reviews: { en: 'Reviews', es: 'Reseñas' },
  settings: { en: 'Settings', es: 'Configuración' },

  // Home Page
  trendingNow: { en: 'Trending Now', es: 'Tendencias' },
  newReleases: { en: 'New Releases', es: 'Estrenos Recientes' },
  allTimeClassics: { en: 'All-Time Classics', es: 'Clásicos de Siempre' },
  topRated: { en: 'Top Rated', es: 'Mejor Calificados' },
  yourPersonalCineTrack: { en: 'Your Personal CineTrack', es: 'Tu CineTrack Personal' },
  signInPrompt: {
    en: 'Sign in to save favorites, build your watchlist, and track series episodes.',
    es: 'Inicia sesión para guardar favoritos, armar tus listas y seguir episodios.'
  },

  // Profile Page
  statistics: { en: 'Statistics', es: 'Estadísticas' },
  totalHours: { en: 'Total Hours', es: 'Horas Totales' },
  moviesWatched: { en: 'Movies Watched', es: 'Películas Vistas' },
  seriesWatched: { en: 'Series Watched', es: 'Series Vistas' },
  moviesLabel: { en: 'Movies', es: 'Películas' },
  seriesLabel: { en: 'Series', es: 'Series' },
  avgMoviesPerWeek: { en: 'movies / week', es: 'películas / sem.' },
  seasonsCompletedText: { en: 'completed', es: 'completadas' },
  top5Popularity: { en: 'Top 5 Watched by Popularity', es: 'Top 5 Más Vistas por Popularidad' },
  top5Rating: { en: 'Top 5 Watched by Average Rating', es: 'Top 5 Más Vistas por Calificación Promedio' },
  top5MyRating: { en: 'Top 5 Watched by My Rating', es: 'Top 5 Más Vistas por Mi Calificación' },
  genresWatched: { en: 'Genres Watched', es: 'Géneros Vistos' },
  titlesCountCenter: { en: 'TITLES', es: 'TÍTULOS' },
  recentlyWatched: { en: 'Recently Watched', es: 'Vistos Recientemente' },
  viewAll: { en: 'View All', es: 'Ver Todos' },
  editProfile: { en: 'Edit Profile', es: 'Editar Perfil' },
  memberSince: { en: 'Member since', es: 'Miembro desde' },
  noWatchedTitles: { en: 'No watched titles yet.', es: 'Aún no hay títulos vistos.' },
  noRatedTitles: { en: 'No rated titles yet.', es: 'Aún no hay títulos calificados.' },

  // Settings Page
  settingsHeading: { en: 'Settings', es: 'Configuración' },
  settingsSubtitle: {
    en: 'Manage your account security and interface preferences',
    es: 'Administra la seguridad de tu cuenta y preferencias de interfaz'
  },
  securityPassword: { en: 'Security & Password', es: 'Seguridad y Contraseña' },
  currentPassword: { en: 'Current Password', es: 'Contraseña Actual' },
  newPassword: { en: 'New Password', es: 'Nueva Contraseña' },
  confirmPassword: { en: 'Confirm New Password', es: 'Confirmar Nueva Contraseña' },
  updatePassword: { en: 'Update Password', es: 'Actualizar Contraseña' },
  interfacePreferences: { en: 'Interface Preferences', es: 'Preferencias de Interfaz' },
  interfaceLanguage: { en: 'Interface Language', es: 'Idioma de la Interfaz' },
  interfaceLanguageDesc: {
    en: 'Select your preferred language for menus, navigation, and genre classifications.',
    es: 'Elige tu idioma preferido para menús, navegación y clasificación de géneros.'
  },
  preferencesSaved: { en: 'Preferences saved successfully.', es: 'Preferencias guardadas exitosamente.' },

  // Library Page
  myLibrary: { en: 'My Library', es: 'Mi Biblioteca' },
  manageSavedDesc: { en: 'Manage your saved movies and series', es: 'Administra tus películas y series guardadas' },
  watched: { en: 'Watched', es: 'Vistas' },
  allFilter: { en: 'All Titles', es: 'Todos los Títulos' },
  moviesFilter: { en: 'Movies', es: 'Películas' },
  seriesFilter: { en: 'Series', es: 'Series' },
  signInToViewLibrary: { en: 'Sign in to view your library', es: 'Inicia sesión para ver tu biblioteca' },
  librarySignInDesc: {
    en: 'Save your favorite titles, manage watchlists, and track series episode progress across devices.',
    es: 'Guarda tus títulos favoritos, administra tus listas y sigue el progreso de tus episodios en todos tus dispositivos.'
  },
  loadingLibrary: { en: 'Loading titles from your library...', es: 'Cargando títulos de tu biblioteca...' },
  noTitlesInSection: { en: 'No titles in this section', es: 'No hay títulos en esta sección' },
  exploreLibraryPrompt: {
    en: 'Explore the catalog or trending titles to add movies and series to your library.',
    es: 'Explora el catálogo o las tendencias para agregar películas y series a tu biblioteca.'
  },

  // Reviews Page
  myReviews: { en: 'My Reviews', es: 'Mis Reseñas' },
  pendingReviews: { en: 'Pending Reviews', es: 'Reseñas Pendientes' },
  signInToManageReviews: { en: 'Sign in to manage your reviews', es: 'Inicia sesión para administrar tus reseñas' },
  reviewsSignInDesc: {
    en: 'Track all your written opinions, edit ratings, and review titles you have already watched.',
    es: 'Consulta todas tus opiniones, edita calificaciones y reseña los títulos que ya viste.'
  },

  // AI Recommender Page
  recommendationsNav: { en: 'AI Recommendations', es: 'Recomendaciones IA' },
  aiRecommenderTitle: { en: 'AI Recommender', es: 'Recomendador Inteligente con IA' },
  aiRecommenderSubtitle: {
    en: 'Describe what you feel like watching and our AI will handpick the best matches from the catalog.',
    es: 'Describe qué tienes ganas de ver y nuestra IA seleccionará las mejores opciones de nuestro catálogo.'
  },
  aiWhyRecommended: { en: 'Why we recommend it:', es: 'Por qué te la recomendamos:' },
  aiGuestTip: {
    en: 'Sign in or register to let CineTrack tailor recommendations to your favorites and watch history!',
    es: '¡Iniciá sesión o registrate para que CineTrack adapte las recomendaciones a tus favoritos e historial!'
  },
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('cinetrack_lang')
    return saved === 'es' ? 'es' : 'en'
  })

  useEffect(() => {
    localStorage.setItem('cinetrack_lang', language)
  }, [language])

  const setLanguage = (newLang: Language) => {
    setLanguageState(newLang)
  }

  const t = (key: string, defaultText?: string): string => {
    const entry = UI_STRINGS[key]
    if (entry && entry[language]) {
      return entry[language]
    }
    return defaultText ?? key
  }

  const translateGenreName = (genreName: string): string => {
    return translateGenre(genreName, language)
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, translateGenreName }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}
