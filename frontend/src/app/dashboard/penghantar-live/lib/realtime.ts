// Penghantar Live — Supabase Realtime subscription helper.
//
// The migration 029 publication adds public.riders to supabase_realtime, so
// any UPDATE/INSERT/DELETE filtered by website_id is pushed within ~1s of the
// DB write. The owner page subscribes when an outlet is selected and unsub-
// scribes on outlet change / unmount.
//
// We do NOT subscribe to delivery_orders here — order status changes are
// lower-frequency and the 15s polling fallback covers them. If owners report
// stale order state, switch on a second channel.

import { supabase } from '@/lib/supabase';

export type RealtimeStatus = 'subscribed' | 'closed' | 'error' | 'connecting';

export interface RealtimeHandle {
  unsubscribe: () => void;
}

export function subscribeToRiders(
  websiteId: string,
  onChange: () => void,
  onStatusChange?: (status: RealtimeStatus) => void,
): RealtimeHandle {
  if (!supabase) {
    // Supabase not configured in env — caller falls back to polling.
    return { unsubscribe: () => {} };
  }
  const client = supabase;

  const channel = client
    .channel(`phl-riders:${websiteId}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'riders',
        filter: `website_id=eq.${websiteId}`,
      },
      () => onChange(),
    )
    .subscribe((status) => {
      if (!onStatusChange) return;
      // supabase-js statuses: SUBSCRIBED | CHANNEL_ERROR | TIMED_OUT | CLOSED
      if (status === 'SUBSCRIBED') onStatusChange('subscribed');
      else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT')
        onStatusChange('error');
      else if (status === 'CLOSED') onStatusChange('closed');
      else onStatusChange('connecting');
    });

  return {
    unsubscribe: () => {
      client.removeChannel(channel);
    },
  };
}
