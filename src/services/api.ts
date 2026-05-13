import type { Distortion } from '@/types'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const DEVICE_ID_KEY = 'cbt-device-id'

function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_ID_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(DEVICE_ID_KEY, id)
  }
  return id
}

async function call<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Device-Id': getDeviceId(),
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    if (response.status === 429) throw new Error('Слишком много запросов, подождите')
    throw new Error(`API error: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export async function analyzeThought(
  thought: string,
  situation?: string,
  emotions?: string,
  signal?: AbortSignal,
): Promise<Distortion[]> {
  const data = await call<{ distortions: Distortion[] }>(
    '/analyze',
    { thought, situation, emotions },
    signal,
  )
  return data.distortions
}

export async function downwardArrowStep(
  thought: string,
  distortions: Distortion[],
  history: { question: string; answer: string }[],
  situation?: string,
  emotions?: string,
  signal?: AbortSignal,
): Promise<{ question: string; isCoreBelief: boolean }> {
  return call(
    '/downward-arrow',
    { thought, distortions, history, situation, emotions },
    signal,
  )
}

export async function socraticStep(
  thought: string,
  distortions: Distortion[],
  history: { question: string; answer: string }[],
  situation?: string,
  emotions?: string,
  signal?: AbortSignal,
): Promise<{ question: string }> {
  return call('/socratic', { thought, distortions, history, situation, emotions }, signal)
}
