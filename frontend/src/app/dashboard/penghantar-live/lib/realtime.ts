// Penghantar Live — Supabase Realtime subscription helper.
//
// Migration 002 adds public.delivery_orders and migration 029 adds
// public.riders to the supabase_realtime publication, so any INSERT/UPDATE/
// DELETE filtered by website_id is pushed within ~1s of the DB write. The
// owner page subscribes when an outlet is selected and unsubscribes on outlet
// change / unmount.
//
// We subscribe to BOTH tables on one channel:
//   - riders: GPS pings + online/offline transitions (high frequency).
//   - delivery_orders: new orders + status changes. A freshly-placed order is
//     inserted unassigned (rider_id NULL, status 'pending'); without this
//     subscription the dashboard only learned of it on the next poll — and the
//     poll is paused while realtime is up, so new orders could sit unseen.

import { supabase } from '@/lib/supabase';

export type RealtimeStatus = 'subscribed' | 'closed' | 'error' | 'connecting';

export interface RealtimeHandle {
  unsubscribe: () => void;
}

export function subscribeToLive(
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
    .channel(`phl-live:${websiteId}`)
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
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'delivery_orders',
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
