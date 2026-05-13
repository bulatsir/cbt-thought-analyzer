import { useState } from 'react'
import { EmotionsField } from './EmotionsField'
import { SituationField } from './SituationField'
import { BeliefsField } from './BeliefsField'

export function ABCLayout() {
  // useState — React-хук: создаёт «переменную состояния» + функцию для её изменения
  // Аналог в Python: emotions = "" / self.emotions = ""
  // Но в React нельзя просто emotions = "новое" — нужно вызвать setEmotions("новое"),
  // чтобы React узнал об изменении и перерисовал компонент
  const [emotions, setEmotions] = useState('')
  const [situation, setSituation] = useState('')

  // JSX: className вместо class (class — зарезервированное слово в JS)
  // Строки типа "mx-auto max-w-4xl" — это Tailwind CSS классы
  return (
    <div className="mx-auto max-w-4xl p-6 flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">CBT Thought Analyzer</h1>
      <div className="grid grid-cols-2 gap-4">
        {/* Передаём значение и функцию-сеттер как пропсы (аргументы компонента) */}
        <EmotionsField value={emotions} onChange={setEmotions} />
        <SituationField value={situation} onChange={setSituation} />
      </div>
      <BeliefsField situation={situation} emotions={emotions} />
    </div>
  )
}
