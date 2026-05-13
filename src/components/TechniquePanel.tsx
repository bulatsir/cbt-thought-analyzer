import type { BeliefLine as BeliefLineType, TechniqueState, TechniqueType } from '@/types'
import { SocraticTechnique } from './SocraticTechnique'
import { DownwardArrowTechnique } from './DownwardArrowTechnique'

interface TechniquePanelProps {
  line: BeliefLineType
  situation: string
  emotions: string
  onUpdateTechnique: (technique: TechniqueType, state: TechniqueState) => void
  getSignal: (technique: TechniqueType) => AbortSignal
  cleanup: (technique: TechniqueType) => void
}

const TECHNIQUE_TITLES: Record<TechniqueType, string> = {
  'downward-arrow': 'Нисходящая стрелка',
  socratic: 'Сократовские вопросы',
}

export function TechniquePanel({
  line,
  situation,
  emotions,
  onUpdateTechnique,
  getSignal,
  cleanup,
}: TechniquePanelProps) {
  const activeTechnique = line.activeTechnique
  const isOpen = activeTechnique !== null

  return (
    <div
      className="grid transition-[grid-template-rows] duration-300 ease-in-out"
      style={{ gridTemplateRows: isOpen ? '1fr' : '0fr' }}
    >
      <div className="overflow-hidden">
        {activeTechnique && (
          <div className="mt-2 rounded-lg border border-border bg-card">
            <div className="px-4 py-2 border-b border-border">
              <span className="text-xs font-medium text-muted-foreground">
                {TECHNIQUE_TITLES[activeTechnique]}
              </span>
            </div>
            <TechniqueContent
              line={line}
              technique={activeTechnique}
              situation={situation}
              emotions={emotions}
              onUpdateTechnique={onUpdateTechnique}
              getSignal={getSignal}
              cleanup={cleanup}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function TechniqueContent({
  line,
  technique,
  situation,
  emotions,
  onUpdateTechnique,
  getSignal,
  cleanup,
}: {
  line: BeliefLineType
  technique: TechniqueType
  situation: string
  emotions: string
  onUpdateTechnique: (technique: TechniqueType, state: TechniqueState) => void
  getSignal: (technique: TechniqueType) => AbortSignal
  cleanup: (technique: TechniqueType) => void
}) {
  const state = line.techniques[technique]
  if (!state) return null

  const commonProps = {
    thought: line.text,
    distortions: line.distortions,
    situation,
    emotions,
    getSignal: () => getSignal(technique),
    cleanup: () => cleanup(technique),
  }

  switch (technique) {
    case 'socratic':
      return (
        <SocraticTechnique
          {...commonProps}
          state={state as import('@/types').SocraticQuestionsState}
          onUpdate={(s) => onUpdateTechnique(technique, s)}
        />
      )
    case 'downward-arrow':
      return (
        <DownwardArrowTechnique
          {...commonProps}
          state={state as import('@/types').DownwardArrowState}
          onUpdate={(s) => onUpdateTechnique(technique, s)}
        />
      )
    default:
      return null
  }
}
