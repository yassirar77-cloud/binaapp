'use client';

// NotificationPermissionPrompt — first-login modal asking the rider to
// allow web-push notifications. The actual push pipeline is a followup
// PR; for now we just call Notification.requestPermission() and stash
// the user's decision in localStorage so we don't re-prompt.

import { useState } from 'react';
import { Bell, Loader2 } from 'lucide-react';

interface NotificationPermissionPromptProps {
  onResolve: (granted: boolean) => void;
}

export default function NotificationPermissionPrompt({
  onResolve,
}: NotificationPermissionPromptProps) {
  const [busy, setBusy] = useState(false);

  const allow = async () => {
    setBusy(true);
    try {
      if (typeof Notification === 'undefined') {
        onResolve(false);
        return;
      }
      const result = await Notification.requestPermission();
      onResolve(result === 'granted');
    } catch {
      onResolve(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center rider-fade-in"
    >
      <button
        type="button"
        aria-label="Tutup"
        onClick={busy ? undefined : () => onResolve(false)}
        className="absolute inset-0 bg-black/65 backdrop-blur-sm"
      />
      <div className="relative w-full sm:max-w-sm sm:mx-4 bg-[var(--rider-surface)] rounded-t-3xl sm:rounded-3xl border border-[var(--rider-border)] p-5 rider-modal-in">
        <div className="flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-2xl bg-[rgba(199,255,61,0.10)] border border-[rgba(199,255,61,0.30)] flex items-center justify-center mb-3">
            <Bell
              className="w-7 h-7 text-[var(--rider-lime)]"
              strokeWidth={2.25}
            />
          </div>
          <h2 className="text-[18px] font-semibold text-white">
            Benarkan notifikasi?
          </h2>
          <p className="mt-1.5 text-[13px] text-[var(--rider-text-2)]">
            Dapat tahu pesanan baru walaupun aplikasi tertutup.
          </p>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => onResolve(false)}
            disabled={busy}
            className="h-12 rounded-2xl bg-[var(--rider-surface-2)] border border-[var(--rider-border)] text-[var(--rider-text-2)] text-[14px] font-medium hover:text-white disabled:opacity-60"
          >
            Tidak sekarang
          </button>
          <button
            type="button"
            onClick={allow}
            disabled={busy}
            className="h-12 rounded-2xl bg-[var(--rider-lime)] hover:bg-[var(--rider-lime-2)] text-black text-[14px] font-semibold flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
            Benarkan
          </button>
        </div>
      </div>
    </div>
  );
}
