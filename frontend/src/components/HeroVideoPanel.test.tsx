// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import toast from 'react-hot-toast';
import HeroVideoPanel from './HeroVideoPanel';

vi.mock('react-hot-toast', () => {
  const toast = Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
  });
  return { default: toast, toast };
});

vi.mock('@/lib/supabase', () => ({
  getApiAuthToken: vi.fn(async () => 'tok-123'),
  getCurrentUser: vi.fn(async () => ({ id: 'user-1', email: 'u@x.my' })),
}));

const fetchHeroVideoOptions = vi.fn();
const fetchHeroVideoState = vi.fn();
const startHeroVideo = vi.fn();
const pollHeroVideoJob = vi.fn();
const updateHeroVideoLook = vi.fn();
const removeHeroVideo = vi.fn();
const startHeroVideoPurchase = vi.fn(async (..._args: unknown[]) => undefined);

vi.mock('@/lib/heroVideo', async () => {
  const actual = await vi.importActual<typeof import('@/lib/heroVideo')>('@/lib/heroVideo');
  return {
    ...actual,
    fetchHeroVideoOptions: (...args: unknown[]) => fetchHeroVideoOptions(...args),
    fetchHeroVideoState: (...args: unknown[]) => fetchHeroVideoState(...args),
    startHeroVideo: (...args: unknown[]) => startHeroVideo(...args),
    pollHeroVideoJob: (...args: unknown[]) => pollHeroVideoJob(...args),
    updateHeroVideoLook: (...args: unknown[]) => updateHeroVideoLook(...args),
    removeHeroVideo: (...args: unknown[]) => removeHeroVideo(...args),
    startHeroVideoPurchase: (...args: unknown[]) => startHeroVideoPurchase(...args),
  };
});

const OPTIONS = {
  model: 'cogvideox-3',
  duration_seconds: 5,
  durations: [5, 10],
  poll_interval_seconds: 1,
  styles: [
    { key: 'cinematic', label_ms: 'Sinematik', label_en: 'Cinematic' },
    { key: 'ambient', label_ms: 'Tenang', label_en: 'Ambient' },
  ],
  overlays: ['dark', 'light', 'none'],
  text_modes: ['auto', 'light', 'dark', 'keep'],
};

const SETTINGS = {
  video_url: 'https://res.cloudinary.com/x/video/upload/v1/hero.mp4',
  poster_url: 'https://res.cloudinary.com/x/video/upload/v1/hero.jpg',
  overlay: 'dark' as const,
  overlay_opacity: 0.45,
  text_mode: 'auto' as const,
  show_on_mobile: true,
};

function cleanState(overrides: Record<string, unknown> = {}) {
  return {
    has_video: false,
    settings: null,
    hero_found: true,
    hero_match: 'id',
    allowed: true,
    free_access: true,
    credits: 0,
    price_rm: 5,
    addon_type: 'hero_video',
    job: null,
    poll_interval_seconds: 1,
    source: 'db',
    ...overrides,
  };
}

function job(status: string, extra: Record<string, unknown> = {}) {
  return {
    job_id: 'job-1',
    status,
    error: null,
    video_url: null,
    poster_url: null,
    applied: false,
    live_site_updated: false,
    elapsed_seconds: 0,
    ...extra,
  };
}

