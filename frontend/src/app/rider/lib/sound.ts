// /rider — new-order alert sound.
//
// No audio asset: a short two-tone beep is synthesised via Web Audio. To
// satisfy browser autoplay policy the AudioContext is created lazily on the
// first user interaction (primeAudioOnInteraction, wired by RiderApp on
// mount); alerts before that first tap fall back to vibration only.

let audioCtx: AudioContext | null = null;
let primed = false;

type AudioContextCtor = typeof AudioContext;

function getAudioContextCtor(): AudioContextCtor | null {
  if (typeof window === 'undefined') return null;
  return (
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: AudioContextCtor })
      .webkitAudioContext ||
    null
  );
}

function ensureAudioContext(): AudioContext | null {
  const Ctor = getAudioContextCtor();
  if (!Ctor) return null;
  if (!audioCtx) {
    try {
      audioCtx = new Ctor();
    } catch {
      return null;
    }
  }
  return audioCtx;
}

/** Install a one-time listener that creates/resumes the AudioContext on the
 *  first pointer/key interaction (autoplay policy). Safe to call more than
 *  once. */
export function primeAudioOnInteraction(): void {
  if (primed || typeof window === 'undefined') return;
  primed = true;
  const unlock = () => {
    const ctx = ensureAudioContext();
    if (ctx && ctx.state === 'suspended') {
      void ctx.resume().catch(() => {});
    }
    window.removeEventListener('pointerdown', unlock);
    window.removeEventListener('keydown', unlock);
  };
  window.addEventListener('pointerdown', unlock, { once: true });
  window.addEventListener('keydown', unlock, { once: true });
}

function beep(ctx: AudioContext, freq: number, at: number, dur: number): void {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'sine';
  osc.frequency.value = freq;
  // Short attack/decay envelope so the tone doesn't click.
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.exponentialRampToValueAtTime(0.25, at + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + dur);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(at);
  osc.stop(at + dur + 0.05);
}

/** Two-tone "pesanan baru" chirp + vibration. Silently no-ops when Web
 *  Audio is unavailable or the context hasn't been unlocked yet. */
export function playNewOrderAlert(): void {
  const ctx = ensureAudioContext();
  if (ctx && ctx.state === 'running') {
    const t = ctx.currentTime;
    beep(ctx, 880, t, 0.18);
    beep(ctx, 1174.66, t + 0.22, 0.22);
  }
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    navigator.vibrate([200, 100, 200]);
  }
}
