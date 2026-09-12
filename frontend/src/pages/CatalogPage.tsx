import React, { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useOutletContext } from 'react-router-dom'
import { Filter, Search, ChevronLeft, ChevronRight, Film, Tv, Sparkles, AlertCircle, X } from 'lucide-react'
import { catalogService, type TitlesResponse } from '@/services/catalogService'
import { TitleCard } from '@/components/common/TitleCard'

interface OutletContextType {
  openAuth: () => void
}

export const CatalogPage: React.FC = () => {
  const { openAuth } = useOutletContext<OutletContextType>()
  const [searchParams, setSearchParams] = useSearchParams()

  const [data, setData] = useState<TitlesResponse | null>(null)
  const [genres, setGenres] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Extraer parámetros de la URL
  const query = searchParams.get('q') || ''
  const tipo = (searchParams.get('tipo') as 'movie' | 'tv') || undefined
  const section = (searchParams.get('section') as any) || undefined
  const genero = searchParams.get('genero') || undefined
  const actor = searchParams.get('actor') || undefined
  const sortBy = (searchParams.get('sort_by') as any) || 'popularity'
  const order = (searchParams.get('order') as any) || 'desc'
  const page = parseInt(searchParams.get('page') || '1', 10)

  // Input local para búsqueda instantánea
  const [searchInput, setSearchInput] = useState(query)

  // Cargar lista de géneros disponibles
  useEffect(() => {
    catalogService
      .getGenres()
      .then((res) => {
        const names = res.map((g) => (typeof g === 'string' ? g : g.nombre))
        setGenres(names)
      })
      .catch(console.error)
  }, [])

  const fetchTitles = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true)
    setError(null)
    try {
      const res = await catalogService.getTitles({
        q: query || undefined,
        tipo,
        section,
        genero,
        actor,
        sort_by: sortBy,
        order,
        page,
        page_size: 24,
      })
      setData(res)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Error al consultar el catálogo')
      }
    } finally {
      if (showSpinner) setLoading(false)
    }
  }, [query, tipo, section, genero, actor, sortBy, order, page])

  useEffect(() => {
    fetchTitles(true)
  }, [fetchTitles])

  const handleCardStateChange = (action: 'favorite' | 'watchlist' | 'watched') => {
    if (action === 'watched') {
      fetchTitles(false)
    }
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

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateParam('q', searchInput.trim() || undefined)
  }

  const setPage = (newPage: number) => {
    const next = new URLSearchParams(searchParams)
    next.set('page', newPage.toString())
    setSearchParams(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Title and Main Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-6 border-b border-[#262626]">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
            {tipo === 'movie' ? (
              <>
                <Film className="w-7 h-7 text-amber-400" /> Movies
              </>
            ) : tipo === 'tv' ? (
              <>
                <Tv className="w-7 h-7 text-amber-400" /> TV Series
              </>
            ) : (
              <>Explore Catalog</>
            )}
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            {data ? `${data.total.toLocaleString()} titles found` : 'Filter and discover'}
          </p>
        </div>

        {/* Catalog search bar with clear button 'X' */}
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search titles, actors..."
            className="w-full pl-9 pr-9 py-2 text-sm bg-[#141414] border border-[#262626] rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => {
                setSearchInput('')
                updateParam('q', undefined)
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-white rounded-full transition-colors"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      {/* Filters and Sorting Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-8 p-4 rounded-xl bg-[#141414] border border-[#262626]">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 mr-2">
          <Filter className="w-4 h-4 text-amber-400" />
          <span>Filters:</span>
        </div>

        {/* Type Filter */}
        <select
          value={tipo || ''}
          onChange={(e) => updateParam('tipo', e.target.value || undefined)}
          className="px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#262626] text-xs text-gray-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
        >
          <option value="">All types</option>
          <option value="movie">Movies</option>
          <option value="tv">Series</option>
        </select>

        {/* Genre Filter */}
        <select
          value={genero || ''}
          onChange={(e) => updateParam('genero', e.target.value || undefined)}
          className="px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#262626] text-xs text-gray-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 max-w-[150px] transition-colors"
        >
          <option value="">All genres</option>
          {genres.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>

        {/* Section Filter */}
        <select
          value={section || ''}
          onChange={(e) => updateParam('section', e.target.value || undefined)}
          className="px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#262626] text-xs text-gray-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
        >
          <option value="">All sections</option>
          <option value="trending">🔥 Trending Now</option>
          <option value="new_releases">🕒 New Releases</option>
          <option value="classics">💎 Classics</option>
          <option value="top_rated">⭐ Top Rated</option>
          <option value="others">More Discoveries</option>
        </select>

        {/* Sorting */}
        <div className="ml-auto flex items-center gap-2">
          <select
            value={sortBy}
            onChange={(e) => updateParam('sort_by', e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#262626] text-xs text-gray-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
          >
            <option value="popularity">Popularity</option>
            <option value="rating">Rating</option>
            <option value="release_date">Release Date</option>
            <option value="title">Title (A-Z)</option>
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

      {/* Grid Content or Empty State */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <div className="w-10 h-10 border-4 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
          <p className="text-xs text-gray-400">Loading results...</p>
        </div>
      ) : error ? (
        <div className="p-8 text-center bg-[#141414] rounded-2xl border border-[#262626]">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-sm text-gray-300">{error}</p>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="p-16 text-center bg-[#141414] rounded-2xl border border-[#262626]">
          <Sparkles className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white mb-1">No titles found</h3>
          <p className="text-xs text-gray-400 max-w-sm mx-auto mb-4">
            No titles match the selected filters. Try resetting filters or searching with another term.
          </p>
          <button
            onClick={() => {
              setSearchInput('')
              setSearchParams(new URLSearchParams())
            }}
            className="px-4 py-2 text-xs font-bold rounded-lg bg-amber-500 hover:bg-amber-400 text-black shadow-md transition-colors"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <>
          {/* Titles Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 sm:gap-6">
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
                <ChevronLeft className="w-4 h-4" /> Previous
              </button>

              <span className="text-xs text-gray-400 font-medium">
                Page <strong className="text-white">{page}</strong> of{' '}
                {Math.ceil(data.total / data.page_size)}
              </span>

              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= Math.ceil(data.total / data.page_size)}
                className="flex items-center gap-1 px-3.5 py-2 rounded-lg bg-[#141414] border border-[#262626] text-xs font-medium text-gray-300 hover:bg-[#202020] hover:text-white hover:border-amber-500/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
