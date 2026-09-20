/**
 * Clips for the landing showcase wall — the moving grid of website demos
 * further down the homepage.
 *
 * The wall is a set of columns that drift slowly in alternating directions,
 * each one filled with cards of uneven height so the grid staggers instead of
 * marching in rows. A card plays a video when the clip below has a `src`; when
 * it does not, the card draws itself — gradient, food mark, caption — so the
 * section looks finished whether or not the MP4s have been uploaded yet.
 *
 * TO ADD A VIDEO
 *   1. Drop the file in `frontend/public/showcase/` (see the README there for
 *      the size and encoding the wall expects — short, muted, ~480px wide).
 *   2. Uncomment the `src` line on the matching clip below, or point it at
 *      whatever you named the file.
 *   3. Optionally add a `poster` JPG with the same name so the first frame
 *      shows while the video is still loading.
 *
 * Each clip is one restaurant's site: the screen recording of the site
 * scrolling, an order coming in over WhatsApp, the rider map moving. Clips are
 * dealt into columns in order, so keeping the list varied keeps each column
 * varied. Any number works; 10-20 fills the wall nicely.
 */

export type ShowcaseClip = {
  /** Stable key, and the file name the video/poster are expected to use. */
  id: string
  /** Business name, shown large on the card. */
  label: string
  /** The BinaApp feature this card is showing off. */
  kind: string
  /** Drawn large on the card when there is no video. */
  mark: string
  /** Gradient stops for the card behind the video (and instead of it). */
  from: string
  to: string
  /** Card shape. Mixed heights are what make the grid stagger. */
  ratio: 'tall' | 'portrait' | 'square'
  /** `/showcase/<file>.mp4` once the clip has been uploaded. */
  src?: string
  /** `/showcase/<file>.jpg` — first frame, shown while the video loads. */
  poster?: string
}

export const SHOWCASE_CLIPS: ShowcaseClip[] = [
  {
    id: 'nasi-lemak',
    label: 'Nasi Lemak Kak Yah',
    kind: 'Website siap 60 saat',
    mark: '🍚',
    from: '#2A1FB8',
    to: '#0B0B15',
    ratio: 'tall',
    // src: '/showcase/nasi-lemak.mp4',
  },
  {
    id: 'mamak',
    label: 'Mamak Corner 24J',
    kind: 'Order WhatsApp auto',
    mark: '🫖',
    from: '#7FB500',
    to: '#120D55',
    ratio: 'square',
    // src: '/showcase/mamak.mp4',
  },
  {
    id: 'satay',
    label: 'Satay Station Kajang',
    kind: 'QR menu atas meja',
    mark: '🍢',
    from: '#E08800',
    to: '#161623',
    ratio: 'portrait',
    // src: '/showcase/satay.mp4',
  },
  {
    id: 'roti-canai',
    label: 'Roti Canai Express',
    kind: 'Bayar ToyyibPay',
    mark: '🫓',
    from: '#4F3DFF',
    to: '#05050C',
    ratio: 'square',
    // src: '/showcase/roti-canai.mp4',
  },
  {
    id: 'tomyam',
    label: 'Tomyam Seafood Bagan',
    kind: 'Jejak penghantar live',
    mark: '🦐',
    from: '#E03A3F',
    to: '#120D55',
    ratio: 'tall',
    // src: '/showcase/tomyam.mp4',
  },
  {
    id: 'bubble-tea',
    label: 'Bubble Tea Lab',
    kind: 'Pre-order & pickup',
    mark: '🧋',
    from: '#8F80FF',
    to: '#0B0B15',
    ratio: 'portrait',
    // src: '/showcase/bubble-tea.mp4',
  },
  {
    id: 'burger-bakar',
    label: 'Burger Bakar Malam',
    kind: 'Delivery sendiri',
    mark: '🍔',
    from: '#C7FF3D',
    to: '#1C1580',
    ratio: 'square',
    // src: '/showcase/burger-bakar.mp4',
  },
  {
    id: 'kuey-teow',
    label: 'Char Kuey Teow Ah Hock',
    kind: 'Menu dalam BM',
    mark: '🍜',
    from: '#22C08F',
    to: '#05050C',
    ratio: 'tall',
    // src: '/showcase/kuey-teow.mp4',
  },
  {
    id: 'kuih',
    label: 'Kuih Muih Pagi',
    kind: 'Tempahan awal pagi',
    mark: '🧁',
    from: '#DDFF7A',
    to: '#2A1FB8',
    ratio: 'portrait',
    // src: '/showcase/kuih.mp4',
  },
  {
    id: 'ayam-penyet',
    label: 'Ayam Penyet Joyah',
    kind: 'Sifar komisen',
    mark: '🍗',
    from: '#3FB8FF',
    to: '#120D55',
    ratio: 'square',
    // src: '/showcase/ayam-penyet.mp4',
  },
  {
    id: 'cendol',
    label: 'Cendol & ABC Pak Mat',
    kind: 'Promo musim panas',
    mark: '🍧',
    from: '#6B5CFF',
    to: '#05050C',
    ratio: 'tall',
    // src: '/showcase/cendol.mp4',
  },
  {
    id: 'katering',
    label: 'Katering Kenduri Suria',
    kind: 'Tempahan pukal',
    mark: '🍛',
    from: '#A8E81C',
    to: '#161623',
    ratio: 'portrait',
    // src: '/showcase/katering.mp4',
  },
  {
    id: 'kopitiam',
    label: 'Kopitiam Ah Seng',
    kind: 'Menu digital',
    mark: '☕',
    from: '#3A3A4A',
    to: '#05050C',
    ratio: 'square',
    // src: '/showcase/kopitiam.mp4',
  },
  {
    id: 'pizza-kampung',
    label: 'Pizza Kampung',
    kind: 'Kod promo QR',
    mark: '🍕',
    from: '#FF5A5F',
    to: '#1C1580',
    ratio: 'tall',
    // src: '/showcase/pizza-kampung.mp4',
  },
  {
    id: 'nasi-kandar',
    label: 'Nasi Kandar Pulau',
    kind: 'Kutipan harian',
    mark: '🍛',
    from: '#0F9D6B',
    to: '#0B0B15',
    ratio: 'portrait',
    // src: '/showcase/nasi-kandar.mp4',
  },
  {
    id: 'western-kampung',
    label: 'Western Kampung Pak Su',
    kind: 'Jualan naik 3x',
    mark: '🍳',
    from: '#1C1580',
    to: '#05050C',
    ratio: 'square',
    // src: '/showcase/western-kampung.mp4',
  },
]

/**
 * Deals the clips into `count` columns, one after another, so no clip lands in
 * two columns at once and neighbouring cards are never the same dish.
 *
 * A short list would leave columns with one or two cards, which loops visibly.
 * Those columns wrap back around the list until they have enough to stay
 * taller than the section they scroll through; columns are allowed to end up
 * different lengths, since each one animates against its own height.
 */
export function dealClipsIntoColumns(clips: ShowcaseClip[], count: number): ShowcaseClip[][] {
  if (clips.length === 0) return Array.from({ length: count }, () => [])

  const MIN_PER_COLUMN = 3

  return Array.from({ length: count }, (_, column) => {
    const dealt = clips.filter((_, index) => index % count === column)

    let index = column
    while (dealt.length < MIN_PER_COLUMN) {
      index = (index + count) % clips.length
      dealt.push(clips[index])
    }

    return dealt
  })
}
