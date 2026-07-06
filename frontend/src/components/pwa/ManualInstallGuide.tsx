'use client';

import { Modal } from '@/components/ui/popups';

// Fallback guide for Android/desktop when no programmatic install prompt is
// available — e.g. Chrome hasn't fired `beforeinstallprompt` yet, or the
// browser (Firefox, Samsung Internet, in-app webviews) never fires it at all.
// Mirrors IOSInstallGuide so the install affordance is never a dead end.

interface ManualInstallGuideProps {
  appName: string;
  onClose: () => void;
}

const STEPS = [
  <>
    Tekan ikon menu{' '}
    <span className="font-semibold text-[#C7FF3D]">⋮</span> (atau{' '}
    <strong>⋯</strong>) di penjuru pelayar
  </>,
  <>
    Pilih <strong>&quot;Add to Home screen&quot;</strong> atau{' '}
    <strong>&quot;Install app&quot;</strong>
  </>,
  <>
    Tekan <strong>&quot;Add&quot;</strong> / <strong>&quot;Install&quot;</strong> — siap!
  </>,
];

export default function ManualInstallGuide({
  appName,
  onClose,
}: ManualInstallGuideProps) {
  return (
    <Modal
      open
      onClose={onClose}
      title={`Install ${appName}`}
      description="Untuk Android (Chrome) atau desktop:"
      footer={
        <button
          type="button"
          onClick={onClose}
          className="w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-sm font-medium text-white transition-colors sm:w-auto sm:px-6"
        >
          Faham
        </button>
      }
    >
      <ol className="space-y-3">
        {STEPS.map((step, i) => (
          <li key={i} className="flex items-center gap-3 text-sm text-white/80">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-xs font-semibold text-white">
              {i + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-xs text-white/50">
        Di komputer, cari ikon pasang (⊕) di hujung bar alamat pelayar.
      </p>
    </Modal>
  );
}
