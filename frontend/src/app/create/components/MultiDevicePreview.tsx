/**
 * Multi-Device Preview Component
 * Side-by-side comparison of Mobile, Tablet, and Desktop views
 */

'use client'

import { Monitor, Tablet, Smartphone } from 'lucide-react'

interface MultiDevicePreviewProps {
  htmlContent: string
  title?: string
}

export default function MultiDevicePreview({ htmlContent, title = "Multi-Device Preview" }: MultiDevicePreviewProps) {
  const devices = [
    {
      name: 'Mobile',
      icon: Smartphone,
      width: 375,
      height: 667,
      scale: 0.35
    },
    {
      name: 'Tablet',
      icon: Tablet,
      width: 768,
      height: 1024,
      scale: 0.28
    },
    {
      name: 'Desktop',
      icon: Monitor,
      width: 1920,
      height: 1080,
      scale: 0.2
    }
  ]

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 text-white px-4 py-3">
        <h3 className="font-semibold">{title}</h3>
      </div>

      {/* Multi-Device Grid */}
      <div className="bg-gradient-to-br from-gray-100 to-gray-200 p-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {devices.map((device) => {
            const DeviceIcon = device.icon

            return (
              <div key={device.name} className="flex flex-col items-center">
                {/* Device Label */}
                <div className="flex items-center gap-2 mb-4">
                  <DeviceIcon className="w-5 h-5 text-gray-600" />
                  <span className="font-semibold text-gray-900">{device.name}</span>
                  <span className="text-sm text-gray-500">
                    {device.width}×{device.height}
                  </span>
                </div>

                {/* Device Frame */}
                <div
                  className="relative bg-black rounded-3xl shadow-2xl transition-transform hover:scale-105"
                  style={{
                    width: `${device.width}px`,
                    height: `${device.height}px`,
                    transform: `scale(${device.scale})`,
                    transformOrigin: 'top center'
                  }}
                >
                  {/* Notch for mobile */}
                  {device.name === 'Mobile' && (
                    <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-1/3 h-6 bg-black rounded-b-2xl z-10"></div>
                  )}

                  {/* Screen */}
                  <div className="absolute inset-2 bg-white rounded-2xl overflow-hidden">
                    <iframe
                      srcDoc={htmlContent}
                      className="w-full h-full border-0"
                      title={`${device.name} Preview`}
                      sandbox="allow-same-origin"
                      style={{
                        width: `${device.width}px`,
                        height: `${device.height}px`,
                        pointerEvents: 'none'
                      }}
                    />
                  </div>

                  {/* Home Button for mobile */}
                  {device.name === 'Mobile' && (
                    <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-12 h-12 rounded-full border-2 border-gray-800"></div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 text-center text-sm text-gray-600">
        Viewing across all devices - Perfect for testing responsive design
      </div>
    </div>
  )
}
