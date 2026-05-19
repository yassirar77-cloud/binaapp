'use client';

// ProfileScreen — the "Saya" tab.
//
// Sections (top to bottom):
//   1. Hero — avatar + name + vehicle plate + today's stats
//   2. Online / Offline toggle (UI-only for now, see comment below)
//   3. Profile card (phone + vehicle, read-only)
//   4. Settings (notification sound + battery saver, localStorage)
//   5. Log Keluar button → confirmation modal
//
// Today's stats are fetched from /api/v1/delivery/riders/{id}/today
// (Phase-4 endpoint). The fetch shows a skeleton while in-flight and
// silently falls back to zeros on error so the rider never sees a
// broken hero.

import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
  Bike,
  Loader2,
  LogOut,
  Phone,
  ShieldCheck,
  TrendingUp,
  Volume2,
  Wifi,
  WifiOff,
  Zap,
} from 'lucide-react';

import { ApiError, fetchTodayStats, setRiderOnline } from '../lib/api';
import {
  loadBatterySaverPref,
  loadOnlinePref,
  loadSoundPref,
  saveBatterySaverPref,
  saveOnlinePref,
  saveSoundPref,
} from '../lib/storage';
import type { Rider, TodayStats } from '../lib/types';

interface ProfileScreenProps {
  rider: Rider;
  onLogout: () => void;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0) return '?';
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase();
}

