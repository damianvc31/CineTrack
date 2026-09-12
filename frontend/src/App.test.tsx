import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('CineTrack Frontend App', () => {
  it('renders the header with CineTrack branding', () => {
    render(<App />)
    const brandElements = screen.getAllByText(/CineTrack/i)
    expect(brandElements.length).toBeGreaterThan(0)
  })

  it('renders navigation links for Movies and Series', () => {
    render(<App />)
    const moviesLinks = screen.getAllByText(/Movies/i)
    const seriesLinks = screen.getAllByText(/Series/i)
    expect(moviesLinks.length).toBeGreaterThan(0)
    expect(seriesLinks.length).toBeGreaterThan(0)
  })
})
