import { useState, useCallback } from 'react'
import { BeliefLineComponent } from './BeliefLine'
import { useDebounceAnalysis } from '@/hooks/useDebounceAnalysis'
import { useTechniqueAbort } from '@/hooks/useTechniqueAbort'
import type {
  BeliefLine,
  TechniqueType,
  TechniqueState,
  DownwardArrowState,
  SocraticQuestionsState,
} from '@/types'

interface BeliefsFieldProps {
  situation: string
  emotions: string
}

function createLine(): BeliefLine {
  return {
    id: crypto.randomUUID(),
    text: '',
    distortions: [],
    status: 'idle',
    techniques: {},
    activeTechnique: null,
  }
}

function createInitialState(technique: TechniqueType): TechniqueState {
  switch (technique) {
    case 'downward-arrow':
      return { type: 'downward-arrow', steps: [], currentQuestion: null, status: 'idle' } satisfies DownwardArrowState
    case 'socratic':
      return { type: 'socratic', steps: [], currentQuestion: null, status: 'idle' } satisfies SocraticQuestionsState
  }
}

export function BeliefsField({ situation, emotions }: BeliefsFieldProps) {
  const [lines, setLines] = useState<BeliefLine[]>([createLine()])
  const [focusIndex, setFocusIndex] = useState(0)

  const updateLine = useCallback((id: string, updates: Partial<BeliefLine>) => {
    setLines((prev) =>
      prev.map((line) => (line.id === id ? { ...line, ...updates } : line)),
    )
  }, [])

  const { trigger, cancel } = useDebounceAnalysis(updateLine, situation, emotions)
  const { getSignal, cleanup } = useTechniqueAbort()

  const handleChange = (index: number, text: string) => {
    const line = lines[index]
    updateLine(line.id, { text })
    trigger(line.id, text)
  }

  const handleEnter = (index: number) => {
    const newLine = createLine()
    setLines((prev) => {
      const next = [...prev]
      next.splice(index + 1, 0, newLine)
      return next
    })
    setFocusIndex(index + 1)
  }

  const handleBackspaceEmpty = (index: number) => {
    if (lines.length <= 1) return
    const line = lines[index]
    cancel(line.id)
    setLines((prev) => prev.filter((_, i) => i !== index))
    setFocusIndex(Math.max(0, index - 1))
  }

  const handleTechniqueSelect = (lineId: string, technique: TechniqueType) => {
    setLines((prev) =>
      prev.map((line) => {
        if (line.id === lineId) {
          if (line.activeTechnique === technique) {
            return { ...line, activeTechnique: null }
          }
          const techniques = { ...line.techniques }
          if (!techniques[technique]) {
            techniques[technique] = createInitialState(technique)
          }
          return { ...line, activeTechnique: technique, techniques }
        }
        if (line.activeTechnique !== null) {
          return { ...line, activeTechnique: null }
        }
        return line
      }),
    )
  }

  const handleUpdateTechnique = (lineId: string, technique: TechniqueType, state: TechniqueState) => {
    setLines((prev) =>
      prev.map((line) => {
        if (line.id !== lineId) return line
        return {
          ...line,
          techniques: { ...line.techniques, [technique]: state },
        }
      }),
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-muted-foreground">
        B — Автоматические мысли
      </label>
      <div className="flex flex-col gap-2">
        {lines.map((line, index) => (
          <BeliefLineComponent
            key={line.id}
            line={line}
            onChange={(text) => handleChange(index, text)}
            onEnter={() => handleEnter(index)}
            onBackspaceEmpty={() => handleBackspaceEmpty(index)}
            autoFocus={index === focusIndex}
            situation={situation}
            emotions={emotions}
            onTechniqueSelect={(technique) => handleTechniqueSelect(line.id, technique)}
            onUpdateTechnique={(technique, state) => handleUpdateTechnique(line.id, technique, state)}
            getSignal={(technique) => getSignal(line.id, technique)}
            cleanupSignal={(technique) => cleanup(line.id, technique)}
          />
        ))}
      </div>
    </div>
  )
}
