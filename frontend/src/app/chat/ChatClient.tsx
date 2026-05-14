'use client';

// /chat — main client wrapper. Owns conversation + filter state, polls every
// 30s, and renders DashboardHeader / TopBar / ConversationListPanel +
// ChatPanelWrapper for the selected conversation.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { getCurrentUser } from '@/lib/supabase';
import DashboardHeader from '@/components/dashboard-new/DashboardHeader';
import {
  ApiError,
  closeConversation,
  getConversations,
  getWebsites,
  verifyPayment,
} from './lib/api';
import type { Conversation, Message, TabKey, Website } from './lib/types';
import { POLL_INTERVAL_MS, SEARCH_DEBOUNCE_MS, TABS } from './lib/constants';
import { useIsMobile } from './lib/useIsMobile';
import TopBar from './components/TopBar';
import ConversationListPanel from './components/ConversationListPanel';
import ChatPanelWrapper from './components/ChatPanelWrapper';
import EmptyState, { type EmptyStateStat } from './components/EmptyState';
import VerifyPaymentModal from './components/VerifyPaymentModal';
import './chat.css';

export default function ChatClient() {
  const router = useRouter();

  // ----- Data -----
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [websites, setWebsites] = useState<Website[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [userName, setUserName] = useState('Pengguna');

  // ----- Filter state -----
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string | 'all'>('all');
  const [tab, setTab] = useState<TabKey>('all');
  const [searchQuery, setSearchQuery] = useState('');
  // Debounced mirror (collapses 300ms keystroke bursts).
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // ----- Selection -----
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  // Payment-verify modal target. BinaChat fires onVerifyPayment with a message
  // id; we resolve it to a Message and render <VerifyPaymentModal/>. Null hides.
  const [verifyModalForMessage, setVerifyModalForMessage] = useState<Message | null>(null);

  const isMobile = useIsMobile();

  // ----- Bookkeeping -----
  const mountedRef = useRef(true);
  // One-shot default-tab landing once first non-empty load resolves. After
  // that the user owns the tab selection — we don't fight their choice.
  const defaultTabAppliedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // ----- Toasts -----
  const reportSuccess = useCallback((msg: string) => {
    toast.success(msg, { duration: 3000 });
  }, []);

  const reportError = useCallback(
    (e: unknown, fallback: string, opts: { silent?: boolean } = {}) => {
      if (e instanceof ApiError && e.status === 401) {
        router.push('/login');
        return;
      }
      if (opts.silent) return;
      const msg =
        e instanceof ApiError && e.status === 0
          ? 'Tiada sambungan. Periksa internet anda.'
          : e instanceof Error && e.message
            ? e.message
            : fallback;
      toast.error(msg, { duration: 5000 });
    },
    [router],
  );

  // ----- Refresh -----
  const refreshConversations = useCallback(
    async (opts: { silent?: boolean } = {}) => {
      try {
        const list = await getConversations();
        if (!mountedRef.current) return;
        setConversations(list);
        setLastRefresh(new Date());
      } catch (e) {
        if (!mountedRef.current) return;
        reportError(e, 'Gagal muat chat. Sila cuba lagi.', {
          silent: opts.silent,
        });
      }
    },
    [reportError],
  );

  // User display name for DashboardHeader.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await getCurrentUser();
        if (cancelled || !user) return;
        const u = user as {
          user_metadata?: { full_name?: string };
          email?: string;
        };
        setUserName(
          u.user_metadata?.full_name || u.email?.split('@')[0] || 'Pengguna',
        );
      } catch {
        // Silent: keep default.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('binaapp_token');
      localStorage.removeItem('binaapp_user');
    }
    router.push('/');
  }, [router]);

  // Initial load — websites + conversations.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [ws, convs] = await Promise.all([
          getWebsites(),
          getConversations(),
        ]);
        if (cancelled) return;
        setWebsites(ws);
        setConversations(convs);
        setLastRefresh(new Date());
      } catch (e) {
        if (cancelled) return;
        reportError(e, 'Gagal muat chat. Sila refresh halaman.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reportError]);

  // Background polling — 30s, silent toasts so we don't spam on flaky network.
  useEffect(() => {
    const id = window.setInterval(() => {
      void refreshConversations({ silent: true });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [refreshConversations]);

  // Default tab landing — once on first non-loading render, jump to 'unread'
  // if any conversation has unread_owner > 0; else stay on 'all'. Doesn't
  // re-trigger after the user picks a tab.
  useEffect(() => {
    if (defaultTabAppliedRef.current) return;
    if (loading) return;
    defaultTabAppliedRef.current = true;
    const hasUnread = conversations.some((c) => (c.unread_owner ?? 0) > 0);
    if (hasUnread) setTab('unread');
  }, [loading, conversations]);

  // Auto-collapse 'all' down to the sole outlet once websites resolve, so the
  // outlet selector doesn't show a redundant "Semua" pill for single-outlet users.
  useEffect(() => {
    if (websites.length === 1 && selectedWebsiteId === 'all') {
      setSelectedWebsiteId(websites[0].id);
    }
  }, [websites, selectedWebsiteId]);

  // Search debounce.
  useEffect(() => {
    const t = window.setTimeout(
      () => setDebouncedSearch(searchQuery),
      SEARCH_DEBOUNCE_MS,
    );
    return () => window.clearTimeout(t);
  }, [searchQuery]);

  // ----- Derived -----

  const websiteLabelById = useMemo(() => {
    const m = new Map<string, string>();
    for (const w of websites) {
      m.set(w.id, w.name || w.business_name || 'Outlet');
    }
    return m;
  }, [websites]);

  const unreadTotal = useMemo(
    () =>
      conversations.reduce((sum, c) => sum + (c.unread_owner ?? 0), 0),
    [conversations],
  );

  // Filter chain: outlet -> tab -> search. Then sort by updated_at desc.
  const filteredConversations = useMemo(() => {
    const tabDef = TABS.find((t) => t.id === tab);
    const q = debouncedSearch.trim().toLowerCase();

    const matches = conversations.filter((c) => {
      if (
        selectedWebsiteId !== 'all' &&
        c.website_id !== selectedWebsiteId
      ) {
        return false;
      }
      if (tabDef && !tabDef.match(c)) return false;
      if (q) {
        const last = c.chat_messages?.[c.chat_messages.length - 1];
        const lastText =
          last?.message_text ||
          (last as any)?.content ||
          (last as any)?.message ||
          '';
        const hay = [
          c.customer_name,
          c.customer_phone,
          c.order_number,
          c.website_name,
          websiteLabelById.get(c.website_id),
          lastText,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    matches.sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
    return matches;
  }, [
    conversations,
    selectedWebsiteId,
    tab,
    debouncedSearch,
    websiteLabelById,
  ]);

  const selectedConversation = useMemo(
    () =>
      selectedConversationId
        ? conversations.find((c) => c.id === selectedConversationId) ?? null
        : null,
    [conversations, selectedConversationId],
  );

  // Drop stale selection if a poll refresh removed the selected conversation.
  useEffect(() => {
    if (selectedConversationId && !selectedConversation) {
      setSelectedConversationId(null);
    }
  }, [selectedConversationId, selectedConversation]);

  // ----- Handlers -----

  const handleSelectConversation = useCallback((id: string) => {
    setSelectedConversationId(id);
  }, []);

  const handleBackToList = useCallback(() => {
    setSelectedConversationId(null);
  }, []);

  const handleRefresh = useCallback(async () => {
    await refreshConversations();
  }, [refreshConversations]);

  const handleCopyPhone = useCallback(
    async (phone: string) => {
      try {
        if (navigator?.clipboard?.writeText) {
          await navigator.clipboard.writeText(phone);
          reportSuccess('Nombor telefon disalin');
        } else {
          toast('Salinan tidak tersedia', { duration: 3000 });
        }
      } catch {
        toast.error('Gagal salin nombor', { duration: 3000 });
      }
    },
    [reportSuccess],
  );

  const handleCloseConversation = useCallback(
    async (id: string) => {
      try {
        await closeConversation(id);
        reportSuccess('Chat ditutup');
        await refreshConversations();
      } catch (e) {
        reportError(e, 'Gagal tutup chat. Sila cuba lagi.');
      }
    },
    [refreshConversations, reportSuccess, reportError],
  );

  // BinaChat fires this with the payment message id; we look it up in the
  // selected conversation's preview window and open the modal. Fallback to a
  // bare {id} stub if the message has scrolled out of the preview — the modal
  // can still show order_id from metadata once it loads, and the verify call
  // only needs the id.
  const handleVerifyPayment = useCallback(
    (messageId: string) => {
      const conv = conversations.find((c) => c.id === selectedConversationId);
      const msg =
        conv?.chat_messages?.find((m) => m.id === messageId) ??
        ({ id: messageId } as Message);
      setVerifyModalForMessage(msg);
    },
    [conversations, selectedConversationId],
  );

  const handleCloseVerifyModal = useCallback(() => {
    setVerifyModalForMessage(null);
  }, []);

  // Owner confirms the payment. On success: toast + close modal + refetch
  // conversations so the verified state propagates everywhere. On failure:
  // toast + return false so the modal stays open and the user can retry.
  const handleConfirmVerify = useCallback(
    async (messageId: string): Promise<boolean> => {
      try {
        await verifyPayment(messageId);
        const orderTail =
          verifyModalForMessage?.metadata?.order_id?.slice?.(-8);
        reportSuccess(
          orderTail
            ? `Pembayaran disahkan untuk pesanan #${orderTail}`
            : 'Pembayaran disahkan',
        );
        setVerifyModalForMessage(null);
        void refreshConversations({ silent: true });
        return true;
      } catch (e) {
        reportError(e, 'Gagal sahkan pembayaran. Sila cuba lagi.');
        return false;
      }
    },
    [verifyModalForMessage, refreshConversations, reportSuccess, reportError],
  );

  // Owner display name passed to BinaChat (shown to customer + rider as the
  // sender of owner messages). Prefer the first website's business_name —
  // matches the legacy OwnerChatDashboard fallback chain.
  const ownerName = useMemo(() => {
    const first = websites[0];
    return (
      first?.business_name || first?.name || userName || 'Pemilik Kedai'
    );
  }, [websites, userName]);

  // Stats for the no-selection empty state. "Payment pending" is an
  // approximation — only the last 10 messages per conversation come back in
  // the preview window, so older pending proofs aren't counted. Good enough
  // for an at-a-glance number; a precise count would need a dedicated query.
  const noSelectionStats: EmptyStateStat[] = useMemo(() => {
    let activeOrders = 0;
    let paymentPending = 0;
    for (const c of conversations) {
      if (c.order_id && c.status === 'active') activeOrders++;
      const msgs = c.chat_messages ?? [];
      for (const m of msgs) {
        if (
          m.message_type === 'payment' &&
          m.metadata?.status === 'pending_verification'
        ) {
          paymentPending++;
        }
      }
    }
    return [
      {
        label: 'Belum dibaca',
        value: unreadTotal,
        tone: unreadTotal > 0 ? 'accent' : 'normal',
      },
      {
        label: 'Pesanan aktif',
        value: activeOrders,
        tone: 'normal',
      },
      {
        label: 'Bayaran perlu sah',
        value: paymentPending,
        tone: paymentPending > 0 ? 'alert' : 'normal',
      },
    ];
  }, [conversations, unreadTotal]);

  // ----- Layout -----
  // Mobile two-screen pattern: when a conversation is selected, the list is
  // hidden and only the right panel shows (with a back affordance handled by
  // the right panel itself in Phase 7). For now the placeholder won't show a
  // back button — that's a Phase 7 concern.
  const showListOnMobile = !selectedConversationId;
  const showRightOnMobile = !!selectedConversationId;

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e1a] text-white">
      <DashboardHeader userName={userName} onLogout={handleLogout} />

      <div className="sticky top-14 z-30 bg-[#0a0e1a]/95 backdrop-blur-sm">
        <TopBar
          unreadTotal={unreadTotal}
          loading={loading}
          lastRefresh={lastRefresh}
          onRefresh={handleRefresh}
        />
      </div>

      <main className="flex-1 min-h-0 flex">
        <ConversationListPanel
          conversations={conversations}
          filteredConversations={filteredConversations}
          websites={websites}
          websiteLabelById={websiteLabelById}
          selectedWebsiteId={selectedWebsiteId}
          tab={tab}
          searchQuery={searchQuery}
          selectedConversationId={selectedConversationId}
          loading={loading}
          onWebsiteChange={setSelectedWebsiteId}
          onTabChange={setTab}
          onSearchChange={setSearchQuery}
          onSelectConversation={handleSelectConversation}
          className={[
            'w-full md:w-[380px] md:shrink-0 border-r border-white/[0.06]',
            isMobile && !showListOnMobile ? 'hidden' : 'flex',
          ].join(' ')}
        />

        <section
          className={[
            'flex-1 min-w-0 flex flex-col',
            isMobile && !showRightOnMobile ? 'hidden md:flex' : 'flex',
          ].join(' ')}
        >
          {selectedConversation ? (
            <ChatPanelWrapper
              conv={selectedConversation}
              ownerName={ownerName}
              websiteLabel={
                websiteLabelById.get(selectedConversation.website_id) ||
                'Outlet'
              }
              isMobile={isMobile}
              onBack={handleBackToList}
              onCopyPhone={handleCopyPhone}
              onCloseConversation={handleCloseConversation}
              onVerifyPayment={handleVerifyPayment}
            />
          ) : (
            <EmptyState variant="no-selection" stats={noSelectionStats} />
          )}
        </section>
      </main>

      <VerifyPaymentModal
        message={verifyModalForMessage}
        onConfirm={handleConfirmVerify}
        onClose={handleCloseVerifyModal}
      />
    </div>
  );
}
