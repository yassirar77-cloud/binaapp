/**
 * runHeroVideoJob — the create page's start-and-wait runner.
 *
 * The lifecycle it must get right: start → early first poll → poll on the
 * server's interval while processing/storing → resolve with the terminal
 * job (which carries html_content on success) → stop when asked to.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { runHeroVideoJob, type HeroVideoJob } from './heroVideo';

const WS = 'ws-1';

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

function job(overrides: Partial<HeroVideoJob>): HeroVideoJob {
  return {
    job_id: 'job-1',
    status: 'processing',
    error: null,
    video_url: null,
    poster_url: null,
    applied: false,
    live_site_updated: false,
    elapsed_seconds: 0,
    ...overrides,
  };
}

const START_OK = {
  job_id: 'job-1',
  status: 'processing',
  poll_interval_seconds: 8,
  prompt: 'p',
  message: 'Video sedang dijana…',
};

describe('runHeroVideoJob', () => {
  const fetchMock = vi.fn();
  const sleeps: number[] = [];
  const sleep = async (ms: number) => {
    sleeps.push(ms);
  };

  beforeEach(() => {
    fetchMock.mockReset();
    sleeps.length = 0;
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('starts the job, polls until completed and returns the patched html', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(202, START_OK))
      .mockResolvedValueOnce(jsonResponse(200, job({ status: 'processing', elapsed_seconds: 3 })))
      .mockResolvedValueOnce(jsonResponse(200, job({ status: 'storing', elapsed_seconds: 40 })))
      .mockResolvedValueOnce(
        jsonResponse(
          200,
          job({
            status: 'completed',
            applied: true,
            live_site_updated: true,
            video_url: 'https://res.cloudinary.com/x/video/upload/v.mp4',
            html_content: '<html>with video</html>',
          })
        )
      );
    const seen: string[] = [];

    const result = await runHeroVideoJob(
      WS,
      { style: 'cinematic' },
      'tok',
      { sleep, onUpdate: (j) => seen.push(j.status) }
    );

    expect(result?.status).toBe('completed');
    expect(result?.html_content).toBe('<html>with video</html>');
    expect(seen).toEqual(['processing', 'processing', 'storing', 'completed']);

    // Start call shape.
    const [startUrl, startInit] = fetchMock.mock.calls[0];
    expect(String(startUrl)).toMatch(/\/api\/v1\/websites\/ws-1\/hero-video\/generate$/);
    expect(startInit.method).toBe('POST');
    expect(JSON.parse(startInit.body)).toEqual({ style: 'cinematic' });
    expect(startInit.headers.Authorization).toBe('Bearer tok');

    // Polls hit the job endpoint.
    expect(String(fetchMock.mock.calls[1][0])).toMatch(/\/hero-video\/jobs\/job-1$/);

    // Early first poll (3s), then the server's 8s cadence between active polls.
    expect(sleeps).toEqual([3000, 8000, 8000]);
  });

  it('returns the failed job with its error code intact', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(202, START_OK))
      .mockResolvedValueOnce(jsonResponse(200, job({ status: 'failed', error: 'zai_failed' })));

    const result = await runHeroVideoJob(WS, {}, 'tok', { sleep });
    expect(result?.status).toBe('failed');
    expect(result?.error).toBe('zai_failed');
  });

  it('throws a Malay message when the start is refused', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(403, { detail: { error: 'plan_not_allowed' } })
    );
    await expect(runHeroVideoJob(WS, {}, 'tok', { sleep })).rejects.toThrow(/pelan|plan/i);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('stops polling and resolves null when asked to stop', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(202, START_OK))
      .mockResolvedValue(jsonResponse(200, job({ status: 'processing' })));
    let polls = 0;
    const result = await runHeroVideoJob(WS, {}, 'tok', {
      sleep,
      shouldStop: () => polls >= 2,
      onUpdate: (j) => {
        if (j.elapsed_seconds === 0 && j.status === 'processing') polls += 1;
      },
    });
    expect(result).toBeNull();
    // start + at most a couple of polls before the stop was honoured
    expect(fetchMock.mock.calls.length).toBeLessThanOrEqual(4);
  });

  it('uses a fresh token for each poll when getToken is supplied', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(202, START_OK))
      .mockResolvedValueOnce(jsonResponse(200, job({ status: 'completed', applied: true })));
    await runHeroVideoJob(WS, {}, 'start-tok', {
      sleep,
      getToken: async () => 'fresh-tok',
    });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer start-tok');
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer fresh-tok');
  });

  it('gives up with a timeout error once maxWaitSeconds is exceeded', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(202, START_OK))
      .mockResolvedValue(jsonResponse(200, job({ status: 'processing' })));
    const result = await runHeroVideoJob(WS, {}, 'tok', { sleep, maxWaitSeconds: -1 });
    expect(result?.status).toBe('failed');
    expect(result?.error).toBe('timeout');
  });
});
