// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import toast from 'react-hot-toast';
import DesignStudioPanel from './DesignStudioPanel';

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

const applyTheme = vi.fn();
const fetchDesignOptions = vi.fn();
const fetchCurrentTheme = vi.fn();
const fetchPosterHtml = vi.fn();

vi.mock('@/lib/designStudio', async () => {
  const actual = await vi.importActual<typeof import('@/lib/designStudio')>(
    '@/lib/designStudio'
  );
  return {
    ...actual,
    applyTheme: (...args: unknown[]) => applyTheme(...args),
    fetchDesignOptions: (...args: unknown[]) => fetchDesignOptions(...args),
    fetchCurrentTheme: (...args: unknown[]) => fetchCurrentTheme(...args),
    fetchPosterHtml: (...args: unknown[]) => fetchPosterHtml(...args),
  };
});

/** A stand-in for the tab window.open returns, so we can inspect what we wrote. */
function fakeTab() {
  const written: string[] = [];
  return {
    closed: false,
    written,
    close: vi.fn(function (this: { closed: boolean }) {
      this.closed = true;
    }),
    document: {
      open: vi.fn(),
      write: vi.fn((html: string) => written.push(html)),
      close: vi.fn(),
    },
  };
}

const OPTIONS = {
  palettes: [
    {
      key: 'blue',
      label_ms: 'Biru',
      label_en: 'Blue',
      colors: {
        primary: '#2563EB',
        secondary: '#1E40AF',
        accent: '#DBEAFE',
        background: '#F8FAFF',
        surface: '#FFFFFF',
        text: '#0F172A',
      },
    },
    {
      key: 'gold',
      label_ms: 'Emas',
      label_en: 'Gold',
      colors: {
        primary: '#A16207',
        secondary: '#713F12',
        accent: '#FEF9C3',
        background: '#FFFDF5',
        surface: '#FFFFFF',
        text: '#1C1917',
      },
    },
  ],
  fonts: [
    {
      key: 'bebas-neue__barlow',
      heading: 'Bebas Neue',
      body: 'Barlow',
      vibe: 'Bold, energetic',
      business_type: 'gym',
    },
  ],
  styles: [],
};

const CURRENT = {
  palette: { primary: '#A16207' },
  palette_key: 'gold',
  fonts: { heading: 'Lora', body: 'Nunito' },
  text_contrast: 12.1,
  source: 'storage',
};

function renderPanel(props: Partial<React.ComponentProps<typeof DesignStudioPanel>> = {}) {
  const onHtmlChange = vi.fn();
  render(
    <DesignStudioPanel
      websiteId="ws-1"
      isPublished
      onHtmlChange={onHtmlChange}
      {...props}
    />
  );
  return { onHtmlChange };
}

beforeEach(() => {
  applyTheme.mockReset();
  fetchDesignOptions.mockReset().mockResolvedValue(OPTIONS);
  fetchCurrentTheme.mockReset().mockResolvedValue(CURRENT);
  fetchPosterHtml
    .mockReset()
    .mockResolvedValue('<!DOCTYPE html><html><body>Poster</body></html>');
  // Shared across tests via the module mock — clear so a toast assertion
  // cannot pass on a call made by an earlier test.
  vi.mocked(toast).mockClear();
  vi.mocked(toast.success).mockClear();
  vi.mocked(toast.error).mockClear();
  applyTheme.mockResolvedValue({
    success: true,
    changed: true,
    message: 'Tema laman web dikemas kini.',
    palette_key: 'blue',
    palette: { primary: '#2563EB' },
    fonts: {},
    live_site_updated: true,
    html_content: '<html>repainted</html>',
  });
});

afterEach(cleanup);

