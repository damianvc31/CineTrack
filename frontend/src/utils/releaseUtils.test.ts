import { describe, it, expect } from 'vitest'
import { isTitleUnreleased } from './releaseUtils'

describe('isTitleUnreleased', () => {
  it('retorna false si el título es nulo o indefinido', () => {
    expect(isTitleUnreleased(null)).toBe(false)
    expect(isTitleUnreleased(undefined)).toBe(false)
  })

  it('detecta películas no estrenadas por fecha futura o status de producción', () => {
    // Fecha futura
    expect(
      isTitleUnreleased({
        tipo: 'movie',
        fecha_estreno: '2099-12-31',
        status_tmdb: 'Released',
      })
    ).toBe(true)

    // Sin fecha de estreno
    expect(
      isTitleUnreleased({
        tipo: 'movie',
        fecha_estreno: null,
      })
    ).toBe(true)

    // Status de producción/planificación
    expect(
      isTitleUnreleased({
        tipo: 'movie',
        fecha_estreno: '2020-01-01',
        status_tmdb: 'Post Production',
      })
    ).toBe(true)
  })

  it('retorna false para películas ya estrenadas', () => {
    expect(
      isTitleUnreleased({
        tipo: 'movie',
        fecha_estreno: '2020-05-15',
        status_tmdb: 'Released',
      })
    ).toBe(false)
  })

  it('detecta series sin episodios estrenados como unreleased', () => {
    // Serie con fecha futura
    expect(
      isTitleUnreleased({
        tipo: 'tv',
        fecha_estreno: '2099-01-01',
        status_tmdb: 'Planned',
      })
    ).toBe(true)

    // Serie con temporadas donde ningún episodio fue emitido aún
    expect(
      isTitleUnreleased({
        tipo: 'tv',
        fecha_estreno: '2026-01-01',
        status_tmdb: 'Returning Series',
        temporadas: [
          {
            episodios: [
              { id: 1, temporada_id: 1, numero: 1, nombre: 'Ep 1', visto: false, fecha_estreno: '2099-01-01' },
              { id: 2, temporada_id: 1, numero: 2, nombre: 'Ep 2', visto: false, fecha_estreno: null },
            ],
          } as any,
        ],
      })
    ).toBe(true)
  })

  it('retorna false para series que ya tienen episodios emitidos a la fecha', () => {
    expect(
      isTitleUnreleased({
        tipo: 'tv',
        fecha_estreno: '2020-01-01',
        status_tmdb: 'Returning Series',
        temporadas: [
          {
            episodios: [
              { id: 1, temporada_id: 1, numero: 1, nombre: 'Ep 1', visto: false, fecha_estreno: '2020-01-08' },
              { id: 2, temporada_id: 1, numero: 2, nombre: 'Ep 2', visto: false, fecha_estreno: '2099-01-01' },
            ],
          } as any,
        ],
      })
    ).toBe(false)
  })
})
