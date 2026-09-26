import React, { useState } from 'react'
import { Lock, Globe, AlertCircle, CheckCircle, Sliders, RefreshCw } from 'lucide-react'
import { authService } from '@/services/authService'
import { useAuth } from '@/context/AuthContext'
import { useLanguage } from '@/context/LanguageContext'
import type { VarietyLevel } from '@/types/auth'

const VARIETY_LEVELS: VarietyLevel[] = ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']

export const SettingsPage: React.FC = () => {
  const { user, updateUser } = useAuth()
  const { language, setLanguage, t } = useLanguage()

  // Password state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwdLoading, setPwdLoading] = useState(false)
  const [pwdError, setPwdError] = useState<string | null>(null)
  const [pwdSuccess, setPwdSuccess] = useState<string | null>(null)

  const [langSaved, setLangSaved] = useState(false)

  // Variety level state
  const [variety, setVariety] = useState<VarietyLevel>(() => {
    return (user?.preferencia_variedad_ia as VarietyLevel) || (localStorage.getItem('cinetrack_variety_guest') as VarietyLevel) || 'MEDIUM'
  })
  const [varietySaving, setVarietySaving] = useState(false)
  const [varietySaved, setVarietySaved] = useState(false)
  const [varietyError, setVarietyError] = useState<string | null>(null)

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

  const handleVarietyChange = async (newLevel: VarietyLevel) => {
    setVariety(newLevel)
    setVarietyError(null)
    setVarietySaved(false)
    if (user) {
      setVarietySaving(true)
      try {
        const updated = await authService.updateProfile({ preferencia_variedad_ia: newLevel })
        updateUser(updated)
        setVarietySaved(true)
        setTimeout(() => setVarietySaved(false), 3000)
      } catch (err: unknown) {
        setVarietyError(err instanceof Error ? err.message : 'Error al guardar preferencia')
      } finally {
        setVarietySaving(false)
      }
    } else {
      localStorage.setItem('cinetrack_variety_guest', newLevel)
      setVarietySaved(true)
      setTimeout(() => setVarietySaved(false), 3000)
    }
  }

  const currentSliderIndex = VARIETY_LEVELS.indexOf(variety) !== -1 ? VARIETY_LEVELS.indexOf(variety) : 2

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

      {/* AI Recommender Variety & Surprise Factor */}
      <section className="bg-[#141414] border border-[#262626] rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
        <div className="flex items-center gap-3 pb-3 border-b border-[#262626]">
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">{t('aiVarietyHeading')}</h2>
            <p className="text-xs text-gray-400">{t('aiVarietyDesc')}</p>
          </div>
        </div>

        {varietyError && (
          <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 flex items-center gap-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{varietyError}</span>
          </div>
        )}

        <div className="space-y-6 max-w-2xl">
          {/* Slider Controls */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold text-gray-300">
              <span className="text-blue-400">{t('aiVarietyLevel_VERY_LOW_name')}</span>
              <span className="text-amber-400 font-bold">{t(`aiVarietyLevel_${variety}_name`)}</span>
              <span className="text-purple-400">{t('aiVarietyLevel_VERY_HIGH_name')}</span>
            </div>

            <div className="relative pt-1 pb-2">
              <input
                type="range"
                min={0}
                max={4}
                step={1}
                value={currentSliderIndex}
                disabled={varietySaving}
                onChange={(e) => {
                  const idx = parseInt(e.target.value, 10)
                  handleVarietyChange(VARIETY_LEVELS[idx])
                }}
                className="w-full h-2 bg-[#262626] rounded-lg appearance-none cursor-pointer accent-amber-500 disabled:opacity-50"
              />
              
              {/* Ticks and mini labels */}
              <div className="flex justify-between text-[11px] text-gray-500 px-1 pt-1.5 font-medium">
                {VARIETY_LEVELS.map((level, idx) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => handleVarietyChange(level)}
                    className={`transition-colors cursor-pointer text-center ${
                      variety === level ? 'text-amber-400 font-bold' : 'hover:text-gray-300'
                    }`}
                  >
                    <span className="block text-[10px] sm:text-xs">
                      {idx === 0 ? '1' : idx === 1 ? '2' : idx === 2 ? '3' : idx === 3 ? '4' : '5'}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Descriptive Card for Current Level */}
          <div className="p-4 rounded-xl bg-[#181818] border border-[#2d2d2d] space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-xs font-bold text-white tracking-wide">
                  {t(`aiVarietyLevel_${variety}_name`)}
                </span>
              </div>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-[#252525] text-gray-400 border border-[#333333]">
                {variety}
              </span>
            </div>
            <p className="text-xs text-gray-300 leading-relaxed">
              {t(`aiVarietyLevel_${variety}_desc`)}
            </p>
          </div>

          {/* Feedback messages */}
          {varietySaving && (
            <div className="flex items-center gap-2 text-xs text-amber-400">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>{language === 'es' ? 'Guardando preferencia...' : 'Saving preference...'}</span>
            </div>
          )}

          {varietySaved && (
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span>{user ? t('aiVarietySaved') : `${t('aiVarietySaved')} ${t('aiVarietyGuestNote')}`}</span>
            </div>
          )}
        </div>
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
