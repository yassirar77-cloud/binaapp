/**
 * Device Preview Component
 * Responsive preview with device frames (Mobile, Tablet, Desktop)
 */

'use client'

import { useState } from 'react'
import { Monitor, Tablet, Smartphone, RotateCw } from 'lucide-react'

interface DevicePreviewProps {
  htmlContent: string
  title?: string
}

type DeviceType = 'mobile' | 'tablet' | 'desktop'
type Orientation = 'portrait' | 'landscape'

interface DeviceConfig {
  name: string
  icon: any
  width: number
  height: number
  scale: number
  frame: boolean
}

const DEVICE_CONFIGS: Record<DeviceType, DeviceConfig> = {
  mobile: {
    name: 'Mobile',
    icon: Smartphone,
    width: 375,
    height: 667,
    scale: 0.8,
    frame: true
  },
  tablet: {
    name: 'Tablet',
    icon: Tablet,
    width: 768,
    height: 1024,
    scale: 0.6,
    frame: true
  },
  desktop: {
    name: 'Desktop',
    icon: Monitor,
    width: 1920,
    height: 1080,
    scale: 0.5,
    frame: false
  }
}

export default function DevicePreview({ htmlContent, title = "Preview" }: DevicePreviewProps) {
  const [device, setDevice] = useState<DeviceType>('desktop')
  const [orientation, setOrientation] = useState<Orientation>('portrait')

  const config = DEVICE_CONFIGS[device]
  const canRotate = device !== 'desktop'

  // Calculate dimensions based on orientation
  const width = orientation === 'portrait' ? config.width : config.height
  const height = orientation === 'portrait' ? config.height : config.width

  const toggleOrientation = () => {
    setOrientation(prev => prev === 'portrait' ? 'landscape' : 'portrait')
  }

  return (
    <div style={{ background: '#0F0F1A', border: '1px solid rgba(255,255,255,.06)', borderRadius: 20, overflow: 'hidden' }}>
      {/* Header with Device Toggle */}
      <div style={{ background: '#0A0A14', padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#F5F5FA' }}>{title}</span>

          {/* Device Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {(Object.keys(DEVICE_CONFIGS) as DeviceType[]).map((deviceType) => {
              const DeviceIcon = DEVICE_CONFIGS[deviceType].icon
              const isActive = device === deviceType

              return (
                <button
                  key={deviceType}
                  onClick={() => {
                    setDevice(deviceType)
                    setOrientation('portrait')
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '8px 12px', borderRadius: 10, border: 0, cursor: 'pointer',
                    fontSize: 13, fontFamily: "'Geist', sans-serif", transition: 'all 180ms',
                    background: isActive ? 'rgba(79,61,255,.15)' : 'rgba(255,255,255,.04)',
                    color: isActive ? '#F5F5FA' : '#86869A',
                    boxShadow: isActive ? '0 0 12px rgba(79,61,255,.2), inset 0 1px 0 rgba(255,255,255,.04)' : 'none',
                  }}
                  title={DEVICE_CONFIGS[deviceType].name}
                >
                  <DeviceIcon size={14} />
                  <span className="hidden sm:inline">{DEVICE_CONFIGS[deviceType].name}</span>
                </button>
              )
            })}

            {/* Rotation Button */}
            {canRotate && (
              <button
                onClick={toggleOrientation}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', borderRadius: 10, border: 0, cursor: 'pointer', background: 'rgba(255,255,255,.04)', color: '#86869A', fontSize: 13, fontFamily: "'Geist', sans-serif", transition: 'all 180ms' }}
                title={`Rotate to ${orientation === 'portrait' ? 'landscape' : 'portrait'}`}
              >
                <RotateCw size={14} />
                <span className="hidden sm:inline">Rotate</span>
              </button>
            )}
          </div>

          {/* Device Info */}
          <span className="num" style={{ fontSize: 12, color: '#5A5A6E' }}>
            {width} × {height}px
          </span>
        </div>
      </div>

      {/* Preview Area */}
      <div
        style={{ position: 'relative', background: 'linear-gradient(135deg, #0A0A14, #0F0F1A)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'auto', minHeight: 500, maxHeight: '80vh' }}
      >
        {config.frame ? (
          <div
            style={{
              position: 'relative', background: '#000', borderRadius: 24, margin: 32, transition: 'all 300ms',
              width: width, height: height,
              transform: `scale(${config.scale})`, transformOrigin: 'center',
              boxShadow: '0 8px 40px rgba(0,0,0,.5)',
            }}
          >
            {device === 'mobile' && orientation === 'portrait' && (
              <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: '33%', height: 24, background: '#000', borderRadius: '0 0 16px 16px', zIndex: 10 }} />
            )}
            <div style={{ position: 'absolute', inset: 8, background: '#fff', borderRadius: 16, overflow: 'hidden' }}>
              <iframe
                srcDoc={htmlContent}
                style={{ width: width, height: height, border: 0, transform: 'scale(1)', transformOrigin: 'top left' }}
                title="Device Preview"
                sandbox="allow-same-origin allow-scripts allow-forms"
              />
            </div>
            {device === 'mobile' && orientation === 'portrait' && (
              <div style={{ position: 'absolute', bottom: 4, left: '50%', transform: 'translateX(-50%)', width: 48, height: 48, borderRadius: '50%', border: '2px solid #333' }} />
            )}
          </div>
        ) : (
          <div
            style={{ position: 'relative', background: '#fff', margin: 32, borderRadius: 12, overflow: 'hidden', width: '100%', maxWidth: 1400, height: 700, boxShadow: '0 8px 40px rgba(0,0,0,.5)', transition: 'all 300ms' }}
          >
            <iframe
              srcDoc={htmlContent}
              style={{ width: '100%', height: '100%', border: 0 }}
              title="Desktop Preview"
              sandbox="allow-same-origin allow-scripts allow-forms"
            />
          </div>
        )}
      </div>

      {/* Preview Controls Footer */}
      <div style={{ background: '#0A0A14', padding: '12px 20px', borderTop: '1px solid rgba(255,255,255,.04)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13 }}>
          <span style={{ color: '#86869A' }}>
            Viewing in <strong style={{ color: '#F5F5FA', textTransform: 'capitalize' }}>{device}</strong> mode
            {canRotate && ` (${orientation})`}
          </span>
          <span style={{ color: '#5A5A6E' }}>
            Scroll to see full website
          </span>
        </div>
      </div>
    </div>
  )
}
