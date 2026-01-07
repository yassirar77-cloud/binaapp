const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  'https://binaapp-backend.onrender.com'

export async function apiFetch(
  path: string,
  options?: RequestInit & { timeout?: number }
) {
  // Default timeout: 2 minutes for mobile compatibility
  const timeout = options?.timeout || 120000
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const extraHeaders = (options?.headers || {}) as Record<string, string>
    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...extraHeaders,
      },
      ...{ ...options, headers: undefined },
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'API request failed')
    }

    return res.json()
  } catch (error: any) {
    clearTimeout(timeoutId)

    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please check your connection and try again.')
    }

    throw error
  }
}
