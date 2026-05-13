import { useRef, useCallback } from 'react'
import type { TechniqueType } from '@/types'

export function useTechniqueAbort() {
  const controllersRef = useRef<Map<string, AbortController>>(new Map())

  const getKey = (lineId: string, technique: TechniqueType) =>
    `${lineId}-${technique}`

  const getSignal = useCallback(
    (lineId: string, technique: TechniqueType): AbortSignal => {
      const key = getKey(lineId, technique)
      const existing = controllersRef.current.get(key)
      if (existing) {
        existing.abort()
      }
      const controller = new AbortController()
      controllersRef.current.set(key, controller)
      return controller.signal
    },
    [],
  )

  const abort = useCallback(
    (lineId: string, technique: TechniqueType) => {
      const key = getKey(lineId, technique)
      const controller = controllersRef.current.get(key)
      if (controller) {
        controller.abort()
        controllersRef.current.delete(key)
      }
    },
    [],
  )

  const cleanup = useCallback(
    (lineId: string, technique: TechniqueType) => {
      const key = getKey(lineId, technique)
      controllersRef.current.delete(key)
    },
    [],
  )

  return { getSignal, abort, cleanup }
}
