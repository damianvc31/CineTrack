import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Header } from '@/components/common/Header'
import { Footer } from '@/components/common/Footer'
import { AuthModal } from '@/components/common/AuthModal'

export const Layout: React.FC = () => {
  const [isAuthOpen, setIsAuthOpen] = useState(false)

  return (
    <div className="min-h-screen flex flex-col bg-[#0d0d0d] text-gray-100 selection:bg-amber-500 selection:text-black">
      <Header onOpenAuth={() => setIsAuthOpen(true)} />
      <main className="flex-1">
        <Outlet context={{ openAuth: () => setIsAuthOpen(true) }} />
      </main>
      <Footer />
      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />
    </div>
  )
}
