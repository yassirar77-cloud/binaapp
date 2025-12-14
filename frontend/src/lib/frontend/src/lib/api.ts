export async function apiFetch(
  url: string,
  options?: RequestInit
) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    throw new Error('API request failed')
  }

  return res.json()
}
