const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  'https://binaapp-backend.onrender.com'

export async function apiFetch(
  path: string,
  options?: RequestInit
) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: options?.method || 'GET',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
    body: options?.body,
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'API request failed')
  }

  return res.json()
}