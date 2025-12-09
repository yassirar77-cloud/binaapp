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
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header with Device Toggle */}
      <div className="bg-gray-800 text-white px-4 py-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <span className="font-semibold">{title}</span>

          {/* Device Selector */}
          <div className="flex items-center gap-2">
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
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                  title={DEVICE_CONFIGS[deviceType].name}
                >
                  <DeviceIcon className="w-4 h-4" />
                  <span className="hidden sm:inline text-sm">
                    {DEVICE_CONFIGS[deviceType].name}
                  </span>
                </button>
              )
            })}

            {/* Rotation Button */}
            {canRotate && (
              <button
                onClick={toggleOrientation}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
                title={`Rotate to ${orientation === 'portrait' ? 'landscape' : 'portrait'}`}
              >
                <RotateCw className="w-4 h-4" />
                <span className="hidden sm:inline text-sm">Rotate</span>
              </button>
            )}
          </div>

          {/* Device Info */}
          <div className="text-sm text-gray-400">
            {width} × {height}px
          </div>
        </div>
      </div>

      {/* Preview Area */}
      <div
        className="relative bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center overflow-auto"
        style={{ minHeight: '500px', maxHeight: '80vh' }}
      >
        {config.frame ? (
          /* Device Frame (Mobile/Tablet) */
          <div
            className="relative bg-black rounded-3xl shadow-2xl m-8 transition-all duration-300"
            style={{
              width: `${width}px`,
              height: `${height}px`,
              transform: `scale(${config.scale})`,
              transformOrigin: 'center'
            }}
          >
            {/* Device Notch (for mobile) */}
            {device === 'mobile' && orientation === 'portrait' && (
              <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-1/3 h-6 bg-black rounded-b-2xl z-10"></div>
            )}

            {/* Screen */}
            <div className="absolute inset-2 bg-white rounded-2xl overflow-hidden">
              <iframe
                srcDoc={htmlContent}
                className="w-full h-full border-0"
                title="Device Preview"
                sandbox="allow-same-origin allow-scripts allow-forms"
                style={{
                  width: `${width}px`,
                  height: `${height}px`,
                  transform: 'scale(1)',
                  transformOrigin: 'top left'
                }}
              />
            </div>

            {/* Home Button (mobile) */}
            {device === 'mobile' && orientation === 'portrait' && (
              <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-12 h-12 rounded-full border-2 border-gray-800"></div>
            )}
          </div>
        ) : (
          /* Desktop Preview (no frame) */
          <div
            className="relative bg-white shadow-2xl m-8 rounded-lg overflow-hidden transition-all duration-300"
            style={{
              width: '100%',
              maxWidth: '1400px',
              height: '700px'
            }}
          >
            <iframe
              srcDoc={htmlContent}
              className="w-full h-full border-0"
              title="Desktop Preview"
              sandbox="allow-same-origin allow-scripts allow-forms"
            />
          </div>
        )}
      </div>

      {/* Preview Controls Footer */}
      <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Viewing in <strong className="text-gray-900 capitalize">{device}</strong> mode
            {canRotate && ` (${orientation})`}
          </span>
          <span className="text-gray-500">
            Scroll to see full website
          </span>
        </div>
      </div>
    </div>
  )
}
