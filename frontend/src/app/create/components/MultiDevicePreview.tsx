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
    <div style={{ background: '#0F0F1A', border: '1px solid rgba(255,255,255,.06)', borderRadius: 20, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ background: '#0A0A14', padding: '12px 20px' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#F5F5FA', margin: 0 }}>{title}</h3>
      </div>

      {/* Multi-Device Grid */}
      <div style={{ background: 'linear-gradient(135deg, #0A0A14, #0F0F1A)', padding: 32 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 32 }}>
          {devices.map((device) => {
            const DeviceIcon = device.icon

            return (
              <div key={device.name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                {/* Device Label */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                  <DeviceIcon size={16} style={{ color: '#86869A' }} />
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#F5F5FA' }}>{device.name}</span>
                  <span className="num" style={{ fontSize: 11, color: '#5A5A6E' }}>
                    {device.width}×{device.height}
                  </span>
                </div>

                {/* Device Frame */}
                <div
                  style={{
                    position: 'relative', background: '#000', borderRadius: 24,
                    width: device.width, height: device.height,
                    transform: `scale(${device.scale})`, transformOrigin: 'top center',
                    boxShadow: '0 8px 40px rgba(0,0,0,.5)',
                    transition: 'transform 200ms',
                  }}
                >
                  {device.name === 'Mobile' && (
                    <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: '33%', height: 24, background: '#000', borderRadius: '0 0 16px 16px', zIndex: 10 }} />
                  )}
                  <div style={{ position: 'absolute', inset: 8, background: '#fff', borderRadius: 16, overflow: 'hidden' }}>
                    <iframe
                      srcDoc={htmlContent}
                      style={{ width: device.width, height: device.height, border: 0, pointerEvents: 'none' }}
                      title={`${device.name} Preview`}
                      sandbox="allow-same-origin"
                    />
                  </div>
                  {device.name === 'Mobile' && (
                    <div style={{ position: 'absolute', bottom: 4, left: '50%', transform: 'translateX(-50%)', width: 48, height: 48, borderRadius: '50%', border: '2px solid #333' }} />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Footer */}
      <div style={{ background: '#0A0A14', padding: '12px 20px', borderTop: '1px solid rgba(255,255,255,.04)', textAlign: 'center' }}>
        <span style={{ fontSize: 13, color: '#5A5A6E' }}>Viewing across all devices - Perfect for testing responsive design</span>
      </div>
    </div>
  )
}
