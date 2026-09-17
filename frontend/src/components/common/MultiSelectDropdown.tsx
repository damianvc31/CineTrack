import React, { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check, X, Search } from 'lucide-react'

export interface MultiSelectOption {
  value: string
  label: string
  count?: number
  icon?: React.ReactNode
}

interface ToggleConfig {
  label?: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}

interface MultiSelectDropdownProps {
  label: string
  options: MultiSelectOption[]
  selectedValues: string[]
  onChange: (values: string[]) => void
  placeholderSearch?: string
  emptyMessage?: string
  clearLabel?: string
  toggleConfig?: ToggleConfig
}

export const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  label,
  options,
  selectedValues,
  onChange,
  placeholderSearch = 'Search...',
  emptyMessage = 'No options found',
  clearLabel = 'Clear',
  toggleConfig,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Cerrar al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filteredOptions = options.filter((opt) =>
    opt.label.toLowerCase().includes(search.toLowerCase()) ||
    opt.value.toLowerCase().includes(search.toLowerCase())
  )

  const toggleOption = (val: string) => {
    if (selectedValues.includes(val)) {
      onChange(selectedValues.filter((v) => v !== val))
    } else {
      onChange([...selectedValues, val])
    }
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange([])
  }

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* Botón activador */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
          selectedValues.length > 0
            ? 'bg-amber-500/10 border-amber-500/50 text-amber-300 hover:border-amber-400'
            : 'bg-[#0d0d0d] border-[#262626] text-gray-200 hover:border-gray-600'
        }`}
      >
        <span>{label}</span>
        {selectedValues.length > 0 && (
          <span className="flex items-center justify-center px-1.5 py-0.2 bg-amber-500 text-black font-bold rounded-full text-[10px] leading-tight">
            {selectedValues.length}
          </span>
        )}
        <ChevronDown
          className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-150 ${
            isOpen ? 'rotate-180 text-amber-400' : ''
          }`}
        />
      </button>

      {/* Popover / Menú desplegable */}
      {isOpen && (
        <div className="absolute left-0 mt-1.5 w-64 max-h-80 bg-[#141414] border border-[#2e2e2e] rounded-xl shadow-2xl z-50 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-100">
          {/* Header con toggle opcional y limpiar */}
          <div className="p-2 border-b border-[#262626] flex flex-col gap-2 bg-[#1a1a1a]">
            {toggleConfig && (
              <div className="flex items-center justify-between text-[11px] px-1">
                {toggleConfig.label && (
                  <span className="text-gray-400 font-medium">{toggleConfig.label}:</span>
                )}
                <div className="flex items-center bg-[#0d0d0d] p-0.5 rounded-lg border border-[#262626]">
                  {toggleConfig.options.map((opt) => {
                    const active = toggleConfig.value === opt.value
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => toggleConfig.onChange(opt.value)}
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                          active
                            ? 'bg-amber-500 text-black shadow-sm'
                            : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        {opt.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Buscador interno */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={placeholderSearch}
                className="w-full pl-8 pr-7 py-1 text-xs bg-[#0d0d0d] border border-[#262626] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-amber-500"
                autoFocus
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Fila de acciones (contadores y limpiar) */}
            {selectedValues.length > 0 && (
              <div className="flex items-center justify-between px-1 text-[11px] text-gray-400">
                <span>{selectedValues.length} seleccionados</span>
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-amber-400 hover:text-amber-300 hover:underline text-[11px]"
                >
                  {clearLabel}
                </button>
              </div>
            )}
          </div>

          {/* Lista de opciones con scroll */}
          <div className="overflow-y-auto max-h-52 p-1.5 divide-y divide-transparent">
            {filteredOptions.length === 0 ? (
              <div className="py-4 text-center text-xs text-gray-500">{emptyMessage}</div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = selectedValues.includes(opt.value)
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggleOption(opt.value)}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors text-left ${
                      isSelected
                        ? 'bg-amber-500/15 text-amber-200'
                        : 'text-gray-300 hover:bg-[#202020] hover:text-white'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <div
                        className={`w-3.5 h-3.5 rounded flex items-center justify-center border transition-colors shrink-0 ${
                          isSelected
                            ? 'bg-amber-500 border-amber-500 text-black'
                            : 'border-gray-600 bg-[#0d0d0d]'
                        }`}
                      >
                        {isSelected && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                      </div>
                      {opt.icon && <span className="shrink-0 flex items-center">{opt.icon}</span>}
                      <span className="truncate">{opt.label}</span>
                    </div>

                    {opt.count !== undefined && (
                      <span className="text-[10px] text-gray-500 ml-2 shrink-0 font-mono">
                        {opt.count}
                      </span>
                    )}
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
