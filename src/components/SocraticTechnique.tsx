import { useState, useRef, useEffect } from 'react'
import type { SocraticQuestionsState, Distortion } from '@/types'
import { socraticStep } from '@/services/api'

interface SocraticTechniqueProps {
  thought: string
  distortions: Distortion[]
  situation: string
  emotions: string
  state: SocraticQuestionsState
  onUpdate: (state: SocraticQuestionsState) => void
  getSignal: () => AbortSignal
  cleanup: () => void
}

const MAX_STEPS = 3

export function SocraticTechnique({
  thought,
  distortions,
  situation,
  emotions,
  state,
  onUpdate,
  getSignal,
  cleanup,
}: SocraticTechniqueProps) {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Запрашиваем первый вопрос при монтировании
  useEffect(() => {
    if (state.status !== 'idle') return
    fetchNextQuestion(state)
  }, [])

  useEffect(() => {
    if (state.currentQuestion && state.status !== 'loading') {
      inputRef.current?.focus()
    }
  }, [state.currentQuestion, state.status])

  const fetchNextQuestion = async (currentState: SocraticQuestionsState) => {
    onUpdate({ ...currentState, status: 'loading', currentQuestion: null })
    const signal = getSignal()
    try {
      const result = await socraticStep(
        thought,
        distortions,
        currentState.steps,
        situation,
        emotions,
        signal,
      )
      onUpdate({
        ...currentState,
        currentQuestion: result.question,
        status: 'done',
      })
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      onUpdate({ ...currentState, status: 'done', currentQuestion: 'Не удалось получить вопрос.' })
    } finally {
      cleanup()
    }
  }

  const handleSubmit = () => {
    if (!input.trim() || !state.currentQuestion) return

    const newSteps = [...state.steps, { question: state.currentQuestion, answer: input.trim() }]
    const newState: SocraticQuestionsState = {
      ...state,
      steps: newSteps,
      currentQuestion: null,
    }

    setInput('')

    if (newSteps.length >= MAX_STEPS) {
      onUpdate({ ...newState, status: 'done' })
    } else {
      fetchNextQuestion(newState)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="p-4 flex flex-col gap-3">
      {state.steps.map((step, i) => (
        <div key={i} className="flex flex-col gap-1">
          <div className="text-sm text-primary/80">
            <span className="font-medium">→</span> {step.question}
          </div>
          <div className="text-sm pl-4 text-foreground/80">{step.answer}</div>
        </div>
      ))}

      {state.status === 'loading' && (
        <div className="text-sm text-muted-foreground animate-pulse">Формулирую вопрос...</div>
      )}

      {state.currentQuestion && state.status === 'done' && state.steps.length < MAX_STEPS && (
        <div className="flex flex-col gap-2">
          <div className="text-sm text-primary/80">
            <span className="font-medium">→</span> {state.currentQuestion}
          </div>
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Ваш ответ..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!input.trim()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              →
            </button>
          </div>
        </div>
      )}

      {state.steps.length >= MAX_STEPS && (
        <div className="text-xs text-muted-foreground italic mt-1">
          Сессия завершена — рассмотрено {MAX_STEPS} ракурсов.
        </div>
      )}
    </div>
  )
}
