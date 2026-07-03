'use client';

import { useState } from 'react';
import { Check, Download, Smartphone } from 'lucide-react';

import IOSInstallGuide from './IOSInstallGuide';
import { usePWAInstall } from './usePWAInstall';

// Landing-page download card. Click-to-install only — no auto popup. Fires
// the native install dialog on Android/desktop Chrome, opens the Add to
// Home Screen guide on iOS, and falls back to a short hint on browsers
// with no install path (e.g. desktop Firefox).

interface DownloadAppCardProps {
  appName: string;
  tagline: string;
  iconSrc: string;
  className?: string;
}

export default function DownloadAppCard({
  appName,
  tagline,
  iconSrc,
  className = '',
}: DownloadAppCardProps) {
  const { canInstall, isIOS, isStandalone, isInstalled, promptInstall } =
    usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);
  const [busy, setBusy] = useState(false);

  // Already running as the installed app — the card is pointless.
  if (isStandalone) return null;

  const supported = canInstall || isIOS;

  const handleClick = async () => {
    if (busy) return;
    if (canInstall) {
      setBusy(true);
      try {
        await promptInstall();
      } finally {
        setBusy(false);
      }
    } else if (isIOS) {
      setShowIOSGuide(true);
    }
  };

  return (
    <section className={`bg-ink-900 px-8 py-16 ${className}`}>
      <div className="max-w-[720px] mx-auto rounded-3xl border border-white/[0.08] bg-white/[0.04] p-8 sm:p-10 text-center">
        <img
          src={iconSrc}
          alt={`${appName} icon`}
          className="mx-auto h-20 w-20 rounded-2xl shadow-lg shadow-black/40"
        />
        <h2 className="mt-5 text-2xl font-bold text-white">
          Download {appName}
        </h2>
        <p className="mt-2 text-ink-400">{tagline}</p>
        <p className="mt-1 text-xs text-ink-400/70">
          Percuma · Tiada App Store diperlukan · Terus dari browser
        </p>

        <div className="mt-6 flex justify-center">
          {isInstalled ? (
            <span className="inline-flex items-center gap-2 rounded-xl border border-[#C7FF3D]/30 bg-[#C7FF3D]/10 px-5 py-3 text-sm font-semibold text-[#C7FF3D]">
              <Check className="h-4 w-4" />
              App telah dipasang
            </span>
          ) : supported ? (
            <button
              type="button"
              onClick={handleClick}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/25 transition-colors disabled:opacity-60"
            >
              <Download className="h-4 w-4" />
              Download App
            </button>
          ) : (
            <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-5 py-3 text-sm text-ink-400">
              <Smartphone className="h-4 w-4" />
              Buka binaapp.my di Chrome (Android) atau Safari (iPhone) untuk
              install
            </span>
          )}
        </div>
      </div>

      {showIOSGuide && (
        <IOSInstallGuide appName={appName} onClose={() => setShowIOSGuide(false)} />
      )}
    </section>
  );
}
