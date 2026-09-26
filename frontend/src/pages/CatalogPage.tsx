import React, { useState, useCallback, useMemo } from 'react'
import { useSearchParams, useOutletContext } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Filter, Search, ChevronLeft, ChevronRight, Film, Tv, Sparkles, AlertCircle, X, RotateCcw, Compass, User, CalendarClock } from 'lucide-react'
import { catalogService, type TitlesResponse } from '@/services/catalogService'
import { TitleCard } from '@/components/common/TitleCard'
import { CountryFlag } from '@/components/common/CountryFlag'
import { MultiSelectDropdown, type MultiSelectOption } from '@/components/common/MultiSelectDropdown'
import { useLanguage } from '@/context/LanguageContext'
import { getCountryName, getLanguageName } from '@/utils/countryUtils'

interface OutletContextType {
  openAuth: (mode?: 'login' | 'register') => void
}

export const CatalogPage: React.FC = () => {
  const { openAuth } = useOutletContext<OutletContextType>()
  const { language, t, translateGenreName } = useLanguage()
  const [searchParams, setSearchParams] = useSearchParams()

  // Metadatos con caché global (60 min)
  const { data: genresData } = useQuery({
    queryKey: ['genres'],
    queryFn: async () => {
      const res = await catalogService.getGenres()
      return res.map((g) => (typeof g === 'string' ? g : g.nombre))
    },
    staleTime: 60 * 60 * 1000,
  })
  const genres = genresData || []

  const { data: countriesData } = useQuery({
    queryKey: ['countries'],
    queryFn: () => catalogService.getCountries(),
    staleTime: 60 * 60 * 1000,
  })
  const countries = countriesData || []

  const { data: languagesData } = useQuery({
    queryKey: ['languages'],
    queryFn: () => catalogService.getLanguages(),
    staleTime: 60 * 60 * 1000,
  })
  const languages = languagesData || []

  // Extraer parámetros de la URL
  const query = searchParams.get('q') || ''
  const tipo = (searchParams.get('tipo') as 'movie' | 'tv') || undefined
  const upcoming = searchParams.get('upcoming') === 'true'
  const section = (!upcoming && (searchParams.get('section') as any)) || undefined
  const actor = searchParams.get('actor') || undefined
  const rawSort = searchParams.get('sort_by')
  const rawOrder = searchParams.get('order')
  const sortBy = (rawSort as any) || (upcoming ? 'release_date' : section === 'top_rated' ? 'rating' : section === 'new_releases' ? 'release_date' : 'popularity')
  const order = (rawOrder as any) || (upcoming && !rawSort ? 'asc' : 'desc')
  const page = parseInt(searchParams.get('page') || '1', 10)

  // Multi-select filters parsing (con desglose automático de duplas de géneros)
  const selectedGenres = useMemo(() => {
    const raw = searchParams.get('generos') || searchParams.get('genero') || ''
    if (!raw) return []
    const parsed = raw.split(',').map((g) => g.trim()).filter(Boolean)
    const expanded: string[] = []
    for (const g of parsed) {
      const lower = g.toLowerCase()
      if (lower === 'sci-fi & fantasy' || lower === 'science fiction & fantasy') {
        expanded.push('Sci-Fi', 'Fantasy')
      } else if (lower === 'action & adventure') {
        expanded.push('Action', 'Adventure')
      } else if (lower === 'war & politics') {
        expanded.push('War')
      } else {
        expanded.push(g)
      }
    }
    return Array.from(new Set(expanded))
  }, [searchParams])

  const genreOp = (searchParams.get('genre_op') as 'or' | 'and') || 'or'

  const selectedCountries = useMemo(() => {
    const raw = searchParams.get('paises') || searchParams.get('pais') || ''
    return raw ? raw.split(',').map((c) => c.trim().toUpperCase()).filter(Boolean) : []
  }, [searchParams])

  const selectedLanguages = useMemo(() => {
    const raw = searchParams.get('idiomas') || searchParams.get('idioma') || ''
    return raw ? raw.split(',').map((l) => l.trim().toLowerCase()).filter(Boolean) : []
  }, [searchParams])

  // Input local para búsqueda de texto
  const [searchInput, setSearchInput] = useState(query)



  // Nombres localizados para países e idiomas
  const getCountryLabel = useCallback(
    (code: string) => getCountryName(code, language),
    [language]
  )

  const getLanguageLabel = useCallback(
    (code: string) => getLanguageName(code, language),
    [language]
  )

  const getSectionLabel = useCallback(
    (sec: string) => {
      const map: Record<string, string> = {
        trending: 'sectionTrending',
        new_releases: 'sectionNewReleases',
        classics: 'sectionClassics',
        top_rated: 'sectionTopRated',
      }
      return t(map[sec] || sec)
    },
    [t]
  )

  // Opciones formateadas para dropdowns
  const genreOptions = useMemo<MultiSelectOption[]>(() => {
    return genres
      .map((g) => ({
        value: g,
        label: translateGenreName(g),
      }))
      .sort((a, b) => a.label.localeCompare(b.label))
  }, [genres, translateGenreName])

  const countryOptions = useMemo<MultiSelectOption[]>(() => {
    return countries
      .map((c) => ({
        value: c.code,
        label: getCountryLabel(c.code),
        count: c.count,
        icon: <CountryFlag code={c.code} className="w-4 h-3 shrink-0" />,
      }))
      .sort((a, b) => a.label.localeCompare(b.label))
  }, [countries, getCountryLabel])

  const languageOptions = useMemo<MultiSelectOption[]>(() => {
    return languages
      .map((l) => ({
        value: l.code,
        label: getLanguageLabel(l.code),
        count: l.count,
      }))
      .sort((a, b) => a.label.localeCompare(b.label))
  }, [languages, getLanguageLabel])

  const catalogFilters = useMemo(
    () => ({
      q: query || undefined,
      tipo,
      section: upcoming ? undefined : section,
      upcoming: upcoming || undefined,
      generos: selectedGenres.length > 0 ? selectedGenres : undefined,
      genre_op: genreOp,
      paises: selectedCountries.length > 0 ? selectedCountries : undefined,
      idiomas: selectedLanguages.length > 0 ? selectedLanguages : undefined,
      actor,
      sort_by: sortBy,
      order,
      page,
      page_size: 24,
    }),
    [query, tipo, section, upcoming, selectedGenres, genreOp, selectedCountries, selectedLanguages, actor, sortBy, order, page]
  )

  const {
    data,
    isLoading: loading,
    error: queryError,
  } = useQuery<TitlesResponse>({
    queryKey: ['catalog', catalogFilters],
    queryFn: () => catalogService.getTitles(catalogFilters),
  })

  const error = queryError ? (queryError instanceof Error ? queryError.message : 'Error al consultar el catálogo') : null

  const handleCardStateChange = (_action: 'favorite' | 'watchlist' | 'watched') => {
    // Las mutaciones optimistas de useTitleMutations ya actualizan la caché en memoria instantáneamente
  }

  const updateParam = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(searchParams)
    if (value) {
      next.set(key, value)
    } else {
      next.delete(key)
    }
    next.set('page', '1') // Reset page on filter change
    setSearchParams(next)
  }

  const handleUpcomingToggle = (enabled: boolean) => {
    const next = new URLSearchParams(searchParams)
    if (enabled) {
      next.set('upcoming', 'true')
      next.delete('section')
      // Por defecto ordenar del más próximo al más lejano (release_date asc),
      // salvo que el usuario ya tenga configurado un orden explícito no default
      if (!rawSort || rawSort === 'popularity') {
        next.set('sort_by', 'release_date')
        next.set('order', 'asc')
      }
    } else {
      next.delete('upcoming')
      if (rawSort === 'release_date' && rawOrder === 'asc') {
        next.delete('sort_by')
        next.delete('order')
      }
    }
    next.set('page', '1')
    setSearchParams(next)
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateParam('q', searchInput.trim() || undefined)
  }

  const handleGenresChange = (newValues: string[]) => {
    const next = new URLSearchParams(searchParams)
    next.delete('genero')
    if (newValues.length > 0) {
      next.set('generos', newValues.join(','))
    } else {
      next.delete('generos')
      next.delete('genre_op')
    }
    next.set('page', '1')
    setSearchParams(next)
  }

  const handleGenreOpChange = (newOp: string) => {
    const next = new URLSearchParams(searchParams)
    if (newOp === 'and') {
      next.set('genre_op', 'and')
    } else {
      next.delete('genre_op')
    }
    next.set('page', '1')
    setSearchParams(next)
  }

  const handleCountriesChange = (newValues: string[]) => {
    const next = new URLSearchParams(searchParams)
    next.delete('pais')
    if (newValues.length > 0) {
      next.set('paises', newValues.join(','))
    } else {
      next.delete('paises')
    }
    next.set('page', '1')
    setSearchParams(next)
  }

  const handleLanguagesChange = (newValues: string[]) => {
    const next = new URLSearchParams(searchParams)
    next.delete('idioma')
    if (newValues.length > 0) {
      next.set('idiomas', newValues.join(','))
    } else {
      next.delete('idiomas')
    }
    next.set('page', '1')
    setSearchParams(next)
  }

  const handleClearAllFilters = () => {
    const next = new URLSearchParams()
    if (sortBy !== 'popularity' && !upcoming) next.set('sort_by', sortBy)
    if (order !== 'desc' && !upcoming) next.set('order', order)
    setSearchInput('')
    setSearchParams(next)
  }

  const setPage = (newPage: number) => {
    const next = new URLSearchParams(searchParams)
    next.set('page', newPage.toString())
    setSearchParams(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const hasActiveFilters = Boolean(
    query ||
    actor ||
    tipo ||
    upcoming ||
    section ||
    selectedGenres.length > 0 ||
    selectedCountries.length > 0 ||
    selectedLanguages.length > 0
  )

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Title and Main Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-6 border-b border-[#262626]">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
            {tipo === 'movie' ? (
              <>
                <Film className="w-7 h-7 text-amber-400" /> {t('movies')}
              </>
            ) : tipo === 'tv' ? (
              <>
                <Tv className="w-7 h-7 text-amber-400" /> {t('series')}
              </>
            ) : (
              <span className="flex items-center gap-2.5">
                <Compass className="w-7 h-7 text-amber-400" />
                <span className="bg-gradient-to-r from-amber-200 via-amber-400 to-amber-500 bg-clip-text text-transparent">
                  {t('exploreCatalogHeading')}
                </span>
              </span>
            )}
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            {data ? `${data.total.toLocaleString()} ${t('titlesFound')}` : t('filterAndDiscover')}
          </p>
        </div>

        {/* Catalog search bar with submit button and clear button 'X' */}
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-96 md:w-[420px] lg:w-[460px] xl:w-[500px]">
          <button
            type="submit"
            className="absolute left-2.5 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-amber-400 transition-colors focus:outline-none"
            title={t('searchAction')}
          >
            <Search className="w-4 h-4" />
          </button>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t('searchCatalogPlaceholder')}
            className="w-full pl-9 pr-9 py-2 text-xs sm:text-sm bg-[#141414] border border-[#262626] rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => {
                setSearchInput('')
                updateParam('q', undefined)
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-white rounded-full transition-colors"
              title={t('clearSearch')}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      {/* Filters and Sorting Bar */}
      <div className="flex flex-wrap items-center gap-2.5 mb-4 p-4 rounded-xl bg-[#141414] border border-[#262626]">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 mr-1">
          <Filter className="w-4 h-4 text-amber-400" />
          <span>{t('filtersLabel')}</span>
        </div>

        {/* Type Filter */}
        <select
          value={tipo || ''}
          onChange={(e) => updateParam('tipo', e.target.value || undefined)}
          className="px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#262626] text-xs text-gray-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
        >
          <option value="">{t('allTypes')}</option>
          <option value="movie">{t('movies')}</option>
          <option value="tv">{t('series')}</option>
        </select>

        {/* Upcoming Releases Checkbox */}
        <label
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs cursor-pointer select-none transition-all ${
            upcoming
              ? 'bg-amber-500/15 border-amber-500/50 text-amber-300 font-semibold shadow-sm shadow-amber-500/10'
              : 'bg-[#0d0d0d] border-[#262626] text-gray-400 hover:text-gray-200 hover:border-gray-600'
          }`}
          title={language === 'es' ? 'Mostrar exclusivamente títulos no estrenados' : 'Show exclusively unreleased titles'}
        >
          <input
            type="checkbox"
            checked={upcoming}
            onChange={(e) => handleUpcomingToggle(e.target.checked)}
            className="w-3.5 h-3.5 rounded bg-[#141414] border-[#333] text-amber-500 focus:ring-0 focus:ring-offset-0 cursor-pointer accent-amber-500"
          />
          <CalendarClock className={`w-3.5 h-3.5 shrink-0 ${upcoming ? 'text-amber-400' : 'text-gray-400'}`} />
          <span>{language === 'es' ? 'Próximos Estrenos' : 'Upcoming Releases'}</span>
        </label>

        {/* Section Filter */}
        <select
          value={upcoming ? '' : (section || '')}
          disabled={upcoming}
          onChange={(e) => updateParam('section', e.target.value || undefined)}
          className={`px-3 py-1.5 rounded-lg bg-[#0d0d0d] border text-xs transition-colors ${
            upcoming
              ? 'opacity-40 cursor-not-allowed border-[#1f1f1f] text-gray-500'
              : 'border-[#262626] text-gray-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500'
          }`}
          title={upcoming ? (language === 'es' ? 'Las secciones no se mezclan con próximos estrenos' : 'Sections do not mix with upcoming releases') : undefined}
        >
          <option value="">{t('allSections')}</option>
          <option value="trending">{t('sectionTrending')}</option>
          <option value="new_releases">{t('sectionNewReleases')}</option>
          <option value="classics">{t('sectionClassics')}</option>
          <option value="top_rated">{t('sectionTopRated')}</option>
        </select>

        {/* Multi-select Genres Dropdown with OR/AND match toggle */}
        <MultiSelectDropdown
          label={t('genresFilter')}
          options={genreOptions}
          selectedValues={selectedGenres}
          onChange={handleGenresChange}
          placeholderSearch={t('searchGenresPlaceholder')}
          emptyMessage={t('noOptionsFound')}
          clearLabel={t('clearFilters')}
          toggleConfig={{
            label: t('matchMode'),
            value: genreOp,
            options: [
              { value: 'or', label: t('matchAny') },
              { value: 'and', label: t('matchAll') },
            ],
            onChange: handleGenreOpChange,
          }}
        />

        {/* Multi-select Countries Dropdown */}
        <MultiSelectDropdown
          label={t('countriesFilter')}
          options={countryOptions}
          selectedValues={selectedCountries}
          onChange={handleCountriesChange}
          placeholderSearch={t('searchCountriesPlaceholder')}
          emptyMessage={t('noOptionsFound')}
          clearLabel={t('clearFilters')}
        />

        {/* Multi-select Languages Dropdown */}
        <MultiSelectDropdown
          label={t('languagesFilter')}
          options={languageOptions}
          selectedValues={selectedLanguages}
          onChange={handleLanguagesChange}
          placeholderSearch={t('searchLanguagesPlaceholder')}
          emptyMessage={t('noOptionsFound')}
          clearLabel={t('clearFilters')}
        />

        {/* Sorting */}
        <div className="ml-auto flex items-center gap-2">
          <select
            value={sortBy}
            onChange={(e) => updateParam('sort_by', e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#262626] text-xs text-gray-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
          >
            <option value="popularity">{t('sortPopularity')}</option>
            <option value="rating">{t('sortRating')}</option>
            <option value="release_date">{t('sortReleaseDate')}</option>
            <option value="title">{t('sortTitle')}</option>
          </select>

          <button
            onClick={() => updateParam('order', order === 'desc' ? 'asc' : 'desc')}
            title={`Order: ${order === 'desc' ? 'Descending' : 'Ascending'}`}
            className="px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#262626] text-xs text-gray-300 hover:text-white hover:border-amber-500 transition-colors"
          >
            {order === 'desc' ? 'Desc ↓' : 'Asc ↑'}
          </button>
        </div>
      </div>

      {/* Active Filter Chips / Pills */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2 mb-6 px-1">
          <span className="text-xs text-gray-400 font-medium mr-1">{t('activeFilters')}:</span>

          {query && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-amber-500/10 text-amber-300 border border-amber-500/30">
              <span>"{query}"</span>
              <button
                type="button"
                onClick={() => {
                  setSearchInput('')
                  updateParam('q', undefined)
                }}
                className="hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {actor && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-amber-500/10 text-amber-300 border border-amber-500/30">
              <User className="w-3 h-3 text-amber-400 shrink-0" />
              <span>{actor}</span>
              <button
                type="button"
                onClick={() => updateParam('actor', undefined)}
                className="hover:text-white transition-colors"
                title={language === 'es' ? 'Quitar filtro de actor' : 'Remove actor filter'}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {tipo && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-[#1f1f1f] text-gray-200 border border-[#333]">
              <span>{tipo === 'movie' ? t('movies') : t('series')}</span>
              <button type="button" onClick={() => updateParam('tipo', undefined)} className="hover:text-amber-400">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {upcoming && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-amber-500/15 text-amber-300 border border-amber-500/40 font-medium">
              <CalendarClock className="w-3 h-3 text-amber-400 shrink-0" />
              <span>{language === 'es' ? 'Próximos Estrenos' : 'Upcoming Releases'}</span>
              <button
                type="button"
                onClick={() => handleUpcomingToggle(false)}
                className="hover:text-white transition-colors"
                title={language === 'es' ? 'Quitar filtro de próximos estrenos' : 'Remove upcoming filter'}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {section && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-[#1f1f1f] text-gray-200 border border-[#333]">
              <span>{getSectionLabel(section)}</span>
              <button type="button" onClick={() => updateParam('section', undefined)} className="hover:text-amber-400">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {selectedGenres.map((g) => (
            <span
              key={g}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-amber-500/10 text-amber-300 border border-amber-500/30"
            >
              <span>{translateGenreName(g)}</span>
              {selectedGenres.length > 1 && (
                <span className="text-[10px] text-amber-400/70 font-mono uppercase">
                  ({genreOp})
                </span>
              )}
              <button
                type="button"
                onClick={() => handleGenresChange(selectedGenres.filter((v) => v !== g))}
                className="hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}

          {selectedCountries.map((c) => (
            <span
              key={c}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-[#1f1f1f] text-gray-200 border border-[#333]"
            >
              <CountryFlag code={c} className="w-4 h-2.5 shrink-0" />
              <span>{getCountryLabel(c)}</span>
              <button
                type="button"
                onClick={() => handleCountriesChange(selectedCountries.filter((v) => v !== c))}
                className="hover:text-amber-400"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}

          {selectedLanguages.map((l) => (
            <span
              key={l}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-[#1f1f1f] text-gray-200 border border-[#333]"
            >
              <span>{getLanguageLabel(l)}</span>
              <button
                type="button"
                onClick={() => handleLanguagesChange(selectedLanguages.filter((v) => v !== l))}
                className="hover:text-amber-400"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}

          <button
            type="button"
            onClick={handleClearAllFilters}
            className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-amber-400 ml-2 transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            <span>{t('clearAll')}</span>
          </button>
        </div>
      )}

      {/* Grid Content or Empty State */}
      {loading && !data ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <div className="w-10 h-10 border-4 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
          <p className="text-xs text-gray-400">{t('loadingResults')}</p>
        </div>
      ) : error ? (
        <div className="p-8 text-center bg-[#141414] rounded-2xl border border-[#262626]">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm text-gray-300">{error}</p>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="p-16 text-center bg-[#141414] rounded-2xl border border-[#262626]">
          <Sparkles className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white mb-1">{t('noTitlesFound')}</h3>
          <p className="text-xs text-gray-400 max-w-sm mx-auto mb-4">
            {t('noTitlesFilterDesc')}
          </p>
          <button
            onClick={handleClearAllFilters}
            className="px-4 py-2 text-xs font-bold rounded-lg bg-amber-500 hover:bg-amber-400 text-black shadow-md transition-colors"
          >
            {t('clearFilters')}
          </button>
        </div>
      ) : (
        <div className="relative min-h-[400px]">
          {/* Sutil overlay de carga para transiciones de filtro sin parpadeo de scroll */}
          {loading && (
            <div className="absolute inset-0 bg-black/30 backdrop-blur-[0.5px] z-20 flex items-start justify-center pt-24 rounded-2xl animate-in fade-in duration-100 pointer-events-none">
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#171717]/95 border border-[#333] shadow-2xl">
                <div className="w-3.5 h-3.5 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
                <span className="text-xs font-medium text-gray-200">{t('loadingResults')}</span>
              </div>
            </div>
          )}

          {/* Titles Grid */}
          <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 sm:gap-6 transition-opacity duration-200 ${loading ? 'opacity-40' : 'opacity-100'}`}>
            {data.items.map((item) => (
              <div key={`${item.tipo}-${item.id}`} className="flex justify-center">
                <TitleCard title={item} onStateChange={handleCardStateChange} onOpenAuth={openAuth} />
              </div>
            ))}
          </div>

          {/* Paginator */}
          {Math.ceil(data.total / data.page_size) > 1 && (
            <div className="flex items-center justify-center gap-3 mt-12 pt-6 border-t border-[#262626]">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className="flex items-center gap-1 px-3.5 py-2 rounded-lg bg-[#141414] border border-[#262626] text-xs font-medium text-gray-300 hover:bg-[#202020] hover:text-white hover:border-amber-500/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" /> {t('previous')}
              </button>

              <span className="text-xs text-gray-400 font-medium">
                {t('pageLabel')} <strong className="text-white">{page}</strong> {t('ofLabel')}{' '}
                {Math.ceil(data.total / data.page_size)}
              </span>

              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= Math.ceil(data.total / data.page_size)}
                className="flex items-center gap-1 px-3.5 py-2 rounded-lg bg-[#141414] border border-[#262626] text-xs font-medium text-gray-300 hover:bg-[#202020] hover:text-white hover:border-amber-500/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {t('next')} <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
