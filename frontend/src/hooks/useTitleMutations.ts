import { useMutation, useQueryClient } from '@tanstack/react-query'
import { catalogService, type TitlesResponse } from '@/services/catalogService'
import { useToast } from '@/context/ToastContext'
import { useLanguage } from '@/context/LanguageContext'
import type { HomeSections, TitleCard, TitleDetail } from '@/types/catalog'

export function useTitleMutations() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const { language } = useLanguage()

  const updateCardInHomeSections = (homeData: HomeSections, titleId: number, patch: Partial<TitleCard>): HomeSections => {
    const updateList = (list: TitleCard[]) =>
      list ? list.map((item) => (item.id === titleId ? { ...item, ...patch } : item)) : []

    const updatedByGenre: Record<string, TitleCard[]> = {}
    if (homeData.by_genre) {
      for (const [genre, list] of Object.entries(homeData.by_genre)) {
        updatedByGenre[genre] = updateList(list)
      }
    }

    return {
      ...homeData,
      trending: updateList(homeData.trending),
      new_releases: updateList(homeData.new_releases),
      classics: updateList(homeData.classics),
      top_rated: updateList(homeData.top_rated),
      by_genre: updatedByGenre,
      others: updateList(homeData.others),
    }
  }

  const applyOptimisticPatch = (titleId: number, patch: Partial<TitleCard>) => {
    // 1. Actualizar queries de Home
    queryClient.setQueriesData<HomeSections>({ queryKey: ['homeSections'] }, (old) => {
      if (!old) return old
      return updateCardInHomeSections(old, titleId, patch)
    })

    // 2. Actualizar queries de Catálogo
    queryClient.setQueriesData<TitlesResponse>({ queryKey: ['catalog'] }, (old) => {
      if (!old || !old.items) return old
      return {
        ...old,
        items: old.items.map((item) => (item.id === titleId ? { ...item, ...patch } : item)),
      }
    })

    // 3. Actualizar query de Detalle si coincide
    queryClient.setQueryData<TitleDetail>(['titleDetail', titleId], (old) => {
      if (!old) return old
      return { ...old, ...patch }
    })
  }

  // Mutación: Alternar Favorito
  const favoriteMutation = useMutation({
    mutationFn: (titleId: number) => catalogService.toggleFavorite(titleId),
    onMutate: async (titleId: number) => {
      // Cancelar refetches en curso para evitar sobreescritura
      await queryClient.cancelQueries({ queryKey: ['homeSections'] })
      await queryClient.cancelQueries({ queryKey: ['catalog'] })
      await queryClient.cancelQueries({ queryKey: ['titleDetail', titleId] })

      // Snapshot del estado previo
      const previousHome = queryClient.getQueriesData<HomeSections>({ queryKey: ['homeSections'] })
      const previousCatalog = queryClient.getQueriesData<TitlesResponse>({ queryKey: ['catalog'] })
      const previousDetail = queryClient.getQueryData<TitleDetail>(['titleDetail', titleId])

      // Determinar valor opuesto a partir del detalle o de alguna card
      let currentFav = false
      if (previousDetail) {
        currentFav = !!previousDetail.user_favorito
      } else {
        for (const [, hData] of previousHome) {
          if (!hData) continue
          const found = [
            ...(hData.trending || []),
            ...(hData.new_releases || []),
            ...(hData.classics || []),
            ...(hData.top_rated || []),
          ].find((t) => t.id === titleId)
          if (found) {
            currentFav = !!found.user_favorito
            break
          }
        }
      }

      const nextFav = !currentFav
      applyOptimisticPatch(titleId, { user_favorito: nextFav })

      return { previousHome, previousCatalog, previousDetail, titleId }
    },
    onError: (_err, _titleId, context) => {
      // Rollback al estado anterior
      if (context) {
        context.previousHome.forEach(([qKey, qData]) => {
          queryClient.setQueryData(qKey, qData)
        })
        context.previousCatalog.forEach(([qKey, qData]) => {
          queryClient.setQueryData(qKey, qData)
        })
        if (context.previousDetail) {
          queryClient.setQueryData(['titleDetail', context.titleId], context.previousDetail)
        }
      }
      showToast(
        language === 'es'
          ? 'No se pudo actualizar favoritos. Reintentando...'
          : 'Could not update favorites. Please try again.',
        'error'
      )
    },
    onSettled: (_data, _err, titleId) => {
      queryClient.invalidateQueries({ queryKey: ['homeSections'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      queryClient.invalidateQueries({ queryKey: ['titleDetail', titleId] })
      queryClient.invalidateQueries({ queryKey: ['userLibrary'] })
      queryClient.invalidateQueries({ queryKey: ['userStats'] })
    },
  })

  // Mutación: Alternar Watchlist
  const watchlistMutation = useMutation({
    mutationFn: (titleId: number) => catalogService.toggleWatchlist(titleId),
    onMutate: async (titleId: number) => {
      await queryClient.cancelQueries({ queryKey: ['homeSections'] })
      await queryClient.cancelQueries({ queryKey: ['catalog'] })
      await queryClient.cancelQueries({ queryKey: ['titleDetail', titleId] })

      const previousHome = queryClient.getQueriesData<HomeSections>({ queryKey: ['homeSections'] })
      const previousCatalog = queryClient.getQueriesData<TitlesResponse>({ queryKey: ['catalog'] })
      const previousDetail = queryClient.getQueryData<TitleDetail>(['titleDetail', titleId])

      let currentEstado: string | null = null
      if (previousDetail) {
        currentEstado = previousDetail.user_estado ?? null
      }

      const nextEstado = currentEstado === 'watchlist' ? null : 'watchlist'
      applyOptimisticPatch(titleId, { user_estado: nextEstado })

      return { previousHome, previousCatalog, previousDetail, titleId }
    },
    onError: (_err, _titleId, context) => {
      if (context) {
        context.previousHome.forEach(([qKey, qData]) => {
          queryClient.setQueryData(qKey, qData)
        })
        context.previousCatalog.forEach(([qKey, qData]) => {
          queryClient.setQueryData(qKey, qData)
        })
        if (context.previousDetail) {
          queryClient.setQueryData(['titleDetail', context.titleId], context.previousDetail)
        }
      }
      showToast(
        language === 'es'
          ? 'No se pudo actualizar watchlist. Reintentando...'
          : 'Could not update watchlist. Please try again.',
        'error'
      )
    },
    onSettled: (_data, _err, titleId) => {
      queryClient.invalidateQueries({ queryKey: ['homeSections'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      queryClient.invalidateQueries({ queryKey: ['titleDetail', titleId] })
      queryClient.invalidateQueries({ queryKey: ['userLibrary'] })
    },
  })

  // Mutación: Alternar Visto
  const watchedMutation = useMutation({
    mutationFn: (titleId: number) => catalogService.toggleWatched(titleId),
    onMutate: async (titleId: number) => {
      await queryClient.cancelQueries({ queryKey: ['homeSections'] })
      await queryClient.cancelQueries({ queryKey: ['catalog'] })
      await queryClient.cancelQueries({ queryKey: ['titleDetail', titleId] })

      const previousHome = queryClient.getQueriesData<HomeSections>({ queryKey: ['homeSections'] })
      const previousCatalog = queryClient.getQueriesData<TitlesResponse>({ queryKey: ['catalog'] })
      const previousDetail = queryClient.getQueryData<TitleDetail>(['titleDetail', titleId])

      let currentEstado: string | null = null
      if (previousDetail) {
        currentEstado = previousDetail.user_estado ?? null
      }

      const nextEstado = currentEstado === 'vista' ? null : 'vista'
      applyOptimisticPatch(titleId, { user_estado: nextEstado })

      return { previousHome, previousCatalog, previousDetail, titleId }
    },
    onError: (_err, _titleId, context) => {
      if (context) {
        context.previousHome.forEach(([qKey, qData]) => {
          queryClient.setQueryData(qKey, qData)
        })
        context.previousCatalog.forEach(([qKey, qData]) => {
          queryClient.setQueryData(qKey, qData)
        })
        if (context.previousDetail) {
          queryClient.setQueryData(['titleDetail', context.titleId], context.previousDetail)
        }
      }
      showToast(
        language === 'es'
          ? 'No se pudo actualizar el estado de visto. Reintentando...'
          : 'Could not update watched status. Please try again.',
        'error'
      )
    },
    onSettled: (_data, _err, titleId) => {
      queryClient.invalidateQueries({ queryKey: ['homeSections'] })
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      queryClient.invalidateQueries({ queryKey: ['titleDetail', titleId] })
      queryClient.invalidateQueries({ queryKey: ['userLibrary'] })
      queryClient.invalidateQueries({ queryKey: ['userStats'] })
    },
  })

  return {
    favoriteMutation,
    watchlistMutation,
    watchedMutation,
  }
}
