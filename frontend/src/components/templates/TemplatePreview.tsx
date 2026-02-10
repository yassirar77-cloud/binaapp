'use client'

import dynamic from 'next/dynamic'

const ParticleGlobe = dynamic(() => import('./animations/ParticleGlobe'), { ssr: false })
const MatrixCode = dynamic(() => import('./animations/MatrixCode'), { ssr: false })
const GradientWave = dynamic(() => import('./animations/GradientWave'), { ssr: false })
const FloatingFood = dynamic(() => import('./animations/FloatingFood'), { ssr: false })
const NeonGrid = dynamic(() => import('./animations/NeonGrid'), { ssr: false })
const MorphingBlob = dynamic(() => import('./animations/MorphingBlob'), { ssr: false })
const Aurora = dynamic(() => import('./animations/Aurora'), { ssr: false })
const Spotlight = dynamic(() => import('./animations/Spotlight'), { ssr: false })
const ParallaxLayers = dynamic(() => import('./animations/ParallaxLayers'), { ssr: false })

interface TemplatePreviewProps {
  styleKey: string
  isVisible: boolean
}

export default function TemplatePreview({ styleKey, isVisible }: TemplatePreviewProps) {
  if (!isVisible) {
    return <div className="w-full h-full" style={{ background: '#0a0a0f' }} />
  }

  switch (styleKey) {
    case 'particle-globe':
      return <ParticleGlobe isVisible={isVisible} />
    case 'gradient-wave':
      return <GradientWave />
    case 'floating-food':
      return <FloatingFood />
    case 'neon-grid':
      return <NeonGrid />
    case 'morphing-blob':
      return <MorphingBlob />
    case 'matrix-code':
      return <MatrixCode isVisible={isVisible} />
    case 'aurora':
      return <Aurora />
    case 'spotlight':
      return <Spotlight />
    case 'parallax-layers':
      return <ParallaxLayers />
    default:
      return <div className="w-full h-full" style={{ background: '#0a0a0f' }} />
  }
}
