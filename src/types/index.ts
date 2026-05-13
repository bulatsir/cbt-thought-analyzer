export interface Distortion {
  name: string
  explanation: string
}

export type TechniqueType = 'downward-arrow' | 'socratic'

// Нисходящая стрелка: цепочка вопрос → ответ → вопрос
export interface DownwardArrowState {
  type: 'downward-arrow'
  steps: { question: string; answer: string }[]
  currentQuestion: string | null
  status: 'idle' | 'loading' | 'done'
}

// Сократовские вопросы: вопросы с разных ракурсов
export interface SocraticQuestionsState {
  type: 'socratic'
  steps: { question: string; answer: string }[]
  currentQuestion: string | null
  status: 'idle' | 'loading' | 'done'
}

export type TechniqueState = DownwardArrowState | SocraticQuestionsState

export interface BeliefLine {
  id: string
  text: string
  distortions: Distortion[]
  status: 'idle' | 'analyzing' | 'done' | 'error'
  techniques: Partial<Record<TechniqueType, TechniqueState>>
  activeTechnique: TechniqueType | null
}
