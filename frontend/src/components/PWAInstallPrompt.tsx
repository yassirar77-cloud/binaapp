'use client';

import { useState, useEffect } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

// Extend Window interface to include our global PWA variables
declare global {
  interface Window {
    __pwaInstallPrompt: BeforeInstallPromptEvent | null;
    __pwaInstallPromptCaptured: boolean;
  }
}

interface Props {
  appName?: string;
  themeColor?: string;
}

export function PWAInstallPrompt({ appName = 'BinaApp', themeColor = '#3b82f6' }: Props) {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  useEffect(() => {
    // Check if already installed
    const standalone = window.matchMedia('(display-mode: standalone)').matches
      || (window.navigator as any).standalone === true;
    setIsStandalone(standalone);

    // Improved iOS detection - handles Safari, WebView, and various iOS browsers
    const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera || '';
    const ios = /iPad|iPhone|iPod/.test(userAgent) && !(window as any).MSStream;
    // Also check for iPad on iOS 13+ which reports as Mac
    const isIPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
    const isIOSDevice = ios || isIPadOS;
    setIsIOS(isIOSDevice);

    // Check if prompt was already captured globally (before React mounted)
    if (window.__pwaInstallPromptCaptured && window.__pwaInstallPrompt) {
      console.log('[PWA] Using globally captured install prompt');
      setDeferredPrompt(window.__pwaInstallPrompt);
      setShowPrompt(true);
    }

    // Listen for install prompt (Android/Desktop) - for late events
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      console.log('[PWA] Install prompt captured in React');
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setShowPrompt(true);
    };

    // Also listen for our custom event dispatched from the early capture script
    const handlePromptReady = () => {
      if (window.__pwaInstallPrompt) {
        console.log('[PWA] Install prompt ready from early capture');
        setDeferredPrompt(window.__pwaInstallPrompt);
        setShowPrompt(true);
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('pwa-prompt-ready', handlePromptReady);

    // Listen for successful install
    const handleInstalled = () => {
      console.log('[PWA] App installed successfully');
      setShowPrompt(false);
      setDeferredPrompt(null);
      window.__pwaInstallPrompt = null;
      window.__pwaInstallPromptCaptured = false;
    };
    window.addEventListener('appinstalled', handleInstalled);

    // Show iOS prompt after 3 seconds if not installed and not in standalone mode
    if (isIOSDevice && !standalone) {
      setTimeout(() => setShowPrompt(true), 3000);
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('pwa-prompt-ready', handlePromptReady);
      window.removeEventListener('appinstalled', handleInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    console.log('[PWA] Triggering install prompt');
    deferredPrompt.prompt();

    const { outcome } = await deferredPrompt.userChoice;
    console.log('[PWA] User choice:', outcome);

    if (outcome === 'accepted') {
      setShowPrompt(false);
    }
    setDeferredPrompt(null);
    // Clear global prompt
    window.__pwaInstallPrompt = null;
    window.__pwaInstallPromptCaptured = false;
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    // Don't show again for 7 days
    localStorage.setItem('pwa-prompt-dismissed', Date.now().toString());
  };

  // Check if dismissed recently
  useEffect(() => {
    const dismissed = localStorage.getItem('pwa-prompt-dismissed');
    if (dismissed) {
      const dismissedTime = parseInt(dismissed);
      const sevenDays = 7 * 24 * 60 * 60 * 1000;
      if (Date.now() - dismissedTime < sevenDays) {
        setShowPrompt(false);
      }
    }
  }, []);

  // Don't show if already installed
  if (isStandalone || !showPrompt) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 animate-slide-up">
      <div
        className="max-w-md mx-auto rounded-2xl shadow-2xl overflow-hidden"
        style={{ backgroundColor: 'white' }}
      >
        {/* Header */}
        <div
          className="px-4 py-3 text-white flex items-center gap-3"
          style={{ backgroundColor: themeColor }}
        >
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center text-2xl">
            📱
          </div>
          <div className="flex-1">
            <div className="font-bold">Install {appName}</div>
            <div className="text-sm opacity-90">Akses lebih cepat dari home screen</div>
          </div>
          <button
            onClick={handleDismiss}
            className="text-white/80 hover:text-white text-xl"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-4">
          {isIOS ? (
            // iOS instructions
            <div className="space-y-3">
              <p className="text-gray-600 text-sm">
                Untuk install di iPhone/iPad:
              </p>
              <ol className="text-sm text-gray-700 space-y-2">
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center text-xs">1</span>
                  Tekan ikon <span className="text-blue-500">Share</span>
                  <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                  </svg>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center text-xs">2</span>
                  Pilih <strong>&quot;Add to Home Screen&quot;</strong>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center text-xs">3</span>
                  Tekan <strong>&quot;Add&quot;</strong>
                </li>
              </ol>
              <button
                onClick={handleDismiss}
                className="w-full py-2 rounded-lg text-gray-600 text-sm"
              >
                Nanti
              </button>
            </div>
          ) : (
            // Android/Desktop install button
            <div className="flex gap-2">
              <button
                onClick={handleDismiss}
                className="flex-1 py-3 rounded-xl border border-gray-200 text-gray-600 font-medium"
              >
                Nanti
              </button>
              <button
                onClick={handleInstall}
                className="flex-1 py-3 rounded-xl text-white font-medium"
                style={{ backgroundColor: themeColor }}
              >
                ⬇️ Install
              </button>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-up {
          from { transform: translateY(100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
