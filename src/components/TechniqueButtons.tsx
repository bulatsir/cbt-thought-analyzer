import type { TechniqueType } from '@/types'

interface TechniqueButtonsProps {
  activeTechnique: TechniqueType | null
  onSelect: (technique: TechniqueType) => void
}

const TECHNIQUES: { type: TechniqueType; icon: string; title: string }[] = [
  { type: 'downward-arrow', icon: '↓', title: 'Нисходящая стрелка' },
  { type: 'socratic', icon: '?', title: 'Сократовские вопросы' },
]

export function TechniqueButtons({ activeTechnique, onSelect }: TechniqueButtonsProps) {
  return (
    <div className="flex items-center gap-1">
      {TECHNIQUES.map((t) => (
        <button
          key={t.type}
          type="button"
          title={t.title}
          onClick={() => onSelect(t.type)}
          className={`inline-flex items-center justify-center w-7 h-7 rounded-md border text-xs font-medium transition-colors
            ${
              activeTechnique === t.type
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border text-muted-foreground hover:border-primary/50 hover:text-primary'
            }`}
        >
          {t.icon}
        </button>
      ))}
    </div>
  )
}
