import { useRef, useEffect } from 'react'
import { DistortionLabel } from './DistortionLabel'
import { TechniqueButtons } from './TechniqueButtons'
import { TechniquePanel } from './TechniquePanel'
import type { BeliefLine as BeliefLineType, TechniqueType, TechniqueState } from '@/types'

interface BeliefLineProps {
  line: BeliefLineType
  onChange: (text: string) => void
  onEnter: () => void
  onBackspaceEmpty: () => void
  autoFocus?: boolean
  situation: string
  emotions: string
  onTechniqueSelect: (technique: TechniqueType) => void
  onUpdateTechnique: (technique: TechniqueType, state: TechniqueState) => void
  getSignal: (technique: TechniqueType) => AbortSignal
  cleanupSignal: (technique: TechniqueType) => void
}

export function BeliefLineComponent({
  line,
  onChange,
  onEnter,
  onBackspaceEmpty,
  autoFocus,
  situation,
  emotions,
  onTechniqueSelect,
  onUpdateTechnique,
  getSignal,
  cleanupSignal,
}: BeliefLineProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (autoFocus) {
      inputRef.current?.focus()
    }
  }, [autoFocus])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      onEnter()
    }
    if (e.key === 'Backspace' && line.text === '') {
      e.preventDefault()
      onBackspaceEmpty()
    }
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Введите мысль..."
          value={line.text}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="flex items-center gap-1 min-w-0 shrink-0">
          {line.status === 'analyzing' && (
            <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground animate-pulse">
              Анализ...
            </span>
          )}
          {line.status === 'error' && (
            <span className="inline-flex items-center rounded-full bg-destructive/10 px-2.5 py-0.5 text-xs text-destructive">
              Ошибка
            </span>
          )}
          {line.status === 'done' &&
            line.distortions.map((d, i) => (
              <DistortionLabel key={i} distortion={d} />
            ))}
          {line.status === 'done' && (
            <TechniqueButtons
              activeTechnique={line.activeTechnique}
              onSelect={onTechniqueSelect}
            />
          )}
        </div>
      </div>
      <TechniquePanel
        line={line}
        situation={situation}
        emotions={emotions}
        onUpdateTechnique={onUpdateTechnique}
        getSignal={getSignal}
        cleanup={cleanupSignal}
      />
    </div>
  )
}
