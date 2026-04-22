import Link from 'next/link'
import Image from 'next/image'

const linkGroups = [
  {
    title: 'Produk',
    links: [
      { label: 'Ciri-ciri', href: '#ciri' },
      { label: 'Harga', href: '#harga' },
    ],
  },
  {
    title: 'Undang-undang',
    links: [
      { label: 'Polisi Privasi', href: '/privacy-policy' },
      { label: 'Terma Perkhidmatan', href: '/terms-of-service' },
    ],
  },
  {
    title: 'Hubungi',
    links: [
      { label: 'support.team@binaapp.my', href: 'mailto:support.team@binaapp.my' },
    ],
  },
]

export default function LandingFooter() {
  return (
    <footer className="bg-ink-900 text-ink-400 border-t border-white/[.06] pt-16 pb-10 px-8">
      <div className="max-w-[1200px] mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">

        {/* Brand column */}
        <div>
          <div className="flex items-center gap-2.5 mb-4">
            <Image
              src="/brand/logo-mark.svg"
              alt="BinaApp"
              width={30}
              height={30}
              className="rounded-lg"
            />
            <span className="font-geist font-bold text-xl text-white tracking-tight">
              bina<span className="text-brand-300">app</span>
            </span>
          </div>
          <p className="font-geist text-sm leading-relaxed max-w-[340px]">
            Platform website AI untuk restoran Malaysia. Dibina di KL. Dibuat untuk mamak, cafe, bistro.
          </p>
        </div>

        {/* Link groups */}
        {linkGroups.map((group) => (
          <div key={group.title}>
            <div className="font-geist-mono text-[11px] tracking-[.12em] uppercase text-ink-500 mb-3.5">
              {group.title}
            </div>
            <ul className="flex flex-col gap-2.5">
              {group.links.map((link) => (
                <li key={link.label}>
                  {link.href.startsWith('/') ? (
                    <Link
                      href={link.href}
                      className="font-geist text-sm text-ink-300 hover:text-white transition-colors"
                    >
                      {link.label}
                    </Link>
                  ) : (
                    <a
                      href={link.href}
                      className="font-geist text-sm text-ink-300 hover:text-white transition-colors"
                    >
                      {link.label}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Bottom bar */}
      <div className="max-w-[1200px] mx-auto mt-12 pt-6 border-t border-white/[.06] flex flex-col sm:flex-row justify-between font-geist-mono text-[11px] text-ink-500 tracking-[.04em] gap-2">
        <span>© 2026 binaapp · dibina di KL</span>
        <span>support.team@binaapp.my</span>
      </div>
    </footer>
  )
}
