/**
 * ThemeProvider — injects CSS custom properties from ThemeTokens.
 *
 * Wraps the entire website preview. All section components reference
 * these variables via var(--color-primary), var(--font-heading), etc.
 *
 * Also exports themeToCSS() for the static HTML renderer (backend).
 */

import React from 'react'
import type { ThemeTokens } from '@/types/recipe'

interface ThemeProviderProps {
  theme: ThemeTokens
  children: React.ReactNode
}

/**
 * Convert ThemeTokens to a CSS custom property block.
 * Used both by the React component and the backend HTML renderer.
 */
export function themeToCSS(theme: ThemeTokens): string {
  return `
:root {
  /* Colors */
  --color-primary: ${theme.colors.primary};
  --color-primary-hover: ${theme.colors.primary_hover};
  --color-secondary: ${theme.colors.secondary};
  --color-accent: ${theme.colors.accent};
  --color-background: ${theme.colors.background};
  --color-surface: ${theme.colors.surface};
  --color-text: ${theme.colors.text};
  --color-text-muted: ${theme.colors.text_muted};
  --color-border: ${theme.colors.border};
  --color-gradient-from: ${theme.colors.gradient_from};
  --color-gradient-to: ${theme.colors.gradient_to};

  /* Fonts */
  --font-heading: '${theme.fonts.heading}', serif;
  --font-body: '${theme.fonts.body}', sans-serif;

  /* Tokens */
  --radius-sm: ${theme.tokens.border_radius_sm};
  --radius-md: ${theme.tokens.border_radius_md};
  --radius-lg: ${theme.tokens.border_radius_lg};
  --shadow: ${theme.tokens.shadow};
  --shadow-lg: ${theme.tokens.shadow_lg};
  --spacing-section: ${theme.tokens.spacing_section};
  --max-width: ${theme.tokens.max_width};
}

html { scroll-behavior: smooth; }
body {
  background-color: var(--color-background);
  color: var(--color-text);
  font-family: var(--font-body);
}
h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-heading);
}
`.trim()
}

export default function ThemeProvider({ theme, children }: ThemeProviderProps) {
  const cssText = themeToCSS(theme)

  return (
    <div
      style={{
        backgroundColor: theme.colors.background,
        color: theme.colors.text,
        fontFamily: `'${theme.fonts.body}', sans-serif`,
      }}
    >
      <style dangerouslySetInnerHTML={{ __html: cssText }} />
      {children}
    </div>
  )
}
