interface SituationFieldProps {
  value: string
  onChange: (value: string) => void
}

export function SituationField({ value, onChange }: SituationFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-muted-foreground">
        A — Ситуация
      </label>
      <textarea
        className="min-h-[120px] w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        placeholder="Что произошло? Опишите ситуацию или триггер."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
