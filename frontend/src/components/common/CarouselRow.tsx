import React, { useRef, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { TitleCard as TitleCardType } from '@/types/catalog'
import { TitleCard } from './TitleCard'
import { useLanguage } from '@/context/LanguageContext'

interface CarouselRowProps {
  title: string
  subtitle?: string
  icon?: React.ReactNode
  titles: TitleCardType[]
  viewMoreLink?: string
  onOpenAuth?: (mode?: 'login' | 'register') => void
  onStateChange?: (action: 'favorite' | 'watchlist' | 'watched', titleId: number) => void
}

export const CarouselRow: React.FC<CarouselRowProps> = ({
  title,
  subtitle,
  icon,
  titles,
  viewMoreLink,
  onOpenAuth,
  onStateChange,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { t } = useLanguage()
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(true)

  const checkScroll = () => {
    if (scrollRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current
      setCanScrollLeft(scrollLeft > 10)
      setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 10)
    }
  }

  useEffect(() => {
    checkScroll()
    window.addEventListener('resize', checkScroll)
    return () => window.removeEventListener('resize', checkScroll)
  }, [titles])

  const handleScroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const { clientWidth } = scrollRef.current
      const scrollAmount = direction === 'left' ? -clientWidth * 0.75 : clientWidth * 0.75
      scrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' })
    }
  }

  if (!titles || titles.length === 0) {
    return null
  }

  return (
    <section className="my-8 relative group/carousel">
      {/* Header de la Fila */}
      <div className="flex items-center justify-between mb-3.5 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2.5">
          {icon && <span className="text-xl shrink-0 text-amber-500">{icon}</span>}
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-amber-400 tracking-tight flex items-center gap-2">
              {title}
            </h2>
            {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
          </div>
        </div>

        {viewMoreLink && (
          <Link
            to={viewMoreLink}
            className="flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-amber-400 transition-colors group/link py-1"
          >
            <span>{t('viewAll')}</span>
            <ChevronRight className="w-3.5 h-3.5 group-hover/link:translate-x-0.5 transition-transform" />
          </Link>
        )}
      </div>

      {/* Contenedor Carrusel con Scroll y Flechas Desktop */}
      <div className="relative">
        {/* Flecha Izquierda (Desktop) */}
        {canScrollLeft && (
          <button
            onClick={() => handleScroll('left')}
            aria-label="Scroll left"
            className="hidden md:flex absolute -left-2 lg:-left-4 top-1/2 -translate-y-1/2 z-30 w-9 h-9 items-center justify-center rounded-full bg-[#141414]/90 hover:bg-amber-500 hover:text-black text-white border border-[#262626] shadow-2xl backdrop-blur-md opacity-0 group-hover/carousel:opacity-100 transition-all duration-200"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        )}

        {/* Flecha Derecha (Desktop) */}
        {canScrollRight && (
          <button
            onClick={() => handleScroll('right')}
            aria-label="Scroll right"
            className="hidden md:flex absolute -right-2 lg:-right-4 top-1/2 -translate-y-1/2 z-30 w-9 h-9 items-center justify-center rounded-full bg-[#141414]/90 hover:bg-amber-500 hover:text-black text-white border border-[#262626] shadow-2xl backdrop-blur-md opacity-0 group-hover/carousel:opacity-100 transition-all duration-200"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        )}

        {/* Scrollable Container (Touch Swipe nativo en móvil / Smooth Scroll) */}
        <div
          ref={scrollRef}
          onScroll={checkScroll}
          className="flex items-stretch gap-3 sm:gap-4 overflow-x-auto no-scrollbar scroll-smooth px-4 sm:px-6 lg:px-8 py-2 snap-x snap-mandatory"
        >
          {titles.map((item) => (
            <div key={`${item.tipo}-${item.id}`} className="snap-start shrink-0">
              <TitleCard title={item} onStateChange={onStateChange} onOpenAuth={onOpenAuth} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
