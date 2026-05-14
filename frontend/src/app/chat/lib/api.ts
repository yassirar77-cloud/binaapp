// /chat — API client for owner chat inbox.
// Mirrors the auth + authFetch pattern from /pesanan/lib/api.ts:
// ensureValidToken first (refresh-aware), Supabase session as fallback.
// Surfaces Malay error text from the API `detail` field when present.

import { supabase, ensureValidToken } from '@/lib/supabase';
import type {
  Conversation,
  ConversationDetail,
  Website,
  VerifyPaymentResponse,
} from './types';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

async function getToken(): Promise<string> {
  const validToken = await ensureValidToken();
  if (validToken) return validToken;
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) return data.session.access_token;
  }
  throw new ApiError('Tidak log masuk', 401);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function authFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = await getToken();
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(opts.headers || {}),
      },
    });
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : 'Network error',
      0,
    );
  }

  if (res.status === 204) {
    return null as unknown as T;
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail || `HTTP ${res.status}`, res.status);
  }

  return (await res.json()) as T;
}

// ----- Public API -----

interface ConversationsResponse {
  conversations: Conversation[];
}

/** GET /api/v1/chat/conversations returns `{conversations: [...]}`;
 *  we unwrap to `Conversation[]` so callers don't have to. */
export async function getConversations(
  websiteIds?: string[],
): Promise<Conversation[]> {
  const params = new URLSearchParams();
  if (websiteIds && websiteIds.length > 0) {
    params.set('website_ids', websiteIds.join(','));
  }
  const qs = params.toString();
  const path = qs
    ? `/api/v1/chat/conversations?${qs}`
    : '/api/v1/chat/conversations';
  const res = await authFetch<ConversationsResponse>(path);
  return res?.conversations ?? [];
}

/** GET /api/v1/chat/conversations/{id} returns `{conversation, messages, participants}`.
 *  Caller typically only needs `.conversation` (for header/order_status); the
 *  messages are streamed via WebSocket inside BinaChat. */
export function getConversation(
  conversationId: string,
): Promise<ConversationDetail> {
  return authFetch<ConversationDetail>(
    `/api/v1/chat/conversations/${conversationId}`,
  );
}

/** GET /api/v1/websites/ — normalized to expose `.name`. */
export async function getWebsites(): Promise<Website[]> {
  const raw = await authFetch<Array<Website & { business_name?: string }>>(
    '/api/v1/websites/',
  );
  return (raw ?? []).map((w) => ({
    ...w,
    name: w.name ?? w.business_name,
  }));
}

/** POST /api/v1/chat/messages/mark-read — mark inbound messages as read. */
export function markMessagesRead(conversationId: string): Promise<unknown> {
  return authFetch('/api/v1/chat/messages/mark-read', {
    method: 'POST',
    body: JSON.stringify({ conversation_id: conversationId }),
  });
}

/** POST /api/v1/chat/conversations/{id}/close. */
export function closeConversation(conversationId: string): Promise<unknown> {
  return authFetch(`/api/v1/chat/conversations/${conversationId}/close`, {
    method: 'POST',
  });
}

/** POST /api/v1/chat/messages/{id}/verify-payment — owner verifies a payment
 *  proof. Backend asserts the message belongs to a website owned by the caller. */
export function verifyPayment(
  messageId: string,
): Promise<VerifyPaymentResponse> {
  return authFetch<VerifyPaymentResponse>(
    `/api/v1/chat/messages/${messageId}/verify-payment`,
    { method: 'POST' },
  );
}
