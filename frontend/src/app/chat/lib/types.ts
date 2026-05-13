// /chat — domain types for owner chat inbox.
// Mirrors the chat_messages / chat_conversations Supabase schema and the
// shapes returned by backend/app/api/v1/endpoints/chat.py.

export type ConversationStatus = 'active' | 'closed' | 'archived';

export type TabKey =
  | 'all'
  | 'unread'
  | 'active'
  | 'order'
  | 'support'
  | 'closed';

export type MessageType =
  | 'text'
  | 'image'
  | 'payment'
  | 'system'
  | 'location'
  | 'voice'
  | 'status';

export type SenderType = 'owner' | 'customer' | 'rider' | 'system';

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: SenderType;
  sender_id?: string;
  sender_name?: string;
  message_type: MessageType;
  message_text?: string;
  content?: string;
  message?: string;
  media_url?: string;
  metadata?: Record<string, any>;
  is_read: boolean;
  created_at: string;
}

export interface Conversation {
  id: string;
  website_id: string;
  website_name?: string;
  customer_id?: string;
  customer_name?: string;
  customer_phone?: string;
  order_id?: string;
  order_number?: string;
  order_status?: string;
  status: ConversationStatus;
  unread_owner?: number;
  unread_customer?: number;
  unread_rider?: number;
  created_at: string;
  updated_at: string;
  chat_messages?: Message[];
}

export interface Website {
  id: string;
  business_name?: string;
  name?: string;
  subdomain?: string;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: Message[];
  participants: any[];
}

export interface VerifyPaymentResponse {
  success: boolean;
  message_id: string;
  verified_at: string;
}
