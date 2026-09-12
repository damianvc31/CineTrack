import React, { useState } from 'react'
import { Lock, Globe, AlertCircle, CheckCircle } from 'lucide-react'
import { authService } from '@/services/authService'
import { useLanguage } from '@/context/LanguageContext'

export const SettingsPage: React.FC = () => {
  const { language, setLanguage, t } = useLanguage()

  // Password state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwdLoading, setPwdLoading] = useState(false)
  const [pwdError, setPwdError] = useState<string | null>(null)
  const [pwdSuccess, setPwdSuccess] = useState<string | null>(null)

  const [langSaved, setLangSaved] = useState(false)

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwdError(null)
    setPwdSuccess(null)

    if (!currentPassword) {
      setPwdError('Current password is required.')
      return
    }
    if (newPassword.length < 6) {
      setPwdError('New password must be at least 6 characters long.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPwdError('New passwords do not match.')
      return
    }

    setPwdLoading(true)
    try {
      await authService.changePassword(currentPassword, newPassword)
      setPwdSuccess('Password changed successfully.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: unknown) {
      if (err instanceof Error) {
        setPwdError(err.message)
      } else {
        setPwdError('Failed to change password.')
      }
    } finally {
      setPwdLoading(false)
    }
  }

  const handleLanguageChange = (newLang: 'en' | 'es') => {
    setLanguage(newLang)
    setLangSaved(true)
    setTimeout(() => setLangSaved(false), 2500)
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Title */}
      <div className="pb-4 border-b border-[#262626]">
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">{t('settingsHeading')}</h1>
        <p className="text-xs sm:text-sm text-gray-400 mt-1">
          {t('settingsSubtitle')}
        </p>
      </div>

      {/* Security & Password */}
      <section className="bg-[#141414] border border-[#262626] rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
        <div className="flex items-center gap-3 pb-3 border-b border-[#262626]">
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">{t('securityPassword')}</h2>
            <p className="text-xs text-gray-400">{language === 'es' ? 'Cambia la contraseña de tu cuenta de forma segura' : 'Change your account password securely'}</p>
          </div>
        </div>

        {pwdError && (
          <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 flex items-center gap-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{pwdError}</span>
          </div>
        )}

        {pwdSuccess && (
          <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/60 flex items-center gap-2 text-xs text-emerald-300">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>{pwdSuccess}</span>
          </div>
        )}

        <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">
              {t('currentPassword')}
            </label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">
              {t('newPassword')} <span className="text-[10px] text-gray-500">{language === 'es' ? '(mín. 6 caracteres)' : '(min. 6 characters)'}</span>
            </label>
            <input
              type="password"
              required
              minLength={6}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">
              {t('confirmPassword')}
            </label>
            <input
              type="password"
              required
              minLength={6}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 bg-[#181818] border border-[#333333] rounded-xl text-xs text-white placeholder-gray-600 focus:outline-none focus:border-amber-500/60"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={pwdLoading}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black text-xs font-bold shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
            >
              {pwdLoading ? (language === 'es' ? 'Actualizando Contraseña...' : 'Updating Password...') : t('updatePassword')}
            </button>
          </div>
        </form>
      </section>

      {/* Interface Preferences */}
      <section className="bg-[#141414] border border-[#262626] rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
        <div className="flex items-center gap-3 pb-3 border-b border-[#262626]">
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">{t('interfacePreferences')}</h2>
            <p className="text-xs text-gray-400">{t('interfaceLanguageDesc')}</p>
          </div>
        </div>

        <div className="space-y-4 max-w-md">
          <label className="block text-xs font-medium text-gray-300">
            {t('interfaceLanguage')}
          </label>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleLanguageChange('en')}
              className={`p-4 rounded-xl border text-left transition-all ${
                language === 'en'
                  ? 'bg-amber-500/10 border-amber-500 text-white shadow-md'
                  : 'bg-[#181818] border-[#2c2c2c] text-gray-400 hover:text-gray-200 hover:border-[#444444]'
              }`}
            >
              <div className="font-bold text-xs text-white">English</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Default UI language</div>
            </button>

            <button
              type="button"
              onClick={() => handleLanguageChange('es')}
              className={`p-4 rounded-xl border text-left transition-all ${
                language === 'es'
                  ? 'bg-amber-500/10 border-amber-500 text-white shadow-md'
                  : 'bg-[#181818] border-[#2c2c2c] text-gray-400 hover:text-gray-200 hover:border-[#444444]'
              }`}
            >
              <div className="font-bold text-xs text-white">Español</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Menús y géneros traducidos</div>
            </button>
          </div>

          {langSaved && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 pt-1">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>{t('preferencesSaved')}</span>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
