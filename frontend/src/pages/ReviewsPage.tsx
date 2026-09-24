import React, { useEffect, useState, useCallback } from 'react'
import { useSearchParams, Link, useOutletContext } from 'react-router-dom'
import {
  MessageSquare,
  Star,
  Pencil,
  Trash2,
  Send,
  Film,
  Tv,
  Minus,
  Plus,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react'
import { catalogService } from '@/services/catalogService'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import type { UserReviewItem, TitleCard as TitleCardType } from '@/types/catalog'
import posterFallback from '@/assets/placeholders/poster-empty.svg'

interface OutletContextType {
  openAuth: (mode?: 'login' | 'register') => void
}

export const ReviewsPage: React.FC = () => {
  const { user, loading: authLoading } = useAuth()
  const { t } = useLanguage()
  const { openAuth } = useOutletContext<OutletContextType>()
  const [searchParams, setSearchParams] = useSearchParams()

  const activeTab = searchParams.get('tab') || 'my_reviews'

  // Tab 1: My Reviews
  const [reviews, setReviews] = useState<UserReviewItem[]>([])
  const [totalReviews, setTotalReviews] = useState(0)
  const [reviewPage, setReviewPage] = useState(1)
  const [loadingReviews, setLoadingReviews] = useState(true)

  // Editing state for a review
  const [editingReviewId, setEditingReviewId] = useState<number | null>(null)
  const [editScore, setEditScore] = useState<number>(8.0)
  const [editIncludeScore, setEditIncludeScore] = useState<boolean>(true)
  const [editText, setEditText] = useState<string>('')
  const [submittingEdit, setSubmittingEdit] = useState(false)

  // Deleting state
  const [deletingId, setDeletingId] = useState<number | null>(null)

  // Tab 2: Pending Reviews
  const [pendingTitles, setPendingTitles] = useState<TitleCardType[]>([])
  const [loadingPending, setLoadingPending] = useState(true)

  // Quick write state for a pending title
  const [writingForTitleId, setWritingForTitleId] = useState<number | null>(null)
  const [newScore, setNewScore] = useState<number>(8.0)
  const [newIncludeScore, setNewIncludeScore] = useState<boolean>(true)
  const [newText, setNewText] = useState<string>('')
  const [submittingNew, setSubmittingNew] = useState(false)

  // Success notifications
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const showSuccess = (msg: string) => {
    setSuccessMessage(msg)
    setTimeout(() => setSuccessMessage(null), 4000)
  }

  // Load My Reviews
  const loadMyReviews = useCallback(async (page: number = 1) => {
    if (!user) return
    setLoadingReviews(true)
    try {
      const res = await catalogService.getUserReviews(page, 15)
      setReviews(res.items || [])
      setTotalReviews(res.total || 0)
      setReviewPage(res.page || 1)
    } catch (err) {
      console.error('Error loading user reviews:', err)
    } finally {
      setLoadingReviews(false)
    }
  }, [user])

  // Load Pending Reviews (watched titles without review)
  const loadPendingTitles = useCallback(async () => {
    if (!user) return
    setLoadingPending(true)
    try {
      const res = await catalogService.getUnreviewedWatched(50)
      setPendingTitles(res.items || [])
    } catch (err) {
      console.error('Error loading unreviewed watched titles:', err)
    } finally {
      setLoadingPending(false)
    }
  }, [user])

  useEffect(() => {
    if (user) {
      loadMyReviews(reviewPage)
      loadPendingTitles()
    } else {
      setLoadingReviews(false)
      setLoadingPending(false)
    }
  }, [user, reviewPage, loadMyReviews, loadPendingTitles])

  const setTab = (tabName: string) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', tabName)
    setSearchParams(next)
  }

  // Handle start edit
  const handleStartEdit = (r: UserReviewItem) => {
    setEditingReviewId(r.id)
    setEditText(r.texto)
    if (r.puntaje !== null && r.puntaje !== undefined) {
      setEditIncludeScore(true)
      setEditScore(r.puntaje)
    } else {
      setEditIncludeScore(false)
      setEditScore(8.0)
    }
  }

  // Handle save edit
  const handleSaveEdit = async (r: UserReviewItem) => {
    if (!editText.trim()) return
    setSubmittingEdit(true)
    try {
      const finalScore = editIncludeScore ? Math.round(editScore * 2) / 2 : null
      await catalogService.addReview(r.titulo_id, editText.trim(), finalScore)
      showSuccess('Review updated successfully.')
      setEditingReviewId(null)
      loadMyReviews(reviewPage)
    } catch (err) {
      console.error('Error updating review:', err)
    } finally {
      setSubmittingEdit(false)
    }
  }

  // Handle delete review
  const handleDeleteReview = async (r: UserReviewItem) => {
    if (!window.confirm(`Are you sure you want to delete your review for "${r.titulo_nombre}"?`)) {
      return
    }
    setDeletingId(r.id)
    try {
      await catalogService.deleteReview(r.titulo_id)
      showSuccess('Review deleted successfully.')
      loadMyReviews(reviewPage)
      loadPendingTitles()
    } catch (err) {
      console.error('Error deleting review:', err)
    } finally {
      setDeletingId(null)
    }
  }

  // Handle submit review for pending title
  const handleSubmitPendingReview = async (titleId: number) => {
    if (!newText.trim()) return
    setSubmittingNew(true)
    try {
      const finalScore = newIncludeScore ? Math.round(newScore * 2) / 2 : null
      await catalogService.addReview(titleId, newText.trim(), finalScore)
      showSuccess('Review submitted successfully.')
      setWritingForTitleId(null)
      setNewText('')
      setNewScore(8.0)
      setNewIncludeScore(true)
      loadPendingTitles()
      loadMyReviews(1)
    } catch (err) {
      console.error('Error creating review for watched title:', err)
    } finally {
      setSubmittingNew(false)
    }
  }

  if (authLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-10 h-10 border-3 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
        <p className="text-xs text-gray-400 font-medium">Loading reviews...</p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="max-w-md mx-auto my-24 p-8 bg-[#141414] border border-[#262626] rounded-2xl text-center space-y-4">
        <MessageSquare className="w-12 h-12 text-amber-500 mx-auto" />
        <h2 className="text-xl font-bold text-white">Sign in to manage your reviews</h2>
        <p className="text-xs text-gray-400">
          Track all your written opinions, edit ratings, and review titles you have already watched.
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={() => openAuth('login')}
            className="px-5 py-2.5 rounded-xl bg-[#1a1a1a] hover:bg-[#222222] border border-[#333333] text-gray-200 text-xs font-semibold transition-all active:scale-95"
          >
            Log In
          </button>
          <button
            onClick={() => openAuth('register')}
            className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all active:scale-95"
          >
            Create Account
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#262626] pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
            <MessageSquare className="w-7 h-7 text-amber-500" /> Reviews & Opinions
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Manage your written reviews and discover titles in your history waiting for your opinion.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-2 p-1 rounded-xl bg-[#141414] border border-[#262626] self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setTab('my_reviews')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'my_reviews'
                ? 'bg-amber-500 text-black shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <span>My Reviews</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                activeTab === 'my_reviews' ? 'bg-black/30 text-black' : 'bg-[#222222] text-gray-400'
              }`}
            >
              {totalReviews}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setTab('pending')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'pending'
                ? 'bg-amber-500 text-black shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <span>Pending Reviews</span>
            {pendingTitles.length > 0 && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  activeTab === 'pending' ? 'bg-black/30 text-black' : 'bg-amber-500/20 text-amber-400'
                }`}
              >
                {pendingTitles.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Success Notification Alert */}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/80 text-xs font-medium text-emerald-300 flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Tab 1: My Reviews */}
      {activeTab === 'my_reviews' && (
        <div className="space-y-6">
          {loadingReviews ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <div className="w-10 h-10 border-4 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
              <p className="text-xs text-gray-400">Loading your reviews...</p>
            </div>
          ) : reviews.length === 0 ? (
            <div className="p-12 rounded-2xl bg-[#141414] border border-[#262626] text-center space-y-4 max-w-lg mx-auto">
              <MessageSquare className="w-12 h-12 text-gray-600 mx-auto" />
              <h3 className="text-lg font-bold text-white">No reviews yet</h3>
              <p className="text-xs text-gray-400">
                You have not shared any reviews yet. Share your thoughts on titles you have watched or check the pending tab!
              </p>
              <div className="flex justify-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setTab('pending')}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-all"
                >
                  View Pending Titles ({pendingTitles.length})
                </button>
                <Link
                  to="/catalog"
                  className="px-4 py-2 rounded-xl bg-[#202020] hover:bg-[#282828] text-white text-xs font-bold border border-[#333] transition-all"
                >
                  {t('explore')}
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {reviews.map((r) => {
                const isEditing = editingReviewId === r.id

                return (
                  <div
                    key={r.id}
                    className="p-5 rounded-2xl bg-[#141414] border border-[#262626] hover:border-[#333333] transition-all space-y-4"
                  >
                    {/* Header de la Card */}
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div className="flex items-center gap-3.5">
                        <Link to={`/titles/${r.titulo_id}`} className="shrink-0 group">
                          <img
                            src={r.titulo_portada_url || posterFallback}
                            alt={r.titulo_nombre}
                            className="w-12 h-16 object-cover rounded-lg border border-[#262626] group-hover:border-amber-500 transition-colors"
                          />
                        </Link>

                        <div className="space-y-1">
                          <Link
                            to={`/titles/${r.titulo_id}`}
                            className="text-base font-bold text-white hover:text-amber-400 transition-colors line-clamp-1"
                          >
                            {r.titulo_nombre}
                          </Link>

                          <div className="flex items-center gap-2 text-xs text-gray-400">
                            <span className="flex items-center gap-1">
                              {r.titulo_tipo === 'movie' ? (
                                <>
                                  <Film className="w-3 h-3 text-amber-500" /> Movie
                                </>
                              ) : (
                                <>
                                  <Tv className="w-3 h-3 text-amber-500" /> TV Series
                                </>
                              )}
                            </span>
                            <span>•</span>
                            <span>
                              {r.titulo_fecha_estreno
                                ? new Date(r.titulo_fecha_estreno).getFullYear()
                                : '-'}
                            </span>
                            <span>•</span>
                            <span className="text-gray-500">
                              {r.fecha ? new Date(r.fecha).toLocaleDateString() : '-'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Calificación y Acciones */}
                      <div className="flex items-center gap-2">
                        {r.puntaje !== null && r.puntaje !== undefined ? (
                          <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-[#0d0d0d] border border-[#262626] text-amber-400 text-xs font-bold">
                            <Star className="w-3.5 h-3.5 fill-current" />
                            <span>{r.puntaje.toFixed(1)}/10</span>
                          </div>
                        ) : (
                          <span className="text-xs text-gray-500 italic px-2 py-1">No rating</span>
                        )}

                        <button
                          type="button"
                          onClick={() => handleStartEdit(r)}
                          className="p-2 rounded-xl bg-[#1e1e1e] hover:bg-[#282828] text-gray-300 hover:text-white border border-[#333333] transition-colors"
                          title="Edit review"
                        >
                          <Pencil className="w-3.5 h-3.5 text-amber-400" />
                        </button>

                        <button
                          type="button"
                          onClick={() => handleDeleteReview(r)}
                          disabled={deletingId === r.id}
                          className="p-2 rounded-xl bg-red-950/20 hover:bg-red-900/40 text-red-400 border border-red-900/40 transition-colors disabled:opacity-50"
                          title="Delete review"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Contenido / Modo Edición */}
                    {isEditing ? (
                      <div className="p-4 rounded-xl bg-[#0d0d0d] border border-[#262626] space-y-4">
                        <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                          Editing Review for {r.titulo_nombre}
                        </h4>

                        <div className="space-y-2">
                          <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300 select-none">
                            <input
                              type="checkbox"
                              checked={editIncludeScore}
                              onChange={(e) => setEditIncludeScore(e.target.checked)}
                              className="w-4 h-4 rounded border-[#333333] bg-[#1a1a1a] text-amber-500 focus:ring-amber-500"
                            />
                            <span className="font-medium">Include rating / Calificar con puntaje</span>
                          </label>

                          {editIncludeScore && (
                            <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-[#141414] border border-[#262626]">
                              <div className="flex items-center gap-1.5">
                                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                                <span className="text-sm font-bold text-amber-400 w-12 text-center">
                                  {editScore.toFixed(1)}
                                </span>
                                <span className="text-[11px] text-gray-500">/ 10</span>
                              </div>

                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() =>
                                    setEditScore((prev) =>
                                      Math.max(0, Math.round((prev - 0.5) * 2) / 2)
                                    )
                                  }
                                  className="p-1.5 rounded-lg bg-[#222222] hover:bg-[#2c2c2c] text-gray-300 hover:text-white border border-[#333333]"
                                >
                                  <Minus className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() =>
                                    setEditScore((prev) =>
                                      Math.min(10, Math.round((prev + 0.5) * 2) / 2)
                                    )
                                  }
                                  className="p-1.5 rounded-lg bg-[#222222] hover:bg-[#2c2c2c] text-gray-300 hover:text-white border border-[#333333]"
                                >
                                  <Plus className="w-3.5 h-3.5" />
                                </button>
                              </div>

                              <input
                                type="range"
                                min="0"
                                max="10"
                                step="0.5"
                                value={editScore}
                                onChange={(e) => setEditScore(parseFloat(e.target.value))}
                                className="flex-1 min-w-[140px] accent-amber-500 cursor-pointer h-1.5 bg-[#262626] rounded-lg"
                              />
                            </div>
                          )}
                        </div>

                        <textarea
                          rows={3}
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          className="w-full p-3 text-sm bg-[#141414] border border-[#262626] rounded-xl text-white focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
                        />

                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setEditingReviewId(null)}
                            className="px-4 py-1.5 rounded-xl bg-[#222222] hover:bg-[#2c2c2c] text-gray-300 hover:text-white text-xs font-semibold"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(r)}
                            disabled={submittingEdit}
                            className="px-4 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md disabled:opacity-50"
                          >
                            {submittingEdit ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs sm:text-sm text-gray-300 leading-relaxed whitespace-pre-line">
                        {r.texto}
                      </p>
                    )}
                  </div>
                )
              })}

              {/* Paginación */}
              {totalReviews > 15 && (
                <div className="flex items-center justify-between pt-4 border-t border-[#262626]">
                  <span className="text-xs text-gray-400">
                    Showing {(reviewPage - 1) * 15 + 1} to {Math.min(reviewPage * 15, totalReviews)} of{' '}
                    {totalReviews} reviews
                  </span>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setReviewPage((p) => Math.max(1, p - 1))}
                      disabled={reviewPage <= 1}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[#141414] hover:bg-[#202020] border border-[#262626] text-xs font-semibold text-gray-300 hover:text-white disabled:opacity-40"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" /> Previous
                    </button>
                    <span className="text-xs text-amber-500 font-bold px-2">Page {reviewPage}</span>
                    <button
                      type="button"
                      onClick={() => setReviewPage((p) => p + 1)}
                      disabled={reviewPage * 15 >= totalReviews}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[#141414] hover:bg-[#202020] border border-[#262626] text-xs font-semibold text-gray-300 hover:text-white disabled:opacity-40"
                    >
                      Next <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Pending Reviews */}
      {activeTab === 'pending' && (
        <div className="space-y-6">
          {loadingPending ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <div className="w-10 h-10 border-4 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
              <p className="text-xs text-gray-400">Loading pending titles...</p>
            </div>
          ) : pendingTitles.length === 0 ? (
            <div className="p-12 rounded-2xl bg-[#141414] border border-[#262626] text-center space-y-4 max-w-lg mx-auto">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="text-lg font-bold text-white">All caught up!</h3>
              <p className="text-xs text-gray-400">
                You have reviewed all watched and in-progress titles in your library.
              </p>
              <Link
                to="/catalog"
                className="inline-block px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md transition-all"
              >
                Discover More Titles
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[#141414] border border-[#262626] flex items-center justify-between flex-wrap gap-2">
                <span className="text-xs text-gray-300 font-medium">
                  {pendingTitles.length} watched or in-progress titles waiting for your review.
                </span>
                <span className="text-[11px] text-amber-500/90 font-medium">
                  Rate them to refine your recommendations!
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {pendingTitles.map((t) => {
                  const isWriting = writingForTitleId === t.id

                  return (
                    <div
                      key={t.id}
                      className="p-4 rounded-2xl bg-[#141414] border border-[#262626] hover:border-[#333333] transition-all space-y-3"
                    >
                      <div className="flex gap-3">
                        <Link to={`/titles/${t.id}`} className="shrink-0 group">
                          <img
                            src={t.portada_url || posterFallback}
                            alt={t.nombre}
                            className="w-16 h-24 object-cover rounded-xl border border-[#262626] group-hover:border-amber-500 transition-colors"
                          />
                        </Link>

                        <div className="flex-1 min-w-0 space-y-1">
                          <Link
                            to={`/titles/${t.id}`}
                            className="text-sm font-bold text-white hover:text-amber-400 transition-colors line-clamp-1"
                          >
                            {t.nombre}
                          </Link>

                          <div className="flex items-center gap-2 text-[11px] text-gray-400 flex-wrap">
                            <span className="flex items-center gap-1">
                              {t.tipo === 'movie' ? (
                                <>
                                  <Film className="w-3 h-3 text-amber-500" /> Movie
                                </>
                              ) : (
                                <>
                                  <Tv className="w-3 h-3 text-amber-500" /> TV Series
                                </>
                              )}
                            </span>
                            <span>•</span>
                            <span>{t.anio_estreno || '-'}</span>
                            {t.user_estado && (
                              <>
                                <span>•</span>
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                                    t.user_estado === 'siguiendo'
                                      ? 'bg-blue-950/40 text-blue-300 border-blue-800/60'
                                      : t.user_estado === 'vista'
                                      ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                                      : 'bg-red-950/40 text-red-300 border-red-800/60'
                                  }`}
                                >
                                  {t.user_estado === 'siguiendo'
                                    ? 'Watching'
                                    : t.user_estado === 'vista'
                                    ? 'Watched'
                                    : 'Dropped'}
                                </span>
                              </>
                            )}
                          </div>

                          <div className="flex items-center gap-1 text-[11px] text-amber-400 font-semibold pt-1">
                            <Star className="w-3 h-3 fill-current" />
                            <span>{t.rating_unificado ? t.rating_unificado.toFixed(1) : '-'}</span>
                            <span className="text-gray-500 font-normal">TMDB community</span>
                          </div>
                        </div>

                        {!isWriting && (
                          <button
                            type="button"
                            onClick={() => {
                              setWritingForTitleId(t.id)
                              setNewText('')
                              setNewScore(8.0)
                              setNewIncludeScore(true)
                            }}
                            className="self-start px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md transition-all shrink-0 flex items-center gap-1.5"
                          >
                            <Pencil className="w-3 h-3" />
                            <span>Write Review</span>
                          </button>
                        )}
                      </div>

                      {/* Formulario desplegable para escribir reseña directamente */}
                      {isWriting && (
                        <div className="pt-2 border-t border-[#262626] space-y-3 animate-in fade-in">
                          <div className="space-y-2">
                            <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300 select-none">
                              <input
                                type="checkbox"
                                checked={newIncludeScore}
                                onChange={(e) => setNewIncludeScore(e.target.checked)}
                                className="w-4 h-4 rounded border-[#333333] bg-[#0d0d0d] text-amber-500 focus:ring-amber-500"
                              />
                              <span className="font-medium">Include rating / Calificar</span>
                            </label>

                            {newIncludeScore && (
                              <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl bg-[#0d0d0d] border border-[#262626]">
                                <div className="flex items-center gap-1">
                                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                                  <span className="text-xs font-bold text-amber-400 w-10 text-center">
                                    {newScore.toFixed(1)}
                                  </span>
                                  <span className="text-[10px] text-gray-500">/ 10</span>
                                </div>

                                <div className="flex items-center gap-1">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setNewScore((prev) =>
                                        Math.max(0, Math.round((prev - 0.5) * 2) / 2)
                                      )
                                    }
                                    className="p-1 rounded bg-[#1a1a1a] hover:bg-[#252525] text-gray-300 hover:text-white border border-[#333333]"
                                  >
                                    <Minus className="w-3 h-3" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setNewScore((prev) =>
                                        Math.min(10, Math.round((prev + 0.5) * 2) / 2)
                                      )
                                    }
                                    className="p-1 rounded bg-[#1a1a1a] hover:bg-[#252525] text-gray-300 hover:text-white border border-[#333333]"
                                  >
                                    <Plus className="w-3 h-3" />
                                  </button>
                                </div>

                                <input
                                  type="range"
                                  min="0"
                                  max="10"
                                  step="0.5"
                                  value={newScore}
                                  onChange={(e) => setNewScore(parseFloat(e.target.value))}
                                  className="flex-1 min-w-[100px] accent-amber-500 cursor-pointer h-1.5 bg-[#262626] rounded-lg"
                                />
                              </div>
                            )}
                          </div>

                          <textarea
                            rows={2}
                            value={newText}
                            onChange={(e) => setNewText(e.target.value)}
                            placeholder="What did you think of this title? Share your thoughts..."
                            className="w-full p-2.5 text-xs bg-[#0d0d0d] border border-[#262626] rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
                          />

                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => setWritingForTitleId(null)}
                              className="px-3 py-1.5 rounded-xl bg-[#222222] hover:bg-[#2c2c2c] text-gray-300 hover:text-white text-xs font-semibold"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => handleSubmitPendingReview(t.id)}
                              disabled={submittingNew}
                              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold shadow-md disabled:opacity-50"
                            >
                              <Send className="w-3 h-3" />
                              <span>{submittingNew ? 'Publishing...' : 'Publish'}</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
