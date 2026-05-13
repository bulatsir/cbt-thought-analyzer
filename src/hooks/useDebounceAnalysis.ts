import { useRef, useCallback } from 'react'
import { analyzeThought } from '@/services/api'
import type { BeliefLine } from '@/types'

const DEBOUNCE_MS = 1500

// Кастомный хук — функция, которая использует React-хуки и возвращает данные/методы
// Концептуально: переиспользуемый «кусок логики с состоянием»
export function useDebounceAnalysis(
  onUpdate: (id: string, updates: Partial<BeliefLine>) => void,
  situation: string,
  emotions: string,
) {
  // useRef хранит значение между рендерами БЕЗ перерисовки (в отличие от useState)
  // Map<string, ...> — как dict[str, ...] в Python
  // ReturnType<typeof setTimeout> — TS-утилита: «тип того, что возвращает setTimeout»
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  // AbortController — механизм отмены fetch-запросов (как asyncio.Task.cancel() в Python)
  const controllersRef = useRef<Map<string, AbortController>>(new Map())

  const trigger = useCallback(
    (id: string, text: string) => {
      // .get(id) — как dict.get(id) в Python
      const existingTimer = timersRef.current.get(id)
      if (existingTimer) {
        clearTimeout(existingTimer) // отменяет отложенный вызов
      }

      const existingController = controllersRef.current.get(id)
      if (existingController) {
        existingController.abort() // отменяет текущий HTTP-запрос
      }

      // !text.trim() — если строка пустая (после удаления пробелов)
      // ! — логическое НЕ (Python: not)
      if (!text.trim()) {
        onUpdate(id, { distortions: [], status: 'idle' })
        return
      }

      // setTimeout — выполняет функцию через DEBOUNCE_MS мс
      // Это и есть «debounce»: ждём 1.5 сек паузы перед запросом
      const timer = setTimeout(async () => {
        const controller = new AbortController()
        controllersRef.current.set(id, controller) // .set — как dict[id] = controller

        onUpdate(id, { status: 'analyzing' })

        // try/catch/finally — как try/except/finally в Python
        try {
          const distortions = await analyzeThought(
            text,
            situation,
            emotions,
            controller.signal, // передаём signal чтобы fetch можно было отменить
          )
          // shorthand: { distortions } = { distortions: distortions }
          onUpdate(id, { distortions, status: 'done' })
        } catch (err) {
          // (err as Error) — приведение типа (Python: cast(Error, err))
          // AbortError — ошибка отмены запроса, не настоящая ошибка, просто выходим
          if ((err as Error).name === 'AbortError') return
          onUpdate(id, { distortions: [], status: 'error' })
        } finally {
          // finally — выполнится в любом случае (как в Python)
          controllersRef.current.delete(id) // .delete — как del dict[id]
        }
      }, DEBOUNCE_MS)

      timersRef.current.set(id, timer)
    },
    // Массив зависимостей useCallback: функция пересоздаётся когда эти значения меняются
    [onUpdate, situation, emotions],
  )

  const cancel = useCallback((id: string) => {
    const timer = timersRef.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timersRef.current.delete(id)
    }
    const controller = controllersRef.current.get(id)
    if (controller) {
      controller.abort()
      controllersRef.current.delete(id)
    }
  }, [])

  // Возвращаем объект с двумя методами (shorthand: { trigger } = { trigger: trigger })
  return { trigger, cancel }
}