describe('HeroVideoPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    fetchHeroVideoOptions.mockResolvedValue(OPTIONS);
    fetchHeroVideoState.mockResolvedValue(cleanState());
  });

  afterEach(() => {
    cleanup();
  });

  it('renders nothing when the server says the feature is off', async () => {
    fetchHeroVideoOptions.mockResolvedValue(null);
    const { container } = render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    await waitFor(() => expect(fetchHeroVideoOptions).toHaveBeenCalled());
    expect(container.querySelector('[data-testid="hero-video-panel"]')).toBeNull();
    expect(fetchHeroVideoState).not.toHaveBeenCalled();
  });

  it('loads the presets and the current state', async () => {
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    expect(await screen.findByTestId('video-style-cinematic')).toBeTruthy();
    expect(screen.getByTestId('video-style-ambient').textContent).toBe('Tenang');
    expect(fetchHeroVideoState).toHaveBeenCalledWith('ws-1', 'tok-123');
    expect(screen.queryByTestId('hero-video-current')).toBeNull();
    expect(screen.getByTestId('generate-hero-video').textContent).toContain('Jana video latar');
  });

  it('starts a job with the chosen style and look, then applies the clip when it lands', async () => {
    const onHtmlChange = vi.fn();
    startHeroVideo.mockResolvedValue({
      job_id: 'job-1',
      status: 'processing',
      poll_interval_seconds: 1,
      prompt: 'p',
      message: 'Video sedang dijana.',
    });
    pollHeroVideoJob
      .mockResolvedValueOnce(job('processing'))
      .mockResolvedValueOnce(
        job('completed', {
          applied: true,
          live_site_updated: true,
          video_url: SETTINGS.video_url,
          poster_url: SETTINGS.poster_url,
          settings: { ...SETTINGS, overlay: 'light' },
          html_content: '<html>with video</html>',
          message: 'Video latar hero telah dipasang.',
        })
      );

    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={onHtmlChange} />);
    fireEvent.click(await screen.findByTestId('video-style-ambient'));
    fireEvent.click(screen.getByTestId('overlay-light'));
    fireEvent.click(screen.getByTestId('generate-hero-video'));

    await waitFor(() => expect(startHeroVideo).toHaveBeenCalled());
    expect(startHeroVideo.mock.calls[0][1]).toMatchObject({
      style: 'ambient',
      overlay: 'light',
      overlay_opacity: 0.45,
      show_on_mobile: true,
    });
    // No clip yet → the overlay click was a preference, not a PATCH.
    expect(updateHeroVideoLook).not.toHaveBeenCalled();

    expect(await screen.findByTestId('hero-video-progress')).toBeTruthy();
    await waitFor(() => expect(onHtmlChange).toHaveBeenCalledWith('<html>with video</html>'), {
      timeout: 5000,
    });
    expect(pollHeroVideoJob).toHaveBeenCalledWith('ws-1', 'job-1', 'tok-123');
    expect(toast.success).toHaveBeenCalledWith('Video latar hero telah dipasang.');
    expect(screen.queryByTestId('hero-video-progress')).toBeNull();
    expect(screen.getByTestId('hero-video-current')).toBeTruthy();
    expect(screen.getByTestId('overlay-light').getAttribute('aria-pressed')).toBe('true');
  });

  it('keeps the job alive through a dropped poll and still applies the clip', async () => {
    const onHtmlChange = vi.fn();
    startHeroVideo.mockResolvedValue({
      job_id: 'job-1',
      status: 'processing',
      poll_interval_seconds: 1,
      prompt: 'p',
      message: 'Video sedang dijana.',
    });
    pollHeroVideoJob
      // The phone's connection drops for one poll — fetch throws before any
      // response exists. This must NOT read as a failed job.
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(
        job('completed', {
          applied: true,
          live_site_updated: true,
          video_url: SETTINGS.video_url,
          poster_url: SETTINGS.poster_url,
          settings: SETTINGS,
          html_content: '<html>with video</html>',
          message: 'Video latar hero telah dipasang.',
        })
      );

    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={onHtmlChange} />);
    fireEvent.click(await screen.findByTestId('generate-hero-video'));

    // Malay notice, not the browser's raw text — and the job is still shown.
    expect(await screen.findByText(/Sambungan terputus/, {}, { timeout: 4000 })).toBeTruthy();
    expect(screen.queryByText('Failed to fetch')).toBeNull();
    expect(screen.getByTestId('hero-video-progress')).toBeTruthy();

    await waitFor(() => expect(onHtmlChange).toHaveBeenCalledWith('<html>with video</html>'), {
      timeout: 8000,
    });
    expect(pollHeroVideoJob).toHaveBeenCalledTimes(2);
    expect(toast.success).toHaveBeenCalledWith('Video latar hero telah dipasang.');
    expect(screen.queryByText(/Sambungan terputus/)).toBeNull();
    expect(screen.getByTestId('hero-video-current')).toBeTruthy();
  }, 15000);

  it('shows a Malay error when the job fails and leaves the page alone', async () => {
    const onHtmlChange = vi.fn();
    startHeroVideo.mockResolvedValue({ job_id: 'job-1', status: 'processing', poll_interval_seconds: 1, prompt: 'p', message: '' });
    pollHeroVideoJob.mockResolvedValue(job('failed', { error: 'generation_failed' }));

    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={onHtmlChange} />);
    fireEvent.click(await screen.findByTestId('generate-hero-video'));

    await waitFor(() => expect(toast.error).toHaveBeenCalled(), { timeout: 5000 });
    expect(toast.error).toHaveBeenCalledWith('AI gagal menjana video ini. Cuba gaya atau penerangan lain.');
    expect(onHtmlChange).not.toHaveBeenCalled();
    expect(screen.getByText(/AI gagal menjana video ini/)).toBeTruthy();
  });

  it('surfaces a start failure from the backend', async () => {
    startHeroVideo.mockRejectedValue(new Error('Had harian video untuk laman web ini telah dicapai. Cuba lagi esok.'));
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    fireEvent.click(await screen.findByTestId('generate-hero-video'));
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(screen.getByText(/Had harian video/)).toBeTruthy();
    expect(pollHeroVideoJob).not.toHaveBeenCalled();
  });

  it('resumes watching a job that is already in flight', async () => {
    fetchHeroVideoState.mockResolvedValue(cleanState({ job: job('processing', { elapsed_seconds: 40 }) }));
    pollHeroVideoJob.mockResolvedValue(job('processing', { elapsed_seconds: 41 }));
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    expect(await screen.findByTestId('hero-video-progress')).toBeTruthy();
    await waitFor(() => expect(pollHeroVideoJob).toHaveBeenCalledWith('ws-1', 'job-1', 'tok-123'), {
      timeout: 5000,
    });
    expect(startHeroVideo).not.toHaveBeenCalled();
    expect((screen.getByTestId('generate-hero-video') as HTMLButtonElement).disabled).toBe(true);
  });

  it('patches the look credit-free once a clip exists', async () => {
    const onHtmlChange = vi.fn();
    fetchHeroVideoState.mockResolvedValue(cleanState({ has_video: true, settings: SETTINGS }));
    updateHeroVideoLook.mockResolvedValue({
      success: true,
      changed: true,
      message: 'Tetapan video latar dikemas kini.',
      settings: { ...SETTINGS, overlay: 'none' },
      live_site_updated: true,
      html_content: '<html>none</html>',
    });

    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={onHtmlChange} />);
    expect(await screen.findByTestId('hero-video-current')).toBeTruthy();
    expect(screen.getByTestId('overlay-dark').getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(screen.getByTestId('overlay-none'));
    await waitFor(() => expect(updateHeroVideoLook).toHaveBeenCalledWith('ws-1', { overlay: 'none' }, 'tok-123'));
    expect(onHtmlChange).toHaveBeenCalledWith('<html>none</html>');
    expect(startHeroVideo).not.toHaveBeenCalled();
    expect(toast.success).toHaveBeenCalledWith('Tetapan video latar dikemas kini.');
  });

  it('removes the clip after confirmation', async () => {
    const onHtmlChange = vi.fn();
    fetchHeroVideoState.mockResolvedValue(cleanState({ has_video: true, settings: SETTINGS }));
    removeHeroVideo.mockResolvedValue({
      success: true,
      changed: true,
      message: 'Video latar hero telah dibuang.',
      live_site_updated: true,
      html_content: '<html>clean</html>',
    });
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={onHtmlChange} />);
    fireEvent.click(await screen.findByTestId('remove-hero-video'));
    await waitFor(() => expect(removeHeroVideo).toHaveBeenCalledWith('ws-1', 'tok-123'));
    expect(onHtmlChange).toHaveBeenCalledWith('<html>clean</html>');
    await waitFor(() => expect(screen.queryByTestId('hero-video-current')).toBeNull());
    confirmSpy.mockRestore();
  });

  it('does not remove when the merchant cancels the confirm', async () => {
    fetchHeroVideoState.mockResolvedValue(cleanState({ has_video: true, settings: SETTINGS }));
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    fireEvent.click(await screen.findByTestId('remove-hero-video'));
    expect(removeHeroVideo).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('disables generation when the account has no free access and no credit', async () => {
    fetchHeroVideoState.mockResolvedValue(
      cleanState({ allowed: false, free_access: false, credits: 0 })
    );
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    expect((await screen.findByTestId('hero-video-credits')).textContent).toContain('setiap klip');
    expect(screen.getByTestId('generate-hero-video').hasAttribute('disabled')).toBe(true);
  });

  it('disables generation when the page has no hero', async () => {
    fetchHeroVideoState.mockResolvedValue(cleanState({ hero_found: false, hero_match: '' }));
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    const button = (await screen.findByTestId('generate-hero-video')) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(screen.getByText(/Bahagian hero tidak dijumpai/)).toBeTruthy();
  });

  it('sells a RM5 credit when the account has none, and sends the merchant back to the editor', async () => {
    fetchHeroVideoState.mockResolvedValue(
      cleanState({ allowed: false, free_access: false, credits: 0, price_rm: 5 })
    );
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    const buy = await screen.findByTestId('buy-hero-video-credit');
    expect(buy.textContent).toContain('RM5');
    expect(screen.getByTestId('generate-hero-video').hasAttribute('disabled')).toBe(true);
    expect(screen.getByTestId('hero-video-credits').textContent).toContain('belum ada kredit');

    fireEvent.click(buy);
    await waitFor(() => expect(startHeroVideoPurchase).toHaveBeenCalled());
    expect(startHeroVideoPurchase.mock.calls[0]?.[0]).toMatchObject({
      userId: 'user-1',
      token: 'tok-123',
      returnTo: window.location.pathname,
    });
  });

  it('shows the credit balance and charges one credit per generation for paid accounts', async () => {
    fetchHeroVideoState.mockResolvedValue(
      cleanState({ allowed: true, free_access: false, credits: 2, price_rm: 5 })
    );
    render(<HeroVideoPanel websiteId="ws-1" onHtmlChange={vi.fn()} />);
    expect((await screen.findByTestId('hero-video-credits')).textContent).toContain('Baki kredit video: 2');
    expect(screen.getByTestId('generate-hero-video').textContent).toContain('(1 kredit)');
    expect(screen.getByTestId('generate-hero-video').hasAttribute('disabled')).toBe(false);
  });
});