export default function ProfileScreen({
  rider,
  onLogout,
}: ProfileScreenProps) {
  const [stats, setStats] = useState<TodayStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [online, setOnline] = useState<boolean>(() => loadOnlinePref());
  const [sound, setSound] = useState<boolean>(() => loadSoundPref());
  const [batterySaver, setBatterySaver] = useState<boolean>(() =>
    loadBatterySaverPref(),
  );
  const [confirmLogout, setConfirmLogout] = useState(false);

  // One-shot fetch on mount. The parent unmounts the screen when the
  // rider taps another nav, so we don't need to poll here.
  useEffect(() => {
    let cancelled = false;
    setStatsLoading(true);
    fetchTodayStats(rider.id)
      .then((s) => {
        if (!cancelled) setStats(s);
      })
      .catch(() => {
        // fetchTodayStats already swallows 404. If we landed here it's
        // a network failure — show zeros rather than nothing.
        if (!cancelled) setStats({ count: 0, earnings: '0.00' });
      })
      .finally(() => {
        if (!cancelled) setStatsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [rider.id]);

  const handleOnlineToggle = async () => {
    const prev = online;
    const next = !prev;
    // Optimistic flip — feels instant and lets the merchant picker see the
    // new state on its next fetch.
    setOnline(next);
    saveOnlinePref(next);
    try {
      await setRiderOnline(rider.id, next);
      toast(
        next
          ? 'Anda kini Online — boleh terima pesanan.'
          : 'Anda kini Offline — tiada pesanan baru.',
        { icon: next ? '🟢' : '⚫' },
      );
    } catch (e) {
      setOnline(prev);
      saveOnlinePref(prev);
      const msg =
        e instanceof ApiError && e.message
          ? e.message
          : 'Gagal kemas kini status. Sila cuba lagi.';
      toast.error(msg);
    }
  };

  const handleSoundToggle = () => {
    const next = !sound;
    setSound(next);
    saveSoundPref(next);
  };
  const handleBatterySaverToggle = () => {
    const next = !batterySaver;
    setBatterySaver(next);
    saveBatterySaverPref(next);
  };

  return (
    <div className="min-h-[100dvh] pb-24 rider-fade-in">
      {/* Hero */}
      <section className="px-5 pt-6 pb-5">
        <div className="flex items-center gap-4">
          {rider.photo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={rider.photo_url}
              alt={rider.name}
              className="w-20 h-20 rounded-full object-cover border-2 border-[var(--rider-border-2)]"
            />
          ) : (
            <div className="w-20 h-20 rounded-full bg-[var(--rider-lime)] text-black text-[24px] font-bold flex items-center justify-center">
              {initials(rider.name)}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h1 className="text-[20px] font-semibold text-white truncate">
              {rider.name}
            </h1>
            <p className="mt-0.5 text-[12px] font-mono text-[var(--rider-text-2)] truncate">
              {rider.vehicle_plate || '—'}
              {rider.vehicle_type ? ` · ${rider.vehicle_type}` : ''}
            </p>
          </div>
        </div>

        {/* Today's stats */}
        <div className="mt-5 grid grid-cols-2 gap-2.5">
          <StatCard
            label="Pesanan Hari Ini"
            value={statsLoading ? null : String(stats?.count ?? 0)}
            Icon={ShieldCheck}
            accent="var(--rider-violet)"
          />
          <StatCard
            label="Pendapatan"
            value={statsLoading ? null : `RM${stats?.earnings ?? '0.00'}`}
            Icon={TrendingUp}
            accent="var(--rider-lime)"
          />
        </div>
      </section>

      {/* Online toggle */}
      <section className="mx-4">
        <button
          type="button"
          onClick={handleOnlineToggle}
          className={`w-full rounded-2xl p-4 flex items-center gap-3 border transition-colors ${
            online
              ? 'bg-[rgba(199,255,61,0.10)] border-[rgba(199,255,61,0.30)]'
              : 'bg-[var(--rider-surface)] border-[var(--rider-border)]'
          }`}
          aria-pressed={online}
        >
          <div
            className={`w-11 h-11 rounded-full flex items-center justify-center ${
              online ? 'bg-[var(--rider-lime)]' : 'bg-[var(--rider-surface-2)]'
            }`}
          >
            {online ? (
              <Wifi className="w-5 h-5 text-black" strokeWidth={2.5} />
            ) : (
              <WifiOff className="w-5 h-5 text-[var(--rider-text-2)]" />
            )}
          </div>
          <div className="flex-1 text-left min-w-0">
            <p
              className={`text-[15px] font-semibold ${
                online ? 'text-[var(--rider-lime)]' : 'text-white'
              }`}
            >
              {online ? 'Anda Online' : 'Anda Offline'}
            </p>
            <p className="text-[12px] text-[var(--rider-text-2)] truncate">
              {online ? 'Boleh terima pesanan baru.' : 'Tiada pesanan baru.'}
            </p>
          </div>
          <SwitchTrack on={online} />
        </button>
      </section>

      {/* Profile card */}
      <section className="mx-4 mt-3 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] divide-y divide-[var(--rider-border)]">
        <ProfileRow
          Icon={Phone}
          label="Nombor Telefon"
          value={rider.phone}
          mono
        />
        <ProfileRow
          Icon={Bike}
          label="Kenderaan"
          value={[rider.vehicle_type, rider.vehicle_plate]
            .filter(Boolean)
            .join(' · ') || '—'}
        />
      </section>

      {/* Settings */}
      <section className="mx-4 mt-3 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] divide-y divide-[var(--rider-border)]">
        <SettingRow
          Icon={Volume2}
          label="Bunyi Notifikasi"
          on={sound}
          onToggle={handleSoundToggle}
        />
        <SettingRow
          Icon={Zap}
          label="Mode Jimat Bateri"
          on={batterySaver}
          onToggle={handleBatterySaverToggle}
        />
      </section>

      {/* Logout */}
      <section className="mx-4 mt-5">
        <button
          type="button"
          onClick={() => setConfirmLogout(true)}
          className="w-full h-12 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] text-[var(--rider-red)] text-[14px] font-semibold flex items-center justify-center gap-2 hover:bg-[var(--rider-surface-2)] transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Log Keluar
        </button>
        <p className="mt-2 text-center text-[11px] text-[var(--rider-muted)]">
          BinaApp Rider · {new Date().getFullYear()}
        </p>
      </section>

      {confirmLogout && (
        <LogoutConfirm
          onCancel={() => setConfirmLogout(false)}
          onConfirm={() => {
            setConfirmLogout(false);
            onLogout();
          }}
        />
      )}
    </div>
  );
}

// ----- Internal pieces -----

interface StatCardProps {
  label: string;
  value: string | null;
  Icon: typeof TrendingUp;
  accent: string;
}

function StatCard({ label, value, Icon, accent }: StatCardProps) {
  return (
    <div className="rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] p-3.5">
      <div className="flex items-center gap-2">
        <Icon className="w-3.5 h-3.5" style={{ color: accent }} />
        <p className="text-[11px] font-medium text-[var(--rider-text-2)] uppercase tracking-wide">
          {label}
        </p>
      </div>
      {value === null ? (
        <div className="mt-1.5 h-7 w-20 rounded-md bg-[var(--rider-surface-2)] animate-pulse" />
      ) : (
        <p
          className="mt-1.5 font-mono text-[22px] font-bold leading-tight"
          style={{ color: accent }}
        >
          {value}
        </p>
      )}
    </div>
  );
}

interface ProfileRowProps {
  Icon: typeof Phone;
  label: string;
  value: string;
  mono?: boolean;
}

function ProfileRow({ Icon, label, value, mono }: ProfileRowProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-3.5">
      <Icon className="w-4 h-4 text-[var(--rider-text-2)] shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-medium text-[var(--rider-text-2)] uppercase tracking-wide">
          {label}
        </p>
        <p
          className={`mt-0.5 text-[14px] text-white truncate ${
            mono ? 'font-mono' : ''
          }`}
        >
          {value}
        </p>
      </div>
    </div>
  );
}

interface SettingRowProps {
  Icon: typeof Volume2;
  label: string;
  on: boolean;
  onToggle: () => void;
}

function SettingRow({ Icon, label, on, onToggle }: SettingRowProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={on}
      className="w-full flex items-center gap-3 px-4 py-3.5 text-left"
    >
      <Icon className="w-4 h-4 text-[var(--rider-text-2)] shrink-0" />
      <p className="flex-1 min-w-0 text-[14px] text-white">{label}</p>
      <SwitchTrack on={on} />
    </button>
  );
}

function SwitchTrack({ on }: { on: boolean }) {
  return (
    <span
      className={`relative inline-flex w-11 h-6 rounded-full transition-colors ${
        on ? 'bg-[var(--rider-lime)]' : 'bg-[var(--rider-surface-2)]'
      }`}
    >
      <span
        className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${
          on ? 'left-[22px]' : 'left-0.5'
        }`}
      />
    </span>
  );
}

interface LogoutConfirmProps {
  onConfirm: () => void;
  onCancel: () => void;
}

function LogoutConfirm({ onConfirm, onCancel }: LogoutConfirmProps) {
  const [busy, setBusy] = useState(false);
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center rider-fade-in"
    >
      <button
        type="button"
        aria-label="Tutup"
        onClick={busy ? undefined : onCancel}
        className="absolute inset-0 bg-black/65 backdrop-blur-sm"
      />
      <div className="relative w-full sm:max-w-sm sm:mx-4 bg-[var(--rider-surface)] rounded-t-3xl sm:rounded-3xl border border-[var(--rider-border)] p-5 rider-modal-in">
        <div className="flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-2xl bg-[rgba(255,90,95,0.12)] border border-[rgba(255,90,95,0.30)] flex items-center justify-center mb-3">
            <LogOut
              className="w-7 h-7 text-[var(--rider-red)]"
              strokeWidth={2.25}
            />
          </div>
          <h2 className="text-[18px] font-semibold text-white">
            Anda pasti mahu log keluar?
          </h2>
          <p className="mt-1.5 text-[13px] text-[var(--rider-text-2)]">
            Anda perlu log masuk semula selepas ini.
          </p>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="h-12 rounded-2xl bg-[var(--rider-surface-2)] border border-[var(--rider-border)] text-white text-[14px] font-medium disabled:opacity-60"
          >
            Batal
          </button>
          <button
            type="button"
            onClick={() => {
              setBusy(true);
              onConfirm();
            }}
            disabled={busy}
            className="h-12 rounded-2xl bg-[var(--rider-red)] text-white text-[14px] font-semibold flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
            Log Keluar
          </button>
        </div>
      </div>
    </div>
  );
}
