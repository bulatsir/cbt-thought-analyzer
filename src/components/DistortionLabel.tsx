import { useState } from 'react'
import type { Distortion } from '@/types'

interface DistortionLabelProps {
  distortion: Distortion
}

export function DistortionLabel({ distortion }: DistortionLabelProps) {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary cursor-default">
        {distortion.name}
      </span>
      {showTooltip && distortion.explanation && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-md bg-popover border border-border p-2 text-xs text-popover-foreground shadow-md z-10">
          {distortion.explanation}
        </span>
      )}
    </span>
  )
}
