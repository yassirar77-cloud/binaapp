import Link from 'next/link'
import Image from 'next/image'

export default function AuthLogo() {
  return (
    <Link href="/" className="inline-flex items-center gap-2.5">
      <Image
        src="/brand/logo-mark.svg"
        alt="BinaApp"
        width={30}
        height={30}
        className="rounded-lg"
      />
      <span className="font-geist font-bold text-lg text-white tracking-tight">
        bina<span className="text-brand-300">app</span>
      </span>
    </Link>
  )
}
