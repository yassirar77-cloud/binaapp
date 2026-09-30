import { NextRequest, NextResponse } from 'next/server';

/**
 * TikTok Login Kit redirect URI — https://binaapp.my/api/tiktok/callback
 * (and the www. variant; both are registered in the TikTok developer portal).
 *
 * TikTok sends the browser here with `code`, `scopes` and `state` (or
 * `error` + `error_description`). The code is exchanged by the backend, which
 * holds the client secret and the encrypted token store; to reach it with the
 * admin's own session we hand `code` and `state` to the admin page, which
 * POSTs them to /api/v1/social/tiktok/oauth/callback with its bearer token.
 * That way the state is checked against both the row we minted AND the
 * signed-in admin — no cookie has to survive the round trip through TikTok.
 *
 * The authorization code is single-use, expires in minutes and is useless
 * without the client secret; the admin page strips it from the URL as soon
 * as it has been consumed.
 */
export const dynamic = 'force-dynamic';

const ADMIN_PATH = '/admin/tiktok';

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const target = request.nextUrl.clone();
  target.pathname = ADMIN_PATH;
  target.search = '';

  const error = params.get('error');
  const code = params.get('code');
  const state = params.get('state');

  if (error) {
    target.searchParams.set('tiktok', 'error');
    target.searchParams.set('reason', error);
    const description = params.get('error_description');
    if (description) target.searchParams.set('description', description.slice(0, 300));
    return NextResponse.redirect(target, { status: 302 });
  }

  if (!code || !state) {
    target.searchParams.set('tiktok', 'error');
    target.searchParams.set('reason', 'missing_code_or_state');
    return NextResponse.redirect(target, { status: 302 });
  }

  target.searchParams.set('tiktok', 'callback');
  target.searchParams.set('code', code);
  target.searchParams.set('state', state);
  const scopes = params.get('scopes');
  if (scopes) target.searchParams.set('scopes', scopes);

  const res = NextResponse.redirect(target, { status: 302 });
  res.headers.set('Cache-Control', 'no-store');
  return res;
}
