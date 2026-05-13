interface EmotionsFieldProps {
  value: string
  onChange: (value: string) => void
}

export function EmotionsField({ value, onChange }: EmotionsFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-muted-foreground">
        C — Эмоции и последствия
      </label>
      <textarea
        className="min-h-[120px] w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        placeholder="Что вы чувствуете? Какие эмоции, ощущения в теле, поведение?"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
