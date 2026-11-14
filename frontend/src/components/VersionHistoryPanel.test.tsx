// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import toast from 'react-hot-toast';
import VersionHistoryPanel from './VersionHistoryPanel';
import { versionErrorMessage, versionSourceLabel } from '@/lib/websiteVersions';

vi.mock('react-hot-toast', () => {
  const toast = Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
  });
  return { default: toast, toast };
});

vi.mock('@/lib/supabase', () => ({
  getApiAuthToken: vi.fn(async () => 'tok-123'),
}));

const fetchVersions = vi.fn();
const fetchVersionHtml = vi.fn();
const restoreVersion = vi.fn();
const labelVersion = vi.fn();

vi.mock('@/lib/websiteVersions', async () => {
  const actual = await vi.importActual<typeof import('@/lib/websiteVersions')>(
    '@/lib/websiteVersions'
  );
  return {
    ...actual,
    fetchVersions: (...args: unknown[]) => fetchVersions(...args),
    fetchVersionHtml: (...args: unknown[]) => fetchVersionHtml(...args),
    restoreVersion: (...args: unknown[]) => restoreVersion(...args),
    labelVersion: (...args: unknown[]) => labelVersion(...args),
  };
});

const VERSIONS = [
  {
    id: 'v-2',
    website_id: 'ws-1',
    source: 'regenerate',
    label: null,
    size_bytes: 20480,
    created_at: '2026-11-14T07:05:00Z',
  },
  {
    id: 'v-1',
    website_id: 'ws-1',
    source: 'manual_save',
    label: 'Sebelum Raya',
    size_bytes: 18000,
    created_at: '2026-11-13T07:05:00Z',
  },
];

const OLD_HTML = '<!DOCTYPE html><html><body><h1>Dahulu</h1></body></html>';

function openPanel(props: Partial<Parameters<typeof VersionHistoryPanel>[0]> = {}) {
  const onHtmlChange = vi.fn();
  render(<VersionHistoryPanel websiteId="ws-1" onHtmlChange={onHtmlChange} {...props} />);
  fireEvent.click(screen.getByRole('button', { name: /Sejarah Versi/ }));
  return { onHtmlChange };
}

beforeEach(() => {
  vi.clearAllMocks();
  fetchVersions.mockResolvedValue(VERSIONS);
  fetchVersionHtml.mockResolvedValue(OLD_HTML);
  restoreVersion.mockResolvedValue({
    success: true,
    changed: true,
    message: 'Versi dipulihkan.',
    live_site_updated: true,
    html_content: OLD_HTML,
  });
});

afterEach(cleanup);

