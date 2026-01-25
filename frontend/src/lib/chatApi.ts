/**
 * BinaApp Chat API Client
 *
 * Centralized API client for all chat operations with proper authentication.
 * Uses stored JWT token for authentication to fix 401 errors.
 */

import { getStoredToken } from './supabase'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  'https://binaapp-backend.onrender.com'

/**
 * Get auth headers with JWT token
 * Priority:
 * 1. Backend token from localStorage (binaapp_auth_token)
 * 2. Fallback to no auth for public endpoints
 */
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  // Get token from localStorage
  const token = getStoredToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
    console.log('[ChatAPI] Auth token attached')
  } else {
    console.warn('[ChatAPI] No auth token found in storage')
  }

  return headers
}

/**
 * Make authenticated fetch request to chat API
 */
async function chatFetch<T>(
  path: string,
  options?: RequestInit & { timeout?: number }
): Promise<T> {
  const timeout = options?.timeout || 30000 // 30 second timeout
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const headers = {
      ...getAuthHeaders(),
      ...(options?.headers as Record<string, string> || {}),
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!res.ok) {
      const errorText = await res.text()
      console.error('[ChatAPI] Request failed:', res.status, errorText)

      // Handle specific error codes
      if (res.status === 401) {
        console.error('[ChatAPI] Authentication failed - token may be expired')
        // Optionally redirect to login
        if (typeof window !== 'undefined') {
          // Clear invalid token
          localStorage.removeItem('binaapp_auth_token')
          // Redirect after a brief delay
          setTimeout(() => {
            window.location.href = '/login?error=session_expired'
          }, 1000)
        }
        throw new Error('Sesi tamat. Sila log masuk semula.')
      }

      if (res.status === 403) {
        throw new Error('Akses tidak dibenarkan.')
      }

      throw new Error(errorText || `Request failed with status ${res.status}`)
    }

    return res.json()
  } catch (error: any) {
    clearTimeout(timeoutId)

    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Sila cuba lagi.')
    }

    throw error
  }
}

// =====================================================
// CONVERSATION ENDPOINTS
// =====================================================

export interface Conversation {
  id: string
  order_id?: string
  website_id: string
  website_name?: string
  customer_id?: string
  customer_name?: string
  customer_phone?: string
  status: 'active' | 'closed' | 'archived'
  unread_owner?: number
  unread_customer?: number
  unread_rider?: number
  created_at: string
  updated_at: string
  chat_messages?: ChatMessage[]
}

export interface ChatMessage {
  id: string
  conversation_id: string
  sender_type: 'customer' | 'owner' | 'rider' | 'system'
  sender_id?: string
  sender_name?: string
  message_type: 'text' | 'image' | 'location' | 'payment' | 'status' | 'voice'
  message_text?: string
  content?: string
  message?: string
  media_url?: string
  metadata?: Record<string, any>
  is_read: boolean
  created_at: string
}

export interface ConversationsResponse {
  conversations: Conversation[]
}

export interface ConversationDetailResponse {
  conversation: Conversation
  messages: ChatMessage[]
  participants: any[]
}

/**
 * Get all conversations for authenticated user's websites
 * Requires authentication
 */
export async function getConversations(
  websiteIds?: string | string[],
  status?: string
): Promise<ConversationsResponse> {
  const params = new URLSearchParams()

  if (websiteIds) {
    const ids = Array.isArray(websiteIds) ? websiteIds.join(',') : websiteIds
    if (ids) params.set('website_ids', ids)
  }

  if (status) {
    params.set('status', status)
  }

  const queryString = params.toString()
  const path = queryString
    ? `/api/v1/chat/conversations?${queryString}`
    : '/api/v1/chat/conversations'

  console.log('[ChatAPI] Getting conversations:', path)
  return chatFetch<ConversationsResponse>(path)
}

/**
 * Get conversation details with messages
 * This endpoint may not require auth for public chat access
 */
export async function getConversation(
  conversationId: string
): Promise<ConversationDetailResponse> {
  console.log('[ChatAPI] Getting conversation:', conversationId)
  return chatFetch<ConversationDetailResponse>(
    `/api/v1/chat/conversations/${conversationId}`
  )
}

/**
 * Get conversations for a specific website
 * Requires authentication - user must own the website
 */
export async function getWebsiteConversations(
  websiteId: string,
  status?: string
): Promise<ConversationsResponse> {
  const params = new URLSearchParams()
  if (status) params.set('status', status)

  const queryString = params.toString()
  const path = queryString
    ? `/api/v1/chat/conversations/website/${websiteId}?${queryString}`
    : `/api/v1/chat/conversations/website/${websiteId}`

  console.log('[ChatAPI] Getting website conversations:', path)
  return chatFetch<ConversationsResponse>(path)
}

// =====================================================
// MESSAGE ENDPOINTS
// =====================================================

export interface SendMessageRequest {
  conversation_id: string
  sender_type: string
  sender_id: string
  sender_name?: string
  message_type?: string
  message_text?: string
  media_url?: string
  metadata?: Record<string, any>
}

export interface SendMessageResponse {
  message_id: string
  status: string
}

/**
 * Send a message in a conversation
 */
export async function sendMessage(
  request: SendMessageRequest
): Promise<SendMessageResponse> {
  console.log('[ChatAPI] Sending message to:', request.conversation_id)
  return chatFetch<SendMessageResponse>('/api/v1/chat/messages/send', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

/**
 * Get messages for a conversation
 */
export async function getMessages(
  conversationId: string
): Promise<ChatMessage[]> {
  console.log('[ChatAPI] Getting messages for:', conversationId)
  return chatFetch<ChatMessage[]>(
    `/api/v1/chat/conversations/${conversationId}/messages`
  )
}

/**
 * Mark messages as read
 */
export async function markMessagesRead(
  conversationId: string,
  userType: string
): Promise<{ status: string }> {
  console.log('[ChatAPI] Marking messages read:', conversationId, userType)
  return chatFetch<{ status: string }>('/api/v1/chat/messages/mark-read', {
    method: 'POST',
    body: JSON.stringify({
      conversation_id: conversationId,
      user_type: userType,
    }),
  })
}

// =====================================================
// FILE UPLOAD ENDPOINTS
// =====================================================

export interface UploadImageResponse {
  success: boolean
  url: string
  filename: string
}

/**
 * Upload an image for chat
 */
export async function uploadChatImage(
  file: File
): Promise<UploadImageResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const token = getStoredToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}/api/v1/chat/chat/messages/upload-image`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || 'Failed to upload image')
  }

  return res.json()
}

// =====================================================
// CONVENIENCE EXPORTS
// =====================================================

export const chatApi = {
  getConversations,
  getConversation,
  getWebsiteConversations,
  sendMessage,
  getMessages,
  markMessagesRead,
  uploadChatImage,
}

export default chatApi
