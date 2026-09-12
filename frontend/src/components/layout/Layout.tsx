import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Header } from '@/components/common/Header'
import { Footer } from '@/components/common/Footer'
import { AuthModal } from '@/components/common/AuthModal'

export const Layout: React.FC = () => {
  const [isAuthOpen, setIsAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')

  const handleOpenAuth = (mode: 'login' | 'register' = 'login') => {
    setAuthMode(mode)
    setIsAuthOpen(true)
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#0d0d0d] text-gray-100 selection:bg-amber-500 selection:text-black">
      <Header onOpenAuth={handleOpenAuth} />
      <main className="flex-1">
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
