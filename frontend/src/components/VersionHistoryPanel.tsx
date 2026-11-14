'use client';

/**
 * Sejarah Versi — earlier copies of the page, and a way back to them.
 *
 * Every change that overwrites the page (a save here, an AI regenerate, a
 * theme change…) first stores the page as it was. This panel lists those
 * copies, previews one in a sandboxed iframe, and restores it.
 *
 * A restore is credit-free and writes straight through to the stored (and,
 * when published, the live) site — so like the Design Studio it hands the
 * new HTML back through onHtmlChange and the editor leaves its buffer clean.
 * It is also undoable: the page being replaced becomes the newest version.
 */

import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { getApiAuthToken } from '@/lib/supabase';
import {
  fetchVersionHtml,
  fetchVersions,
  formatVersionSize,
  formatVersionTime,
  labelVersion,
  restoreVersion,
  versionSourceLabel,
  type WebsiteVersion,
} from '@/lib/websiteVersions';

interface Props {
  websiteId: string;
  /** Whether the editor holds edits that have not been saved. */
  hasUnsavedChanges?: boolean;
  /** Bump to reload the list (e.g. after the editor saves). */
  refreshKey?: number | string;
  /** Called with the restored HTML. */
  onHtmlChange: (html: string) => void;
}

export default function VersionHistoryPanel({
  websiteId,
  hasUnsavedChanges = false,
  refreshKey,
  onHtmlChange,
}: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [versions, setVersions] = useState<WebsiteVersion[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getApiAuthToken();
      setVersions(await fetchVersions(websiteId, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal memuatkan sejarah versi.');
    } finally {
      setLoading(false);
    }
  }, [websiteId]);

  useEffect(() => {
    if (open) void load();
  }, [open, load, refreshKey]);

  const preview = async (version: WebsiteVersion) => {
    if (selectedId === version.id) {
      setSelectedId(null);
      setPreviewHtml(null);
      return;
    }
    setSelectedId(version.id);
    setPreviewHtml(null);
    setConfirmId(null);
    setPreviewLoading(true);
    try {
      const token = await getApiAuthToken();
      setPreviewHtml(await fetchVersionHtml(websiteId, version.id, token));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Gagal memuatkan pratonton.');
      setSelectedId(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const restore = async (version: WebsiteVersion) => {
    setRestoring(true);
    try {
      const token = await getApiAuthToken();
      const result = await restoreVersion(websiteId, version.id, token);
      if (!result.changed) {
        toast(result.message || 'Tiada perubahan.');
      } else {
        onHtmlChange(result.html_content);
        if (result.warning) toast(result.message);
        else toast.success('Versi dipulihkan. Anda boleh buat asal dari senarai ini.');
      }
      setConfirmId(null);
      setSelectedId(null);
      setPreviewHtml(null);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Gagal memulihkan versi.');
    } finally {
      setRestoring(false);
    }
  };

  const rename = async (version: WebsiteVersion) => {
    const next = window.prompt('Nama untuk versi ini (kosongkan untuk buang):', version.label || '');
    if (next === null) return;
    try {
      const token = await getApiAuthToken();
      const updated = await labelVersion(websiteId, version.id, next.trim(), token);
      setVersions((rows) =>
        rows.map((row) => (row.id === version.id ? { ...row, label: updated.label } : row))
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Gagal menamakan versi.');
    }
  };

  return (
    <section
      className="bg-white border border-gray-200 rounded-2xl p-5 sm:p-6 shadow-sm"
      aria-label="Sejarah Versi"
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 text-left"
      >
        <span className="text-2xl" aria-hidden="true">🕘</span>
        <span className="text-lg font-bold text-gray-900">Sejarah Versi</span>
        <span className="ml-auto text-[11px] font-semibold uppercase tracking-wide text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
          Percuma
        </span>
        <span className="text-gray-400 text-sm" aria-hidden="true">{open ? '▲' : '▼'}</span>
      </button>
      <p className="text-sm text-gray-500 mt-1">
        Tersilap simpan atau tak suka hasil jana semula? Pulihkan versi terdahulu — tanpa kredit AI.
      </p>

      {open && (
        <div className="mt-4">
          {error && (
            <div className="mb-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 flex items-center gap-3">
              <span className="flex-1">{error}</span>
              <button
                type="button"
                onClick={() => void load()}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold border border-red-200 bg-white hover:bg-red-50"
              >
                Cuba lagi
              </button>
            </div>
          )}

          {loading && versions.length === 0 && (
            <div className="h-20 rounded-xl bg-gray-100 animate-pulse" aria-hidden="true" />
          )}

          {!loading && !error && versions.length === 0 && (
            <div className="rounded-xl border border-dashed border-gray-300 p-4 text-sm text-gray-500">
              Belum ada versi tersimpan. Versi akan disimpan secara automatik setiap kali
              laman web anda diubah.
            </div>
          )}

          {versions.length > 0 && (
            <ul className="space-y-2 max-h-[28rem] overflow-y-auto pr-1">
              {versions.map((version) => {
                const selected = selectedId === version.id;
                return (
                  <li
                    key={version.id}
                    className={`rounded-xl border p-3 ${
                      selected ? 'border-gray-900 bg-gray-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-gray-900 truncate">
                          {version.label || versionSourceLabel(version.source)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatVersionTime(version.created_at)}
                          {version.label ? ` · ${versionSourceLabel(version.source)}` : ''}
                          {version.size_bytes ? ` · ${formatVersionSize(version.size_bytes)}` : ''}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => void rename(version)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                      >
                        Namakan
                      </button>
                      <button
                        type="button"
                        onClick={() => void preview(version)}
                        aria-pressed={selected}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-semibold border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                      >
                        {selected ? 'Tutup' : 'Pratonton'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmId(version.id)}
                        disabled={restoring}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-gray-900 text-white hover:bg-black disabled:opacity-50 transition-colors"
                      >
                        Pulihkan
                      </button>
                    </div>

                    {selected && (
                      <div className="mt-3">
                        {previewLoading && (
                          <div className="h-64 rounded-lg bg-gray-100 animate-pulse" aria-hidden="true" />
                        )}
                        {previewHtml !== null && (
                          // No allow-scripts / allow-same-origin: an old copy
                          // of the page is shown, never run, and cannot reach
                          // the editor's session.
                          <iframe
                            title={`Pratonton versi ${formatVersionTime(version.created_at)}`}
                            sandbox=""
                            srcDoc={previewHtml}
                            className="w-full h-80 rounded-lg border border-gray-200 bg-white"
                          />
                        )}
                      </div>
                    )}

                    {confirmId === version.id && (
                      <div
                        role="alertdialog"
                        aria-label="Sahkan pemulihan versi"
                        className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
                      >
                        <div className="font-semibold">
                          Pulihkan versi {formatVersionTime(version.created_at)}?
                        </div>
                        <div className="text-xs mt-1">
                          Laman web semasa akan diganti dengan versi ini (termasuk laman yang
                          telah diterbitkan). Laman semasa disimpan dahulu sebagai versi baharu,
                          jadi anda boleh buat asal.
                          {hasUnsavedChanges &&
                            ' Perubahan dalam editor yang belum disimpan akan hilang.'}
                        </div>
                        <div className="mt-2 flex gap-2">
                          <button
                            type="button"
                            onClick={() => void restore(version)}
                            disabled={restoring}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-900 text-white hover:bg-black disabled:opacity-50"
                          >
                            {restoring ? 'Memulihkan…' : 'Ya, pulihkan'}
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmId(null)}
                            disabled={restoring}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                          >
                            Batal
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}

          {versions.length > 0 && (
            <p className="mt-3 text-xs text-gray-400">
              Sehingga 20 versi terbaharu disimpan. Setiap versi ialah laman web anda sebelum
              perubahan yang dinyatakan.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
