import React, { useState, useEffect, useRef } from 'react'
import { Outlet, useLocation, useNavigationType } from 'react-router-dom'
import { Header } from '@/components/common/Header'
import { Footer } from '@/components/common/Footer'
import { AuthModal } from '@/components/common/AuthModal'

export const Layout: React.FC = () => {
  const [isAuthOpen, setIsAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const location = useLocation()
  const navigationType = useNavigationType()
  const mainRef = useRef<HTMLElement>(null)

  // Cerrar modales en navegación histórica (popstate)
  useEffect(() => {
    const handlePopState = () => {
      setIsAuthOpen(false)
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Manejar el foco en contenedor principal al navegar con atrás/adelante (POP) o push
  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.focus({ preventScroll: true })
    }
  }, [location.pathname, navigationType])

  const handleOpenAuth = (mode: 'login' | 'register' = 'login') => {
    setAuthMode(mode)
    setIsAuthOpen(true)
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#0d0d0d] text-gray-100 selection:bg-amber-500 selection:text-black">
      <Header onOpenAuth={handleOpenAuth} />
      <main ref={mainRef} id="main-content" tabIndex={-1} className="flex-1 outline-none">
        <Outlet context={{ openAuth: handleOpenAuth }} />
      </main>
      <Footer />
      <AuthModal
        isOpen={isAuthOpen}
        initialMode={authMode}
        onClose={() => setIsAuthOpen(false)}
      />
    </div>
  )
}
