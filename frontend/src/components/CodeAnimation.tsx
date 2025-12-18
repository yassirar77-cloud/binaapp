'use client'

import { useState, useEffect } from 'react'

const codeLines = [
  '<!DOCTYPE html>',
  '<html lang="en">',
  '  <head>',
  '    <meta charset="UTF-8">',
  '    <title>Your Website</title>',
  '    <script src="tailwindcss"></script>',
  '  </head>',
  '  <body class="bg-gradient-to-r">',
  '    <header class="sticky top-0">',
  '      <nav class="flex justify-between">',
  '        <Logo />',
  '        <Menu items={navigation} />',
  '      </nav>',
  '    </header>',
  '    <section class="hero min-h-screen">',
  '      <h1 class="text-6xl font-bold">',
  '        Welcome to {businessName}',
  '      </h1>',
  '      <button class="cta-button">',
  '        Get Started',
  '      </button>',
  '    </section>',
  '    <section class="services grid-cols-3">',
  '      {services.map(service => (',
  '        <ServiceCard key={service.id} />',
  '      ))}',
  '    </section>',
  '    <footer class="bg-gray-900">',
  '      <ContactInfo />',
  '      <SocialLinks />',
  '    </footer>',
  '  </body>',
  '</html>',
]

export default function CodeAnimation() {
  const [displayedLines, setDisplayedLines] = useState<string[]>([])
  const [currentLine, setCurrentLine] = useState(0)
  const [currentChar, setCurrentChar] = useState(0)

  useEffect(() => {
    if (currentLine >= codeLines.length) {
      // Reset and loop
      const timeout = setTimeout(() => {
        setDisplayedLines([])
        setCurrentLine(0)
        setCurrentChar(0)
      }, 1000)
      return () => clearTimeout(timeout)
    }

    const line = codeLines[currentLine]

    if (currentChar < line.length) {
      const timeout = setTimeout(() => {
        setDisplayedLines(prev => {
          const newLines = [...prev]
          if (newLines.length <= currentLine) {
            newLines.push('')
          }
          newLines[currentLine] = line.substring(0, currentChar + 1)
          return newLines
        })
        setCurrentChar(prev => prev + 1)
      }, 20) // Typing speed
      return () => clearTimeout(timeout)
    } else {
      const timeout = setTimeout(() => {
        setCurrentLine(prev => prev + 1)
        setCurrentChar(0)
      }, 100)
      return () => clearTimeout(timeout)
    }
  }, [currentLine, currentChar])

  const getLineColor = (line: string) => {
    if (line.includes('<!') || line.includes('</')) return 'text-gray-500'
    if (line.includes('<') && line.includes('>')) return 'text-pink-400'
    if (line.includes('class=')) return 'text-green-400'
    if (line.includes('{') || line.includes('}')) return 'text-yellow-400'
    if (line.includes('//')) return 'text-gray-500'
    return 'text-blue-400'
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm h-64 overflow-hidden border border-gray-700">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-700">
        <div className="w-3 h-3 rounded-full bg-red-500"></div>
        <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
        <div className="w-3 h-3 rounded-full bg-green-500"></div>
        <span className="text-gray-500 text-xs ml-2">generating-website.html</span>
      </div>
      <div className="space-y-1">
        {displayedLines.map((line, index) => (
          <div key={index} className="flex">
            <span className="text-gray-600 w-6 text-right mr-3 select-none">
              {index + 1}
            </span>
            <span className={getLineColor(line)}>
              {line}
              {index === displayedLines.length - 1 && (
                <span className="animate-pulse bg-white w-2 h-4 inline-block ml-0.5"></span>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
