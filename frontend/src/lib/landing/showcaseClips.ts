/**
 * Clips for the landing showcase wall — the masonry grid of merchant sites
 * further down the homepage.
 *
 * Each card is one restaurant's own hero video, the way it plays on their
 * site. Nothing else goes on the card: no feature caption, no numbers, just
 * the business name. A card plays a video when the clip below has a `src`;
 * when it does not, the card draws itself — gradient and food mark — so the
 * section looks finished whether or not the MP4s have been uploaded yet.
 *
 * TO ADD A VIDEO
 *   1. Drop the file in `frontend/public/showcase/` under the name already
 *      written in the `src` line below (see the README there for the size and
 *      encoding the wall expects — short, muted, ~480px wide).
 *   2. Add a `poster` JPG with the same name so the first frame shows while
 *      the video loads. `preload` is off, so without a poster the card sits on
 *      its gradient until playback starts.
 *
 * `live` marks a real merchant site and puts a LIVE tag on the card; every
 * other card is tagged CONTOH, because it is a design BinaApp can build rather
 * than a shop that is trading. Only Wak Hassan is live today.
 *
 * `href` is separate on purpose: a demo can be given a link to its preview
 * subdomain without that making it a real business.
 */

export type ShowcaseClip = {
  /** Stable key, and the file name the video/poster use. */
  id: string
  /** Business name — the only text on the card. */
  label: string
  /** Drawn large on the card when there is no video. */
  mark: string
  /** Gradient stops for the card behind the video (and instead of it). */
  from: string
  to: string
  /** Card shape. Mixed heights are what make the grid stagger. */
  ratio: 'tall' | 'portrait' | 'square'
  /** `/showcase/<file>.mp4` — the merchant's hero video. */
  src: string
  /** `/showcase/<file>.jpg` — first frame, shown while the video loads. */
  poster?: string
  /** True only for a real merchant's site. Tags the card LIVE instead of
   *  CONTOH — never set it on a demo build. */
  live?: boolean
  /** Where the card links, if anywhere. Empty means the card does not link. */
  href?: string
}

export const SHOWCASE_CLIPS: ShowcaseClip[] = [
  {
    id: 'nasi-kukus-wak-hassan',
    label: 'Nasi Kukus Wak Hassan',
    mark: '🍚',
    from: '#2A1FB8',
    to: '#0B0B15',
    ratio: 'tall',
    src: '/showcase/nasi-kukus-wak-hassan.mp4',
    poster: '/showcase/nasi-kukus-wak-hassan.jpg',
    live: true,
    href: 'https://mayam.binaapp.my',
  },
  {
    id: 'nasi-kandar-pak-din',
    label: 'Nasi Kandar Pak Din',
    mark: '🍛',
    from: '#E08800',
    to: '#161623',
    ratio: 'square',
    src: '/showcase/nasi-kandar-pak-din.mp4',
    poster: '/showcase/nasi-kandar-pak-din.jpg',
  },
  {
    id: 'roti-canai-abang-li',
    label: 'Roti Canai Abang Li',
    mark: '🫓',
    from: '#4F3DFF',
    to: '#05050C',
    ratio: 'portrait',
    src: '/showcase/roti-canai-abang-li.mp4',
    poster: '/showcase/roti-canai-abang-li.jpg',
  },
  {
    id: 'ckt-ah-seng',
    label: 'Char Kuey Teow Ah Seng',
    mark: '🍜',
    from: '#22C08F',
    to: '#05050C',
    ratio: 'tall',
    src: '/showcase/ckt-ah-seng.mp4',
    poster: '/showcase/ckt-ah-seng.jpg',
  },
  {
    id: 'satay-haji-ramli',
    label: 'Satay Kajang Haji Ramli',
    mark: '🍢',
    from: '#7FB500',
    to: '#120D55',
    ratio: 'square',
    src: '/showcase/satay-haji-ramli.mp4',
    poster: '/showcase/satay-haji-ramli.jpg',
  },
  {
    id: 'laksa-mak-timah',
    label: 'Laksa Penang Mak Timah',
    mark: '🍲',
    from: '#E03A3F',
    to: '#120D55',
    ratio: 'portrait',
    src: '/showcase/laksa-mak-timah.mp4',
    poster: '/showcase/laksa-mak-timah.jpg',
  },
  {
    id: 'nasi-lemak-kak-yah',
    label: 'Nasi Lemak Kak Yah',
    mark: '🥥',
    from: '#1C1580',
    to: '#05050C',
    ratio: 'tall',
    src: '/showcase/nasi-lemak-kak-yah.mp4',
    poster: '/showcase/nasi-lemak-kak-yah.jpg',
  },
  {
    id: 'burger-abang-burn',
    label: 'Burger Bakar Abang Burn',
    mark: '🍔',
    from: '#C7FF3D',
    to: '#1C1580',
    ratio: 'square',
    src: '/showcase/burger-abang-burn.mp4',
    poster: '/showcase/burger-abang-burn.jpg',
  },
  {
    id: 'kopitiam-lim',
    label: 'Kopitiam Lim',
    mark: '☕',
    from: '#3A3A4A',
    to: '#05050C',
    ratio: 'portrait',
    src: '/showcase/kopitiam-lim.mp4',
    poster: '/showcase/kopitiam-lim.jpg',
  },
  {
    id: 'cendol-tok-mat',
    label: 'Cendol Pulut Tok Mat',
    mark: '🍧',
    from: '#6B5CFF',
    to: '#05050C',
    ratio: 'square',
    src: '/showcase/cendol-tok-mat.mp4',
    poster: '/showcase/cendol-tok-mat.jpg',
  },
  {
    id: 'tandoori-raju',
    label: 'Tandoori Bistro Raju',
    mark: '🍗',
    from: '#FF5A5F',
    to: '#161623',
    ratio: 'tall',
    src: '/showcase/tandoori-raju.mp4',
    poster: '/showcase/tandoori-raju.jpg',
  },
  {
    id: 'sup-tulang-johor',
    label: 'Sup Tulang Merah Johor',
    mark: '🍖',
    from: '#E03A3F',
    to: '#05050C',
    ratio: 'portrait',
    src: '/showcase/sup-tulang-johor.mp4',
    poster: '/showcase/sup-tulang-johor.jpg',
  },
  {
    id: 'ayam-penyet-mbok-sri',
    label: 'Ayam Penyet Mbok Sri',
    mark: '🍗',
    from: '#3FB8FF',
    to: '#120D55',
    ratio: 'square',
    src: '/showcase/ayam-penyet-mbok-sri.mp4',
    poster: '/showcase/ayam-penyet-mbok-sri.jpg',
  },
  {
    id: 'dimsum-hong-kee',
    label: 'Dim Sum Hong Kee',
    mark: '🥟',
    from: '#8F80FF',
    to: '#0B0B15',
    ratio: 'tall',
    src: '/showcase/dimsum-hong-kee.mp4',
    poster: '/showcase/dimsum-hong-kee.jpg',
  },
  {
    id: 'al-mandi-house',
    label: 'Nasi Arab Al-Mandi House',
    mark: '🍚',
    from: '#A8E81C',
    to: '#161623',
    ratio: 'portrait',
    src: '/showcase/al-mandi-house.mp4',
    poster: '/showcase/al-mandi-house.jpg',
  },
  {
    id: 'sweet-crumbs',
    label: 'Sweet Crumbs Bakery',
    mark: '🧁',
    from: '#DDFF7A',
    to: '#2A1FB8',
    ratio: 'square',
    src: '/showcase/sweet-crumbs.mp4',
    poster: '/showcase/sweet-crumbs.jpg',
  },
]