describe('VersionHistoryPanel', () => {
  it('loads nothing until it is opened', () => {
    render(<VersionHistoryPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    expect(fetchVersions).not.toHaveBeenCalled();
  });

  it('lists versions with their source and the merchant label', async () => {
    openPanel();
    expect(await screen.findByText('Sebelum jana semula AI')).toBeTruthy();
    expect(screen.getByText('Sebelum Raya')).toBeTruthy();
    expect(fetchVersions).toHaveBeenCalledWith('ws-1', 'tok-123');
  });

  it('says so when there is no history yet', async () => {
    fetchVersions.mockResolvedValue([]);
    openPanel();
    expect(await screen.findByText(/Belum ada versi tersimpan/)).toBeTruthy();
  });

  it('previews a version in an iframe that cannot run scripts', async () => {
    openPanel();
    await screen.findByText('Sebelum jana semula AI');
    fireEvent.click(screen.getAllByRole('button', { name: 'Pratonton' })[0]);

    const frame = (await screen.findByTitle(/Pratonton versi/)) as HTMLIFrameElement;
    expect(frame.getAttribute('srcdoc')).toBe(OLD_HTML);
    expect(frame.getAttribute('sandbox')).toBe('');
    expect(fetchVersionHtml).toHaveBeenCalledWith('ws-1', 'v-2', 'tok-123');
  });

  it('does not restore until the merchant confirms', async () => {
    const { onHtmlChange } = openPanel();
    await screen.findByText('Sebelum jana semula AI');
    fireEvent.click(screen.getAllByRole('button', { name: 'Pulihkan' })[0]);

    expect(restoreVersion).not.toHaveBeenCalled();
    expect(screen.getByRole('alertdialog')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Batal' }));
    expect(screen.queryByRole('alertdialog')).toBeNull();
    expect(restoreVersion).not.toHaveBeenCalled();
    expect(onHtmlChange).not.toHaveBeenCalled();
  });

  it('restores, hands the html to the editor and reloads the list', async () => {
    const { onHtmlChange } = openPanel();
    await screen.findByText('Sebelum jana semula AI');
    fireEvent.click(screen.getAllByRole('button', { name: 'Pulihkan' })[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Ya, pulihkan' }));

    await waitFor(() => expect(onHtmlChange).toHaveBeenCalledWith(OLD_HTML));
    expect(restoreVersion).toHaveBeenCalledWith('ws-1', 'v-2', 'tok-123');
    expect(toast.success).toHaveBeenCalled();
    await waitFor(() => expect(fetchVersions).toHaveBeenCalledTimes(2));
  });

  it('warns that unsaved editor changes will be lost', async () => {
    openPanel({ hasUnsavedChanges: true });
    await screen.findByText('Sebelum jana semula AI');
    fireEvent.click(screen.getAllByRole('button', { name: 'Pulihkan' })[0]);
    expect(screen.getByText(/belum disimpan akan hilang/)).toBeTruthy();
  });

  it('leaves the editor alone when the restore fails', async () => {
    restoreVersion.mockRejectedValue(new Error('Versi ini tidak lengkap dan tidak boleh dipulihkan.'));
    const { onHtmlChange } = openPanel();
    await screen.findByText('Sebelum jana semula AI');
    fireEvent.click(screen.getAllByRole('button', { name: 'Pulihkan' })[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Ya, pulihkan' }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        'Versi ini tidak lengkap dan tidak boleh dipulihkan.'
      )
    );
    expect(onHtmlChange).not.toHaveBeenCalled();
  });

  it('does not touch the editor when nothing changed', async () => {
    restoreVersion.mockResolvedValue({
      success: true,
      changed: false,
      message: 'Tiada perubahan — laman web sudah sama dengan versi ini.',
      live_site_updated: false,
      html_content: OLD_HTML,
    });
    const { onHtmlChange } = openPanel();
    await screen.findByText('Sebelum jana semula AI');
    fireEvent.click(screen.getAllByRole('button', { name: 'Pulihkan' })[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Ya, pulihkan' }));

    await waitFor(() => expect(restoreVersion).toHaveBeenCalled());
    expect(onHtmlChange).not.toHaveBeenCalled();
  });

  it('shows a load failure with a retry', async () => {
    fetchVersions.mockRejectedValueOnce(new Error('Sejarah versi tidak dapat dimuatkan. Cuba lagi.'));
    openPanel();
    expect(await screen.findByText(/tidak dapat dimuatkan/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Cuba lagi' }));
    expect(await screen.findByText('Sebelum jana semula AI')).toBeTruthy();
  });
});

describe('websiteVersions helpers', () => {
  it('maps error codes to Malay copy', () => {
    expect(versionErrorMessage(401)).toMatch(/log masuk/);
    expect(versionErrorMessage(404, { error: 'version_not_found' })).toMatch(/tidak ditemui/);
    expect(versionErrorMessage(422, { error: 'version_html_unbalanced' })).toMatch(/tidak lengkap/);
    expect(versionErrorMessage(409, { error: 'generation_in_progress' })).toMatch(/sedang dijana/);
  });

  it('falls back for an unknown source', () => {
    expect(versionSourceLabel('theme')).toBe('Sebelum tukar tema');
    expect(versionSourceLabel('whatever')).toBe('Versi terdahulu');
  });
});
