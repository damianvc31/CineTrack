import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { LanguageProvider } from '@/context/LanguageContext'
import { AuthProvider } from '@/context/AuthContext'
import { Layout } from '@/components/layout/Layout'
import { HomePage } from '@/pages/HomePage'
import { CatalogPage } from '@/pages/CatalogPage'
import { TitleDetailPage } from '@/pages/TitleDetailPage'
import { LibraryPage } from '@/pages/LibraryPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { RecommendationsPage } from '@/pages/RecommendationsPage'
import { ReviewsPage } from '@/pages/ReviewsPage'
import { SettingsPage } from '@/pages/SettingsPage'

function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname])

  return null
}

function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <BrowserRouter>
          <ScrollToTop />
          <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="catalog" element={<CatalogPage />} />
            <Route path="titles/:id" element={<TitleDetailPage />} />
            <Route path="library" element={<LibraryPage />} />
            <Route path="reviews" element={<ReviewsPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="recommendations" element={<RecommendationsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </LanguageProvider>
  )
}

export default App
