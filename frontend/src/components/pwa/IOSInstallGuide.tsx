'use client';

import { Modal } from '@/components/ui/popups';

// Bottom-sheet guide for iOS Safari, where no programmatic install prompt
// exists — the user must use Share → Add to Home Screen manually.

interface IOSInstallGuideProps {
  appName: string;
  onClose: () => void;
}

const STEPS = [
  <>
    Tekan ikon <span className="font-semibold text-sky-400">Share</span>
    <svg
      className="inline w-4 h-4 ml-1 -mt-0.5 text-sky-400"
      fill="currentColor"
      viewBox="0 0 20 20"
      aria-hidden="true"
    >
      <path d="M10 3a1 1 0 011 1v4.586l1.707-1.707a1 1 0 111.414 1.414l-3.536 3.536a1 1 0 01-1.414 0L5.636 8.293a1 1 0 111.414-1.414L9 8.586V4a1 1 0 011-1z" />
      <path d="M3 12a1 1 0 011 1v2a2 2 0 002 2h8a2 2 0 002-2v-2a1 1 0 112 0v2a4 4 0 01-4 4H6a4 4 0 01-4-4v-2a1 1 0 011-1z" />
    </svg>{' '}
    di bar Safari
  </>,
  <>
    Pilih <strong>&quot;Add to Home Screen&quot;</strong>
  </>,
  <>
    Tekan <strong>&quot;Add&quot;</strong> — siap!
  </>,
];

export default function IOSInstallGuide({ appName, onClose }: IOSInstallGuideProps) {
  return (
    <Modal
      open
      onClose={onClose}
      title={`Install ${appName}`}
      description="Untuk iPhone/iPad (Safari):"
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
    </Modal>
  );
}
