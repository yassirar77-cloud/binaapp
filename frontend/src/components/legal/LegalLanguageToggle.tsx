'use client';

import React from 'react';
import Link from 'next/link';
import { Languages } from 'lucide-react';

type Props = {
  /** Current language displayed on this route. */
  current: 'bm' | 'en';
  /** Route for the BM version of this document. */
  bmHref: string;
  /** Route for the EN version of this document. */
  enHref: string;
  /** Optional accessible label override. */
  ariaLabel?: string;
};

/**
 * Pill-style toggle that switches between the BM and EN versions of the
 * current legal document.
 *
 * Hash preservation: the toggle reads `window.location.hash` and
 * appends it to the target href so that switching language from
 * /polisi-privasi#ai-features lands on /privacy-policy#ai-features.
 * The BM and EN files share section IDs so the same anchor exists
 * on both pages.
 *
 * Uses <Link> from next/link so navigation is client-side and the
 * scroll position survives the hash jump on the other route.
 */
export function LegalLanguageToggle({
  current,
  bmHref,
  enHref,
  ariaLabel = 'Switch language',
}: Props) {
  const [hash, setHash] = React.useState('');

  React.useEffect(() => {
    const sync = () => setHash(window.location.hash);
    sync();
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);

  const bmTarget = `${bmHref}${hash}`;
  const enTarget = `${enHref}${hash}`;

  return (
    <div
      className="inline-flex items-center rounded-full bg-ink-100 p-1 text-sm"
      role="group"
      aria-label={ariaLabel}
    >
      <Languages className="ml-2 mr-1 h-4 w-4 text-ink-400" aria-hidden="true" />
      <Link
        href={bmTarget}
        aria-current={current === 'bm' ? 'page' : undefined}
        className={
          current === 'bm'
            ? 'rounded-full bg-white px-3 py-1 font-semibold text-ink-900 shadow-soft transition'
            : 'rounded-full px-3 py-1 text-ink-600 hover:text-ink-900 transition'
        }
      >
        BM
      </Link>
      <Link
        href={enTarget}
        aria-current={current === 'en' ? 'page' : undefined}
        className={
          current === 'en'
            ? 'rounded-full bg-white px-3 py-1 font-semibold text-ink-900 shadow-soft transition'
            : 'rounded-full px-3 py-1 text-ink-600 hover:text-ink-900 transition'
        }
      >
        EN
      </Link>
    </div>
  );
}
