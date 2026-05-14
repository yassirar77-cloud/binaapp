'use client';

// Left-rail wrapper: WebsiteFilterPills + SearchBar + TabBar + scrollable rows.
// Width fixed at 380px on >=md, full-width on mobile (caller hides via CSS
// when the chat panel is shown). Designed to be self-contained so ChatClient
// just hands data + handlers.

import type { Conversation, TabKey, Website } from '../lib/types';
import WebsiteFilterPills from './WebsiteFilterPills';
import SearchBar from './SearchBar';
import TabBar from './TabBar';
import ConversationRow from './ConversationRow';
import EmptyState from './EmptyState';

interface Props {
  // Data
  conversations: Conversation[];        // unfiltered, for tab counts
  filteredConversations: Conversation[]; // already filtered + sorted
  websites: Website[];
  websiteLabelById: Map<string, string>;
  // Filter state
  selectedWebsiteId: string | 'all';
  tab: TabKey;
  searchQuery: string;
  // Selection
  selectedConversationId: string | null;
  // Bookkeeping
  loading: boolean;
  // Handlers
  onWebsiteChange: (id: string | 'all') => void;
  onTabChange: (next: TabKey) => void;
  onSearchChange: (next: string) => void;
  onSelectConversation: (id: string) => void;
  // Layout
  className?: string;
}

export default function ConversationListPanel({
  conversations,
  filteredConversations,
  websites,
  websiteLabelById,
  selectedWebsiteId,
  tab,
  searchQuery,
  selectedConversationId,
  loading,
  onWebsiteChange,
  onTabChange,
  onSearchChange,
  onSelectConversation,
  className = '',
}: Props) {
  const hasAny = conversations.length > 0;

  return (
    <aside
      className={[
        'relative z-10 flex flex-col h-full min-h-0 bg-white/[0.02]',
        className,
      ].join(' ')}
    >
      <WebsiteFilterPills
        websites={websites}
        selectedWebsiteId={selectedWebsiteId}
        onChange={onWebsiteChange}
      />
      <SearchBar value={searchQuery} onChange={onSearchChange} />
      <TabBar
        tab={tab}
        onTabChange={onTabChange}
        conversations={conversations}
      />

      <div className="flex-1 min-h-0 overflow-y-auto">
        {loading && conversations.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white/40" />
          </div>
        ) : filteredConversations.length === 0 ? (
          <EmptyState variant={hasAny ? 'no-match' : 'no-convs'} />
        ) : (
          <div>
            {filteredConversations.map((c) => (
              <ConversationRow
                key={c.id}
                conv={c}
                websiteLabel={
                  c.website_name ||
                  websiteLabelById.get(c.website_id) ||
                  'Outlet'
                }
                selected={selectedConversationId === c.id}
                onSelect={onSelectConversation}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer: total + unread counts. Mirrors pesanan's footer style. */}
      <div className="px-3 py-2 border-t border-white/[0.06] bg-white/[0.02] flex items-center justify-between font-mono text-[10px] text-white/40">
        <span>{conversations.length} perbualan</span>
        <span>
          {conversations.reduce(
            (sum, c) => sum + (c.unread_owner ?? 0),
            0,
          )}{' '}
          belum dibaca
        </span>
      </div>
    </aside>
  );
}
