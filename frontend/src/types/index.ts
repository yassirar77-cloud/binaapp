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
}
