'use client';

import { useState } from 'react';
import { Check, Download } from 'lucide-react';

import IOSInstallGuide from './IOSInstallGuide';
import { usePWAInstall } from './usePWAInstall';

// Compact click-to-install button. Never auto-shows anything: it fires the
// native install dialog (Android/desktop Chrome) or opens the Add to Home
// Screen guide (iOS) only when clicked. Renders nothing when the app is
// already running standalone or when no install path exists.

interface InstallAppButtonProps {
  appName: string;
  /** Icon-only rendering for tight headers/top bars. */
  compact?: boolean;
  className?: string;
}

export default function InstallAppButton({
  appName,
  compact = false,
  className = '',
}: InstallAppButtonProps) {
  const { canInstall, isIOS, isStandalone, isInstalled, promptInstall } =
    usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);
  const [busy, setBusy] = useState(false);

  // Already running as the installed app — nothing to offer.
  if (isStandalone) return null;

  // Installed during this session — show the installed state.
  if (isInstalled) {
    if (compact) return null;
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border border-[#C7FF3D]/30 bg-[#C7FF3D]/10 px-3 py-1.5 text-xs font-medium text-[#C7FF3D] ${className}`}
      >
        <Check className="h-3.5 w-3.5" />
        App dipasang
      </span>
    );
  }

  // No held prompt and not iOS (unsupported browser, or Chrome hasn't
  // offered installability yet) — render nothing rather than a dead button.
  if (!canInstall && !isIOS) return null;

  const handleClick = async () => {
    if (busy) return;
    // Prefer the native dialog when a deferred prompt is held (covers
    // Chrome on iPadOS-like UAs too); fall back to the iOS guide.
    if (canInstall) {
      setBusy(true);
      try {
        await promptInstall();
      } finally {
        setBusy(false);
      }
    } else {
      setShowIOSGuide(true);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={busy}
        title={`Download ${appName}`}
        aria-label={`Download ${appName}`}
        className={
          compact
            ? `flex h-9 w-9 items-center justify-center rounded-full text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-50 ${className}`
            : `inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.06] px-3 py-1.5 text-xs font-medium text-white/80 hover:bg-white/[0.12] hover:text-white transition-colors disabled:opacity-50 ${className}`
        }
      >
        <Download className={compact ? 'h-[18px] w-[18px]' : 'h-3.5 w-3.5'} />
        {!compact && <span className="whitespace-nowrap">Download App</span>}
      </button>

      {showIOSGuide && (
        <IOSInstallGuide appName={appName} onClose={() => setShowIOSGuide(false)} />
      )}
    </>
  );
}
