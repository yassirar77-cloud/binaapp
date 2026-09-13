/**
 * Which Malaysian locality a piece of merchant text names — the client-side
 * twin of backend business_identity.localities_in, kept small on purpose.
 *
 * Used to warn before Generate when the shop's story and its address name
 * different places. Not a geocoder: it answers "do these two texts share a
 * town?", nothing more.
 */

const LOCALITY_TOKENS = new Set([
  'alam', 'damansara', 'bangi', 'kajang', 'klang', 'puchong', 'subang',
  'petaling', 'ampang', 'cheras', 'gombak', 'rawang', 'sepang', 'nilai',
  'seremban', 'cyberjaya', 'putrajaya', 'serdang', 'semenyih', 'banting',
  'selayang', 'sentul', 'kepong', 'setapak', 'wangsa', 'bangsar',
  'brickfields', 'bukit', 'ipoh', 'taiping', 'melaka', 'malacca', 'muar',
  'batu', 'johor', 'bahru', 'kluang', 'kuantan', 'kemaman', 'terengganu',
  'kelantan', 'bharu', 'kedah', 'alor', 'setar', 'sungai', 'penang',
  'pinang', 'georgetown', 'butterworth', 'kangar', 'kuching', 'kinabalu',
  'sandakan', 'tawau', 'miri', 'sibu', 'labuan', 'kl', 'lumpur', 'kuala',
])

/** Count only with the word that follows: "Kota Damansara" → damansara. */
const QUALIFIERS = new Set(['bukit', 'kuala', 'sungai', 'batu', 'alor', 'kota', 'bandar', 'taman'])
/** Qualifiers that name a place with ANY following word ("Kota Damansara"). */
const OPEN_QUALIFIERS = new Set(['kota', 'bandar', 'taman'])

export function localitiesIn(text: string): Set<string> {
  const tokens = (text || '').match(/[A-Za-z]+/g)?.map((t) => t.toLowerCase()) ?? []
  const found = new Set<string>()
  tokens.forEach((tok, i) => {
    if (LOCALITY_TOKENS.has(tok) && !QUALIFIERS.has(tok)) {
      found.add(tok)
    } else if (QUALIFIERS.has(tok) && i + 1 < tokens.length) {
      const next = tokens[i + 1]
      if (LOCALITY_TOKENS.has(next) || (OPEN_QUALIFIERS.has(tok) && next.length > 3)) found.add(next)
    }
  })
  return found
}

export interface LocalityConflict {
  story: string
  address: string
}

/**
 * The first locality each side names when they share none; null otherwise.
 * Display strings are capitalised tokens — enough to point at the mismatch.
 */
export function localityConflict(description: string, address: string): LocalityConflict | null {
  const story = localitiesIn(description)
  const addr = localitiesIn(address)
  if (story.size === 0 || addr.size === 0) return null
  for (const t of story) if (addr.has(t)) return null
  const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)
  return { story: cap([...story][0]), address: cap([...addr][0]) }
}
