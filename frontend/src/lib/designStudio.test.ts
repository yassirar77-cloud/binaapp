import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  applyTheme,
  fetchCurrentTheme,
  fetchDesignOptions,
  isActivePalette,
  normalizeHex,
  qrPosterUrl,
  readableTextOn,
  themeErrorMessage,
  type CurrentTheme,
  type PaletteOption,
} from './designStudio';

const OPTION: PaletteOption = {
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
};

describe('normalizeHex', () => {
  it('expands shorthand and uppercases', () => {
    expect(normalizeHex('#abc')).toBe('#AABBCC');
    expect(normalizeHex('2563eb')).toBe('#2563EB');
  });

  it('rejects anything that is not a hex colour', () => {
    for (const bad of ['', null, undefined, 'blue', '#12', 'rgb(1,2,3)']) {
      expect(normalizeHex(bad as string)).toBeNull();
    }
  });
});

describe('readableTextOn', () => {
  it('picks white on a dark brand colour', () => {
    expect(readableTextOn('#1E3A8A')).toBe('#FFFFFF');
  });

  it('picks near-black on a pale brand colour', () => {
    expect(readableTextOn('#FDE047')).toBe('#111827');
    expect(readableTextOn('#FFFFFF')).toBe('#111827');
  });

  it('falls back to near-black for an unparseable colour', () => {
    expect(readableTextOn('not-a-colour')).toBe('#111827');
  });
});

describe('isActivePalette', () => {
  it('matches on the palette key when the backend resolved one', () => {
    const current = { palette_key: 'blue', palette: {} } as CurrentTheme;
    expect(isActivePalette(OPTION, current)).toBe(true);
  });

  it('falls back to comparing the primary colour', () => {
    const current = {
      palette_key: null,
      palette: { primary: '#2563eb' },
    } as CurrentTheme;
    expect(isActivePalette(OPTION, current)).toBe(true);
  });

  it('is false for a different palette', () => {
    const current = { palette_key: 'gold', palette: {} } as CurrentTheme;
    expect(isActivePalette(OPTION, current)).toBe(false);
  });

  it('is false before the current theme has loaded', () => {
    expect(isActivePalette(OPTION, null)).toBe(false);
  });
});

describe('themeErrorMessage', () => {
  it('explains an unrepaintable page in Malay', () => {
    expect(themeErrorMessage(422, { error: 'no_balanced_html_base' })).toContain(
      'jana semula'
    );
  });

  it('maps auth failures to a re-login prompt', () => {
    expect(themeErrorMessage(401)).toContain('log masuk');
    expect(themeErrorMessage(403)).toContain('log masuk');
  });

  it('has a generic fallback', () => {
    expect(themeErrorMessage(500)).toBe('Gagal menukar tema. Cuba lagi.');
  });
});

describe('qrPosterUrl', () => {
  it('builds a plain poster url', () => {
    expect(qrPosterUrl('ws-1')).toMatch(/\/api\/v1\/websites\/ws-1\/qr-poster\.html$/);
  });

  it('carries the table number through', () => {
    expect(qrPosterUrl('ws-1', { table: '5' })).toContain('table=5');
  });

  it('carries the language through', () => {
    expect(qrPosterUrl('ws-1', { language: 'en' })).toContain('language=en');
  });
});

describe('API calls', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function ok(body: unknown) {
    return { ok: true, status: 200, json: async () => body };
  }

  it('fetchDesignOptions asks for the requested colour mode', async () => {
    fetchMock.mockResolvedValue(ok({ palettes: [OPTION], fonts: [], styles: [] }));
    const options = await fetchDesignOptions('dark');
    expect(fetchMock.mock.calls[0][0]).toContain('color_mode=dark');
    expect(options.palettes).toHaveLength(1);
  });

  it('fetchDesignOptions tolerates a response with missing arrays', async () => {
    fetchMock.mockResolvedValue(ok({}));
    const options = await fetchDesignOptions();
    expect(options).toEqual({ palettes: [], fonts: [], styles: [] });
  });

  it('fetchCurrentTheme sends the bearer token', async () => {
    fetchMock.mockResolvedValue(ok({ palette: {}, palette_key: null }));
    await fetchCurrentTheme('ws-1', 'tok-123');
    const init = fetchMock.mock.calls[0][1];
    expect(init.headers.Authorization).toBe('Bearer tok-123');
  });

  it('applyTheme PATCHes the requested palette', async () => {
    fetchMock.mockResolvedValue(ok({ success: true, changed: true }));
    await applyTheme('ws-1', { palette: 'blue' }, 'tok');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/v1/websites/ws-1/theme');
    expect(init.method).toBe('PATCH');
    expect(JSON.parse(init.body)).toEqual({ palette: 'blue' });
  });

  it('applyTheme surfaces a structured backend error', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: { error: 'no_balanced_html_base' } }),
    });
    await expect(applyTheme('ws-1', { palette: 'blue' }, 'tok')).rejects.toThrow(
      /jana semula/
    );
  });

  it('applyTheme survives a non-JSON error body', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('not json');
      },
    });
    await expect(applyTheme('ws-1', { shuffle: true }, 'tok')).rejects.toThrow(
      /Gagal menukar tema/
    );
  });
});
