'use client';

/**
 * The connected TikTok account — avatar, display name and @handle straight
 * from TikTok's user.info / creator_info, so a reviewer watching the demo
 * sees exactly which account will receive the post.
 */

import { Button } from '@/components/ui';
import type { TikTokAccount, TikTokConfig } from '@/lib/tiktok';

interface Props {
  config: TikTokConfig | null;
  account: TikTokAccount | null;
  connecting: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onRefresh: () => void;
}

export function TikTokAccountCard({ config, account, connecting, onConnect, onDisconnect, onRefresh }: Props) {
  const connected = !!account && account.status === 'connected';
  const needsReauth = !!account && account.status === 'reauth_required';

  return (
    <section className="rounded-2xl border border-ink-200 bg-white p-5 shadow-soft" aria-labelledby="tt-account-h">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0">
          {account?.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={account.avatar_url}
              alt={account.display_name ? `${account.display_name}'s TikTok avatar` : 'TikTok avatar'}
              className="h-16 w-16 rounded-full object-cover ring-2 ring-ink-100"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="h-16 w-16 rounded-full bg-ink-100 grid place-items-center text-2xl" aria-hidden>
              🎵
            </div>
          )}
          <div className="min-w-0">
            <h2 id="tt-account-h" className="text-xs font-semibold uppercase tracking-wide text-ink-500">
              TikTok account
            </h2>
            {account ? (
              <>
                <p className="text-lg font-bold text-ink-900 truncate">{account.display_name || 'TikTok creator'}</p>
                <p className="text-sm text-ink-600 truncate">
                  {account.username ? `@${account.username}` : `open_id ${account.open_id.slice(0, 10)}…`}
                </p>
              </>
            ) : (
              <p className="text-base text-ink-700">No TikTok account connected yet.</p>
            )}
            {account && (
              <p className="mt-1 text-xs text-ink-500">
                Permissions: {account.scopes.length ? account.scopes.join(', ') : '—'}
                {connected && account.access_token_expires_at && (
                  <> · token auto-refreshes (current one expires {new Date(account.access_token_expires_at).toLocaleString()})</>
                )}
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {connected && (
            <>
              <Button variant="ghost" size="sm" onClick={onRefresh}>
                Refresh profile
              </Button>
              <Button variant="danger" size="sm" onClick={onDisconnect}>
                Disconnect TikTok
              </Button>
            </>
          )}
          {!connected && (
            <Button onClick={onConnect} loading={connecting} disabled={!config?.configured}>
              {needsReauth ? 'Reconnect TikTok' : 'Connect TikTok'}
            </Button>
          )}
        </div>
      </div>

      {needsReauth && (
        <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800" role="alert">
          The stored TikTok permission is no longer valid ({account?.last_error || 'reauth_required'}). Reconnect to
          continue posting.
        </p>
      )}
      {config && !config.configured && (
        <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          TikTok is not configured on the backend. Set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET and
          TIKTOK_REDIRECT_URI on Render.
        </p>
      )}
      {!account && config?.configured && (
        <p className="mt-3 text-xs text-ink-500">
          You will be sent to TikTok to approve <strong>user.info.basic</strong>, <strong>video.upload</strong> and{' '}
          <strong>video.publish</strong>, then returned to this page. Redirect URI: <code>{config.redirect_uri}</code>
        </p>
      )}
    </section>
  );
}
