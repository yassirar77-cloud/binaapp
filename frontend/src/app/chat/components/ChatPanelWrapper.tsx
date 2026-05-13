'use client';

// Right-side panel mounted when a conversation is selected. Renders the new
// ChatHeader above BinaChat. BinaChat is mounted with four new optional props
// (hideHeader, mapVisibility, orderStatus, onVerifyPayment) that this PR
// declares ahead of Phase 8. Phase 8 adds the actual handling in BinaChat.tsx;
// before that, BinaChat ignores them — they're declared here via a typed cast
// so we don't have to touch the shared component until the surgical phase.

import type { ComponentType } from 'react';
import BinaChatRaw from '@/components/BinaChat';
import type { Conversation } from '../lib/types';
import ChatHeader from './ChatHeader';

// Future-shape of BinaChat after Phase 8. Cast is local to this file; once
// Phase 8 lands and BinaChatProps gains these fields, the cast drops away.
type FutureBinaChatProps = {
  conversationId: string;
  userType: 'customer' | 'owner' | 'rider';
  userId: string;
  userName: string;
  orderId?: string;
  showMap?: boolean;
  onClose?: () => void;
  className?: string;
  hideHeader?: boolean;
  mapVisibility?: 'always' | 'in-transit-only' | 'never';
  orderStatus?: string;
  onVerifyPayment?: (messageId: string) => void;
};
const BinaChat = BinaChatRaw as unknown as ComponentType<FutureBinaChatProps>;

interface Props {
  conv: Conversation;
  ownerName: string;
  websiteLabel: string;
  isMobile: boolean;
  onBack: () => void;
  onCopyPhone: (phone: string) => void;
  onCloseConversation: (id: string) => void;
  onVerifyPayment: (messageId: string) => void;
}

export default function ChatPanelWrapper({
  conv,
  ownerName,
  websiteLabel,
  isMobile,
  onBack,
  onCopyPhone,
  onCloseConversation,
  onVerifyPayment,
}: Props) {
  // Owner-display name fallback chain mirrors the legacy OwnerChatDashboard.
  // The customer + rider sides of the chat see this string as "from".
  const displayName =
    conv.website_name || websiteLabel || ownerName || 'Pemilik Kedai';

  return (
    <div className="h-full w-full flex flex-col min-h-0">
      <ChatHeader
        conv={conv}
        isMobile={isMobile}
        onBack={onBack}
        onCopyPhone={onCopyPhone}
        onCloseConversation={onCloseConversation}
      />

      <div className="flex-1 min-h-0">
        <BinaChat
          conversationId={conv.id}
          userType="owner"
          userId={conv.website_id}
          userName={displayName}
          orderId={conv.order_id}
          showMap={false}
          mapVisibility="in-transit-only"
          orderStatus={conv.order_status}
          hideHeader
          onVerifyPayment={onVerifyPayment}
          className="h-full w-full"
        />
      </div>
    </div>
  );
}
