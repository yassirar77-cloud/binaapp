/**
 * TypeScript Type Definitions
 */

export interface User {
  id: string
  email: string
  full_name?: string
  subscription_tier: 'free' | 'basic' | 'pro'
  websites_count: number
}

export interface Website {
  id: string
  user_id: string
  business_name: string
  subdomain: string
  full_url: string
  status: 'draft' | 'generating' | 'published' | 'failed'
  created_at: string
  updated_at: string
  published_at?: string
  html_content?: string
  preview_url?: string
}

export interface Template {
  id: string
  name: string
  category: 'restaurant' | 'retail' | 'services' | 'portfolio' | 'landing'
  description: string
  thumbnail_url: string
  preview_url: string
}

export interface SubscriptionPlan {
  tier: 'free' | 'basic' | 'pro'
  name: string
  price_monthly: number
  price_yearly: number
  features: string[]
  max_websites: number
  custom_domain: boolean
}

export interface WebsiteGenerationForm {
  business_name: string
  business_type: string
  description: string
  language: 'en' | 'ms'
  subdomain: string
  include_whatsapp: boolean
  whatsapp_number: string
  include_maps: boolean
  location_address: string
  include_ecommerce: boolean
  contact_email: string
}

// Delivery Order Types
export type OrderStatus =
  | 'pending'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'picked_up'
  | 'delivering'
  | 'delivered'
  | 'completed'
  | 'cancelled'
  | 'rejected'

export interface DeliveryOrder {
  id: string
  order_number: string
  website_id: string
  customer_name: string
  customer_phone: string
  customer_email?: string
  delivery_address: string
  delivery_fee: number
  subtotal: number
  total_amount: number
  payment_method: 'cod' | 'online' | 'ewallet'
  payment_status: 'pending' | 'paid' | 'failed' | 'refunded'
  status: OrderStatus
  created_at: string
  confirmed_at?: string
  preparing_at?: string
  ready_at?: string
  picked_up_at?: string
  delivered_at?: string
  completed_at?: string
  cancelled_at?: string
  estimated_prep_time?: number
  estimated_delivery_time?: number
  delivery_zone_id?: string | null
  rider_id?: string | null
}

// Dispute Types
export type DisputeCategory =
  | 'wrong_items'
  | 'missing_items'
  | 'quality_issue'
  | 'late_delivery'
  | 'damaged_items'
  | 'overcharged'
  | 'never_delivered'
  | 'rider_issue'
  | 'other'

export type DisputeStatus =
  | 'open'
  | 'under_review'
  | 'awaiting_response'
  | 'resolved'
  | 'closed'
  | 'escalated'
  | 'rejected'

export type DisputePriority = 'low' | 'medium' | 'high' | 'urgent'

export type DisputeResolutionType =
  | 'full_refund'
  | 'partial_refund'
  | 'replacement'
  | 'credit'
  | 'apology'
  | 'rejected'
  | 'escalated'

export interface Dispute {
  id: string
  dispute_number: string
  order_id: string
  website_id: string
  customer_id: string
  customer_name: string
  customer_phone?: string
  customer_email?: string
  category: DisputeCategory
  description: string
  evidence_urls?: string[]
  order_amount: number
  disputed_amount?: number
  refund_amount?: number
  ai_category_confidence?: number
  ai_severity_score?: number
  ai_recommendation?: string
  ai_analysis?: {
    category_confidence: number
    severity_score: number
    recommended_resolution: string
    recommended_refund_percentage?: number
    priority: string
    reasoning: string
    suggested_response: string
    risk_flags: string[]
    analysis_source: string
  }
  status: DisputeStatus
  resolution_type?: DisputeResolutionType
  resolution_notes?: string
  resolved_by?: string
  priority: DisputePriority
  created_at: string
  updated_at: string
  reviewed_at?: string
  resolved_at?: string
  closed_at?: string
}

export interface DisputeMessage {
  id: string
  dispute_id: string
  sender_type: 'customer' | 'owner' | 'admin' | 'ai' | 'system'
  sender_id?: string
  sender_name?: string
  message: string
  attachments?: string[]
  is_internal: boolean
  metadata?: Record<string, any>
  created_at: string
}

export interface DisputeSummary {
  total_disputes: number
  open_disputes: number
  resolved_disputes: number
  escalated_disputes: number
  avg_resolution_time_hours?: number
  total_refunded: number
  resolution_rate: number
  by_category: Record<string, number>
  by_priority: Record<string, number>
}
