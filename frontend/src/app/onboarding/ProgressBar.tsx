'use client'

const STEPS = [
  { num: 1, label: 'Foto' },
  { num: 2, label: 'Hidangan' },
  { num: 3, label: 'Gaya' },
  { num: 4, label: 'Cipta' },
]

interface ProgressBarProps {
  currentStep: number
}

export default function ProgressBar({ currentStep }: ProgressBarProps) {
  return (
    <div className="mb-8">
      <p className="text-sm text-gray-500 mb-2 text-center">
        {currentStep} daripada 4 — {STEPS[currentStep - 1]?.label}
      </p>
      <div className="flex gap-2">
        {STEPS.map(s => (
          <div
            key={s.num}
            className={`h-2 flex-1 rounded-full transition-colors ${
              s.num <= currentStep ? 'bg-orange-500' : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
    </div>
  )
}