describe('DesignStudioPanel', () => {
  it('states plainly that a repaint is free', async () => {
    renderPanel();
    expect(screen.getByText('Percuma')).toBeDefined();
    expect(screen.getByText(/tiada kredit digunakan/i)).toBeDefined();
  });

  it('renders a swatch per palette once the catalogue loads', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('palette-blue')).toBeDefined());
    expect(screen.getByTestId('palette-gold')).toBeDefined();
  });

  it('marks the palette the site is already wearing as active', async () => {
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId('palette-gold').getAttribute('aria-pressed')).toBe(
        'true'
      )
    );
    expect(screen.getByTestId('palette-blue').getAttribute('aria-pressed')).toBe(
      'false'
    );
  });

  it('applies a palette and hands the repainted html back to the editor', async () => {
    const { onHtmlChange } = renderPanel();
    await waitFor(() => screen.getByTestId('palette-blue'));

    fireEvent.click(screen.getByTestId('palette-blue'));

    await waitFor(() => expect(applyTheme).toHaveBeenCalled());
    expect(applyTheme.mock.calls[0][1]).toEqual({
      color_mode: 'light',
      palette: 'blue',
    });
    await waitFor(() =>
      expect(onHtmlChange).toHaveBeenCalledWith('<html>repainted</html>')
    );
  });

  it('shuffle asks the backend for the next palette', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('shuffle-design'));

    fireEvent.click(screen.getByTestId('shuffle-design'));

    await waitFor(() => expect(applyTheme).toHaveBeenCalled());
    expect(applyTheme.mock.calls[0][1]).toEqual({
      color_mode: 'light',
      shuffle: true,
    });
  });

  it('dark mode reloads the catalogue in dark and sends the mode through', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('palette-blue'));

    fireEvent.click(screen.getByText('🌙 Gelap'));
    await waitFor(() => expect(fetchDesignOptions).toHaveBeenCalledWith('dark'));

    fireEvent.click(screen.getByTestId('palette-blue'));
    await waitFor(() => expect(applyTheme).toHaveBeenCalled());
    expect(applyTheme.mock.calls[0][1].color_mode).toBe('dark');
  });

  it('shows the current font pairing and swaps on click', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByText(/Lora \/ Nunito/)).toBeDefined());

    fireEvent.click(screen.getByText(/🔤 Font/));
    const fontButton = await screen.findByTestId('font-bebas-neue__barlow');
    fireEvent.click(fontButton);

    await waitFor(() => expect(applyTheme).toHaveBeenCalled());
    expect(applyTheme.mock.calls[0][1].font_key).toBe('bebas-neue__barlow');
  });

  it('does not touch the editor buffer when nothing changed', async () => {
    applyTheme.mockResolvedValue({
      success: true,
      changed: false,
      message: 'Tiada perubahan.',
      palette_key: 'blue',
      palette: {},
      fonts: {},
      live_site_updated: false,
    });
    const { onHtmlChange } = renderPanel();
    await waitFor(() => screen.getByTestId('palette-blue'));

    fireEvent.click(screen.getByTestId('palette-blue'));
    await waitFor(() => expect(applyTheme).toHaveBeenCalled());
    expect(onHtmlChange).not.toHaveBeenCalled();
  });

  it('surfaces a backend failure instead of pretending it worked', async () => {
    applyTheme.mockRejectedValue(
      new Error('Laman web ini perlu dijana semula sebelum warnanya boleh ditukar.')
    );
    const { onHtmlChange } = renderPanel();
    await waitFor(() => screen.getByTestId('palette-blue'));

    fireEvent.click(screen.getByTestId('palette-blue'));

    await waitFor(() =>
      expect(screen.getByText(/perlu dijana semula/i)).toBeDefined()
    );
    expect(onHtmlChange).not.toHaveBeenCalled();
  });

  it('offers the QR poster only for a published site', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('open-qr-poster')).toBeDefined());

    cleanup();
    renderPanel({ isPublished: false });
    await waitFor(() =>
      expect(screen.getByText(/Terbitkan laman web anda dahulu/i)).toBeDefined()
    );
    expect(screen.queryByTestId('open-qr-poster')).toBeNull();
  });

  it('fetches the poster with auth and writes it into the tab', async () => {
    // Regression: the poster endpoint is owner-only. Navigating a new tab
    // straight at the URL sends no Authorization header and comes back 401,
    // which is exactly what happened in production.
    const tab = fakeTab();
    const openSpy = vi.fn(() => tab);
    vi.stubGlobal('open', openSpy);
    renderPanel();
    await waitFor(() => screen.getByTestId('open-qr-poster'));

    fireEvent.change(screen.getByLabelText('Nombor meja'), {
      target: { value: '7' },
    });
    fireEvent.click(screen.getByTestId('open-qr-poster'));

    await waitFor(() => expect(fetchPosterHtml).toHaveBeenCalled());
    // The tab is opened blank — never navigated at the protected URL.
    expect(openSpy).toHaveBeenCalledWith('', '_blank');
    expect(fetchPosterHtml.mock.calls[0][1]).toEqual({ table: '7' });
    expect(fetchPosterHtml.mock.calls[0][2]).toBe('tok-123');
    await waitFor(() => expect(tab.written.join('')).toContain('Poster'));
    vi.unstubAllGlobals();
  });

  it('omits the table number when the field is left blank', async () => {
    const tab = fakeTab();
    vi.stubGlobal('open', vi.fn(() => tab));
    renderPanel();
    await waitFor(() => screen.getByTestId('open-qr-poster'));

    fireEvent.click(screen.getByTestId('open-qr-poster'));

    await waitFor(() => expect(fetchPosterHtml).toHaveBeenCalled());
    expect(fetchPosterHtml.mock.calls[0][1]).toEqual({ table: undefined });
    vi.unstubAllGlobals();
  });

  it('closes the blank tab and reports when the poster fails', async () => {
    fetchPosterHtml.mockRejectedValue(
      new Error('Terbitkan laman web anda dahulu untuk menjana kod QR.')
    );
    const tab = fakeTab();
    vi.stubGlobal('open', vi.fn(() => tab));
    renderPanel();
    await waitFor(() => screen.getByTestId('open-qr-poster'));

    fireEvent.click(screen.getByTestId('open-qr-poster'));

    // No blank tab left sitting there looking like it is still loading.
    await waitFor(() => expect(tab.close).toHaveBeenCalled());
    expect(screen.getByText(/Terbitkan laman web anda dahulu/i)).toBeDefined();
  });

  it('tells the merchant when the popup blocker ate the tab', async () => {
    vi.stubGlobal('open', vi.fn(() => null));
    renderPanel();
    await waitFor(() => screen.getByTestId('open-qr-poster'));

    fireEvent.click(screen.getByTestId('open-qr-poster'));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/pop-up/i))
    );
    // Nothing was fetched — there is nowhere to put it.
    expect(fetchPosterHtml).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it('renders an error banner when the catalogue cannot load', async () => {
    fetchDesignOptions.mockRejectedValue(new Error('Gagal memuatkan tema.'));
    renderPanel();
    await waitFor(() =>
      expect(screen.getByText('Gagal memuatkan tema.')).toBeDefined()
    );
  });
});
