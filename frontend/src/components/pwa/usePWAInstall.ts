'use client';

import { useSyncExternalStore } from 'react';

// Single shared holder of the `beforeinstallprompt` deferred event.
//
// The early-capture script in app/layout.tsx <head> calls preventDefault()
// before React mounts — that is what suppresses Chrome's automatic install
// mini-infobar — and parks the event on window.__pwaInstallPrompt. This
// module adopts that event and keeps listening for late/re-fired events.
// All install UI (InstallAppButton, DownloadAppCard) reads from this one
// store, so multiple components mounted on the same page share one listener
// set and never fight over the prompt.

export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

declare global {
  interface Window {
    __pwaInstallPrompt: BeforeInstallPromptEvent | null;
    __pwaInstallPromptCaptured: boolean;
  }
  interface WindowEventMap {
    beforeinstallprompt: BeforeInstallPromptEvent;
  }
}

export interface PWAInstallState {
  /** A deferred native prompt is being held — promptInstall() will work. */
  canInstall: boolean;
  /** iOS/iPadOS — no native prompt exists; show the Add to Home Screen guide. */
  isIOS: boolean;
  /** Currently running as the installed app (standalone display mode). */
  isStandalone: boolean;
  /** Installed during this page's lifetime (prompt accepted / appinstalled). */
  isInstalled: boolean;
}

const INITIAL_STATE: PWAInstallState = {
  canInstall: false,
  isIOS: false,
  isStandalone: false,
  isInstalled: false,
};

let state = INITIAL_STATE;
let deferredPrompt: BeforeInstallPromptEvent | null = null;
let wired = false;
const listeners = new Set<() => void>();

function setState(patch: Partial<PWAInstallState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

function adoptDeferredPrompt(e: BeforeInstallPromptEvent) {
  deferredPrompt = e;
  setState({ canInstall: true });
}

function wire() {
  if (wired || typeof window === 'undefined') return;
  wired = true;

  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as any).standalone === true;

  const ua = navigator.userAgent || navigator.vendor || '';
  const isIOS =
    (/iPad|iPhone|iPod/.test(ua) && !(window as any).MSStream) ||
    // iPadOS 13+ reports as MacIntel with touch support
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  setState({ isStandalone, isIOS });

  // Adopt an event the early <head> script captured before React mounted.
  if (window.__pwaInstallPromptCaptured && window.__pwaInstallPrompt) {
    adoptDeferredPrompt(window.__pwaInstallPrompt);
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    adoptDeferredPrompt(e);
  });

  // Fired by the early-capture script after it parks the event, in case
  // the event races React hydration.
  window.addEventListener('pwa-prompt-ready', () => {
    if (window.__pwaInstallPrompt) adoptDeferredPrompt(window.__pwaInstallPrompt);
  });

  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    window.__pwaInstallPrompt = null;
    window.__pwaInstallPromptCaptured = false;
    setState({ canInstall: false, isInstalled: true });
  });
}

function subscribe(cb: () => void) {
  wire();
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

/**
 * Fire the native Chrome/Edge install dialog using the held deferred event.
 * The event is single-use: it is cleared before prompting so a double-click
 * can't re-fire a consumed prompt.
 */
export async function promptInstall(): Promise<'accepted' | 'dismissed' | 'unavailable'> {
  if (!deferredPrompt) return 'unavailable';
  const evt = deferredPrompt;
  deferredPrompt = null;
  window.__pwaInstallPrompt = null;
  window.__pwaInstallPromptCaptured = false;
  setState({ canInstall: false });

  evt.prompt();
  const { outcome } = await evt.userChoice;
  if (outcome === 'accepted') setState({ isInstalled: true });
  return outcome;
}

export function usePWAInstall() {
  const snapshot = useSyncExternalStore(
    subscribe,
    () => state,
    () => INITIAL_STATE,
  );
  return { ...snapshot, promptInstall };
}
