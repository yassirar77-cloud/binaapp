// Attention sounds for the live dashboard — a dashboard on a second monitor
// gets no visual attention, so new orders and stuck transitions chime.
// Web Audio only (no assets); the AudioContext is created lazily because
// browsers block audio before the first user gesture.

const PREF_KEY = 'phl_sound_enabled';

let ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  type AudioWindow = Window & { webkitAudioContext?: typeof AudioContext };
  const Ctor = window.AudioContext || (window as AudioWindow).webkitAudioContext;
  if (!Ctor) return null;
  if (!ctx) {
    try {
      ctx = new Ctor();
    } catch {
      return null;
    }
  }
  if (ctx.state === 'suspended') {
    // Resume is only allowed after a user gesture; ignore failures.
    void ctx.resume().catch(() => {});
  }
  return ctx;
}

function tone(
  audio: AudioContext,
  freq: number,
  startAt: number,
  duration: number,
  gainPeak = 0.08,
) {
  const osc = audio.createOscillator();
  const gain = audio.createGain();
  osc.type = 'sine';
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.0001, startAt);
  gain.gain.exponentialRampToValueAtTime(gainPeak, startAt + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
  osc.connect(gain).connect(audio.destination);
  osc.start(startAt);
  osc.stop(startAt + duration + 0.02);
}

/** Cheerful two-note chime — a new order arrived. */
export function playNewOrderChime(): void {
  const audio = getCtx();
  if (!audio) return;
  const t = audio.currentTime;
  tone(audio, 880, t, 0.18);
  tone(audio, 1174.66, t + 0.16, 0.24);
}

/** Lower two-pulse warning — an order just became stuck. */
export function playStuckAlert(): void {
  const audio = getCtx();
  if (!audio) return;
  const t = audio.currentTime;
  tone(audio, 330, t, 0.22, 0.1);
  tone(audio, 330, t + 0.28, 0.22, 0.1);
}

export function loadSoundPref(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return localStorage.getItem(PREF_KEY) !== '0';
  } catch {
    return true;
  }
}

export function saveSoundPref(enabled: boolean): void {
  try {
    localStorage.setItem(PREF_KEY, enabled ? '1' : '0');
  } catch {
    /* ignore */
  }
}
