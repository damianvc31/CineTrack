import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App Component Smoke Test', () => {
  it('renders the CineTrack frontend base without crashing', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toBeDefined()
  })
})
