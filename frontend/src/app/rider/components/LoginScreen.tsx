'use client';

// LoginScreen — phone + bcrypt password against
// POST /api/v1/delivery/riders/login. Mirrors the original page.tsx login
// flow byte-for-byte (storage keys, phone whitespace strip) so installed
// PWAs keep working; only the visuals change.

import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Eye, EyeOff, Loader2, Truck } from 'lucide-react';

import { ApiError, loginRider } from '../lib/api';
import { loadRiderPhone, clearRiderPhone } from '../lib/storage';
import type { Rider } from '../lib/types';

interface LoginScreenProps {
  onLogin: (rider: Rider, rememberPhone: string | null) => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Pre-fill the phone from the last successful login if the previous
  // session asked us to remember it. Matches the original page.tsx
  // behavior so existing installs see no regression.
  useEffect(() => {
    const saved = loadRiderPhone();
    if (saved) setPhone(saved);
  }, []);

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError('');

    const trimmedPhone = phone.trim();
    if (!trimmedPhone || !password.trim()) {
      setError('Sila masukkan nombor telefon dan kata laluan');
      return;
    }

    setLoading(true);
    try {
      const rider = await loginRider(trimmedPhone, password);
      // If the user unchecked "Ingat saya", scrub any previously stored
      // phone so the next login starts blank.
      if (!rememberMe) clearRiderPhone();
      toast.success(`Selamat datang, ${rider.name}!`);
      onLogin(rider, rememberMe ? trimmedPhone : null);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'Login gagal. Cuba lagi.';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-between px-5 pt-12 pb-8">
      {/* Top spacer + brand */}
      <div className="w-full max-w-[400px] flex flex-col items-center mt-8">
        <div className="w-16 h-16 rounded-2xl bg-[var(--rider-lime)] flex items-center justify-center mb-4">
          <Truck className="w-8 h-8 text-black" strokeWidth={2.25} />
        </div>
        <h1 className="text-white text-[22px] font-semibold tracking-tight">
          BinaApp <span className="text-[var(--rider-lime)]">Rider</span>
        </h1>
      </div>

      {/* Form card */}
      <div className="w-full max-w-[400px] flex-1 flex flex-col justify-center">
        <h2 className="text-white text-[26px] font-semibold leading-tight">
          Log Masuk Penghantar
        </h2>
        <p className="mt-1.5 text-sm text-[var(--rider-text-2)]">
          Untuk penghantar BinaApp sahaja.
        </p>

        <form onSubmit={submit} className="mt-7 space-y-4">
          <div>
            <label
              htmlFor="rider-phone"
              className="block text-xs font-medium text-[var(--rider-text-2)] mb-1.5"
            >
              Nombor Telefon
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-sm text-[var(--rider-muted)] pointer-events-none">
                +60
              </span>
              <input
                id="rider-phone"
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                maxLength={12}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Contoh: 0123456789"
                disabled={loading}
                className="w-full pl-14 pr-4 h-14 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] text-white placeholder:text-[var(--rider-muted)] focus:outline-none focus:border-[var(--rider-lime)] transition-colors"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="rider-password"
              className="block text-xs font-medium text-[var(--rider-text-2)] mb-1.5"
            >
              Kata Laluan
            </label>
            <div className="relative">
              <input
                id="rider-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Kata laluan anda"
                disabled={loading}
                className="w-full pl-4 pr-12 h-14 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] text-white placeholder:text-[var(--rider-muted)] focus:outline-none focus:border-[var(--rider-lime)] transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--rider-text-2)] hover:text-white"
                aria-label={showPassword ? 'Sembunyi kata laluan' : 'Tunjuk kata laluan'}
              >
                {showPassword ? (
                  <EyeOff className="w-5 h-5" />
                ) : (
                  <Eye className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>

          <label className="flex items-center gap-2.5 select-none cursor-pointer">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded border-[var(--rider-border-2)] bg-[var(--rider-surface)] accent-[var(--rider-lime)]"
            />
            <span className="text-sm text-[var(--rider-text-2)]">
              Ingat saya
            </span>
          </label>

          {error && (
            <p className="text-sm text-[var(--rider-red)] rider-fade-in">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full h-14 rounded-2xl bg-[var(--rider-lime)] hover:bg-[var(--rider-lime-2)] text-black font-semibold text-base flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Memproses...
              </>
            ) : (
              'Log Masuk'
            )}
          </button>
        </form>
      </div>

      {/* Bottom hint */}
      <p className="w-full max-w-[400px] text-center text-xs text-[var(--rider-muted)] mt-8">
        Lupa kata laluan? Hubungi pemilik kedai.
      </p>
    </div>
  );
}
