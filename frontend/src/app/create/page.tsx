/**
 * Create Page - AI Website Generation
 */
'use client'
import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Sparkles, Download, Upload, Eye, Copy, Check, Share2, Layout } from 'lucide-react'
import VisualImageUpload from './components/VisualImageUpload'
import DevicePreview from './components/DevicePreview'
import MultiDevicePreview from './components/MultiDevicePreview'
import CodeAnimation from '@/components/CodeAnimation'
import { UpgradeModal } from '@/components/UpgradeModal'
import { AddonPurchaseModal } from '@/components/AddonPurchaseModal'
import { LimitReachedModal } from '@/components/LimitReachedModal'
import { API_BASE_URL, DIRECT_BACKEND_URL } from '@/lib/env'
import { supabase, signOut as customSignOut, getCurrentUser, getStoredToken } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import toast from 'react-hot-toast'
import './create.css'

const EXAMPLE_DESCRIPTIONS = [
  {
    title: 'Kedai Nasi Kandar',
    lang: 'ms',
    text: 'Saya ada kedai nasi kandar di Penang. Kami jual nasi kandar, ayam goreng, ikan bakar, dan pelbagai lauk. Menu dari RM5-RM15. Kami terletak di Jalan Burma, Penang. Telefon 019-5551234. Buka 7am-11pm setiap hari.'
  },
  {
    title: 'Hair Salon Booking',
    lang: 'en',
    text: 'Modern hair salon in KL offering haircuts, coloring, and styling. Prices from RM50-RM300. Located at Bukit Bintang. Book appointments via WhatsApp 012-3456789. Open Tuesday-Sunday 10am-8pm.'
  },
  {
    title: 'Photography Portfolio',
    lang: 'en',
    text: 'Professional photographer specializing in weddings and events. Based in Selangor. Contact via WhatsApp 011-23456789 or email hello@photos.com. View my portfolio and book your session today.'
  },
  {
    title: 'Butik Pakaian Online',
    lang: 'ms',
    text: 'Butik online menjual pakaian wanita, baju kurung, tudung, dan aksesori. Harga dari RM30-RM200. Hantar ke seluruh Malaysia. WhatsApp untuk order: 013-8889999. Instagram: @butikkita'
  }
]

interface StyleVariation {
  style: string
  html: string
  preview_image?: string
  thumbnail?: string
  social_preview?: string
}

// Blocked subdomain words - must match backend list
const BLOCKED_WORDS = [
  // English offensive
  "fuck", "shit", "ass", "bitch", "dick", "porn", "sex", "xxx",
  "nude", "naked", "kill", "murder", "terrorist", "bomb", "drug",
  "cocaine", "heroin", "weed", "gambling", "casino", "scam", "fraud",

  // Malay offensive
  "babi", "bodoh", "sial", "pukimak", "kimak", "lancau", "pantat",
  "sundal", "jalang", "pelacur", "haram", "celaka", "bangang",
  "bengap", "tolol", "goblok", "anjing", "asu",

  // Religious/Political sensitive (Malaysia)
  "allah", "nabi", "rasul", "agong", "sultan", "kerajaan",

  // Brand/Trademark issues
  "google", "facebook", "instagram", "tiktok", "twitter", "amazon",
  "apple", "microsoft", "netflix", "shopee", "lazada", "grab",

  // Government/Official
  "gov", "government", "polis", "police", "tentera", "army",
  "kementerian", "jabatan", "official", "rasmi",
]

/**
 * Validate subdomain against content policy
 * Returns error message if invalid, null if valid
 */
const validateSubdomain = (subdomain: string): string | null => {
  const lower = subdomain.toLowerCase().trim()

  if (lower.length < 3) {
    return "Subdomain mesti sekurang-kurangnya 3 aksara. Minimum 3 characters."
  }

  if (lower.length > 30) {
    return "Subdomain terlalu panjang. Subdomain too long."
  }

  if (!/^[a-z0-9-]+$/.test(lower)) {
    return "Hanya huruf kecil, nombor dan (-) dibenarkan. Only lowercase, numbers and hyphens allowed."
  }

  if (lower.startsWith('-') || lower.endsWith('-')) {
    return "Tidak boleh bermula/berakhir dengan (-). Cannot start/end with hyphen."
  }

  for (const word of BLOCKED_WORDS) {
    if (lower.includes(word)) {
      return "Nama ini tidak dibenarkan. This name is not allowed."
    }
  }

  return null // Valid
}

export default function CreatePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const selectedTemplateId = searchParams.get('template') || null
  const [user, setUser] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [description, setDescription] = useState('')
  const [language, setLanguage] = useState<'ms' | 'en'>('ms')
  const [loading, setLoading] = useState(false)
  const [generatedHtml, setGeneratedHtml] = useState('')
  const [detectedFeatures, setDetectedFeatures] = useState<string[]>([])
  const [templateUsed, setTemplateUsed] = useState('')
  const [error, setError] = useState('')
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [subdomain, setSubdomain] = useState('')
  const [subdomainError, setSubdomainError] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [publishedUrl, setPublishedUrl] = useState('')
  const [copied, setCopied] = useState(false)
  const [uploadedImages, setUploadedImages] = useState<{
    hero: string | null
    gallery: { url: string; name: string; price: string }[]
  }>({ hero: null, gallery: [] })

  const [multiStyle, setMultiStyle] = useState(true)
  const [styleVariations, setStyleVariations] = useState<StyleVariation[]>([])
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null)
  const [generatePreviews, setGeneratePreviews] = useState(false)

  const [previewMode, setPreviewMode] = useState<'single' | 'multi'>('single')
  const [progress, setProgress] = useState(0)

  // CRITICAL: Track current job ID and polling interval to prevent stale polling
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Track progress updates for stale detection
  const [lastProgressUpdate, setLastProgressUpdate] = useState<Date | null>(null)
  const [lastProgress, setLastProgress] = useState<number>(0)
  const [staleWarning, setStaleWarning] = useState<boolean>(false)
  const staleCheckRef = useRef<number>(0) // Count of polls with same progress

  // Upgrade/Addon modal states
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [showAddonModal, setShowAddonModal] = useState(false)
  const [showLimitModal, setShowLimitModal] = useState(false)
  const [limitModalData, setLimitModalData] = useState<{
    resourceType: 'website' | 'menu_item' | 'ai_hero' | 'ai_image' | 'zone' | 'rider';
    currentUsage: number;
    limit: number;
    canBuyAddon: boolean;
    addonPrice?: number;
  } | null>(null)
  const [selectedAddon, setSelectedAddon] = useState<{
    type: string;
    label: string;
    price: number;
    quantity?: number;
    is_recurring?: boolean;
  } | null>(null)
  const [targetTier, setTargetTier] = useState<string>('starter')
  const [currentTier, setCurrentTier] = useState<string>('free')
  const [limitWarning, setLimitWarning] = useState<string | null>(null)
  const [hasActiveSubscription, setHasActiveSubscription] = useState<boolean | null>(null)
  const [subscriptionLoading, setSubscriptionLoading] = useState(true)
  const [isAtLimit, setIsAtLimit] = useState(false)

  // Feature selector states
  const [selectedFeatures, setSelectedFeatures] = useState({
    whatsapp: true,          // WhatsApp button
    googleMap: false,        // Google Map embed
    deliverySystem: false,   // Delivery ordering
    contactForm: false,      // Contact form
    socialMedia: false,      // Social media links
    priceList: true,         // Show prices on menu
    operatingHours: true,    // Show operating hours
    gallery: true,           // Photo gallery section
  })

  // Business type state - for dynamic categories and labels
  const [businessType, setBusinessType] = useState<'auto' | 'food' | 'clothing' | 'salon' | 'services' | 'bakery' | 'general'>('auto')
  const [colorMode, setColorMode] = useState<'light' | 'dark'>('light')

  // STRICT IMAGE CONTROL - Explicit user choice for images
  // 'none' = No images (text-only website)
  // 'upload' = Use only user-uploaded images
  // 'ai' = Generate AI images with Stability AI
  const [imageChoice, setImageChoice] = useState<'none' | 'upload' | 'ai'>('none')

  // Delivery system states
  const [deliveryArea, setDeliveryArea] = useState('')
  const [deliveryFee, setDeliveryFee] = useState('')
  const [minimumOrder, setMinimumOrder] = useState('')
  const [deliveryHours, setDeliveryHours] = useState('')

  // Payment methods state (QR + COD only)
  const [paymentMethods, setPaymentMethods] = useState({
    cod: true,  // Cash on Delivery
    qr: false   // QR Payment (DuitNow/TNG/Bank)
  })
  const [paymentQR, setPaymentQR] = useState<File | null>(null)
  const [paymentQRPreview, setPaymentQRPreview] = useState<string>('')

  // Fulfillment options state
  const [fulfillment, setFulfillment] = useState({
    delivery: true,
    deliveryFee: '5.00',
    minOrder: '20.00',
    deliveryArea: '',
    pickup: false,
    pickupAddress: ''
  })

  // Google Map state
  const [fullAddress, setFullAddress] = useState('')

  // Social media states
  const [instagram, setInstagram] = useState('')
  const [facebook, setFacebook] = useState('')
  const [tiktok, setTiktok] = useState('')

  // Handle QR image upload
  const handleQRUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setPaymentQR(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setPaymentQRPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  useEffect(() => {
    checkUser()
  }, [])

  // Check website limit on page load using direct Supabase count (source of truth)
  useEffect(() => {
    const checkLimit = async () => {
      if (!supabase) return
      try {
        const { data: { user: authUser } } = await supabase.auth.getUser()
        if (!authUser) return

        const { count } = await supabase
          .from('websites')
          .select('id', { count: 'exact', head: true })
          .eq('user_id', authUser.id)

        const { data: subData } = await supabase
          .from('subscriptions')
          .select('subscription_plans(websites_limit)')
          .eq('user_id', authUser.id)
          .eq('status', 'active')
          .order('created_at', { ascending: false })
          .limit(1)
          .single()

        const limit = subData?.subscription_plans?.websites_limit ?? 1

        // Unlimited plan
        if (limit === null) return

        // Get addon credits
        const { data: addons } = await supabase
          .from('addon_purchases')
          .select('quantity_remaining')
          .eq('user_id', authUser.id)
          .eq('addon_type', 'website')
          .eq('status', 'active')
          .gt('quantity_remaining', 0)

        const addonCredits = (addons || []).reduce((sum: number, a: any) => sum + a.quantity_remaining, 0)
        const totalAllowed = limit + addonCredits

        if ((count ?? 0) >= totalAllowed) {
          setIsAtLimit(true)
          setLimitModalData({
            resourceType: 'website',
            currentUsage: count ?? 0,
            limit: limit,
            canBuyAddon: true,
            addonPrice: 5
          })
          setShowLimitModal(true)
        }
      } catch (err) {
        console.error('[Create] Direct limit check failed:', err)
      }
    }
    checkLimit()
  }, [])

  // CRITICAL: Cleanup polling interval on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        console.log('🧹 Cleanup: Clearing polling interval on unmount');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);

  // Check subscription status
  async function checkSubscriptionStatus() {
    try {
      setSubscriptionLoading(true)
      const token = getStoredToken()
      if (!token) {
        setHasActiveSubscription(false)
        setSubscriptionLoading(false)
        return
      }

      const response = await fetch(`${DIRECT_BACKEND_URL}/api/v1/subscription/status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('[Create] Subscription status:', data)
        // Check if subscription is active and not expired
        const isActive = data.status === 'active' && !data.is_expired
        setHasActiveSubscription(isActive)
        setCurrentTier((data.tier || data.plan_name || 'free').toLowerCase())
      } else {
        console.error('[Create] Failed to get subscription status:', response.status)
        setHasActiveSubscription(false)
      }
    } catch (error) {
      console.error('[Create] Error checking subscription:', error)
      setHasActiveSubscription(false)
    } finally {
      setSubscriptionLoading(false)
    }
  }

  async function checkUser() {
    try {
      // First check for custom BinaApp token
      const customToken = getStoredToken()
      const customUser = await getCurrentUser()

      if (customToken && customUser) {
        console.log('[Create] ✅ Using custom BinaApp auth')
        // Create a mock user object compatible with Supabase User type
        const mockUser = {
          id: customUser.id,
          email: customUser.email,
          user_metadata: { full_name: customUser.full_name }
        } as unknown as User
        setUser(mockUser)
        setAuthLoading(false)
        // Check subscription status after user is authenticated
        await checkSubscriptionStatus()
        return
      }

      // Fallback to Supabase session
      if (!supabase) {
        setAuthLoading(false)
        return
      }

      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
    } catch (error) {
      console.error('Error checking user:', error)
    } finally {
      setAuthLoading(false)
    }
  }

  async function handleLogout() {
    try {
      // Clear custom BinaApp token
      await customSignOut()
      // Also clear Supabase session if available
      if (supabase) {
        await supabase.auth.signOut()
      }
      setUser(null)
      router.push('/')
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  // Check if user can create a website (subscription limit check)
  async function checkWebsiteLimit(): Promise<boolean> {
    try {
      const token = getStoredToken()
      if (!token) {
        // Not logged in - allow generation but block publishing later
        return true
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/subscription/check-limit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'create_website' })
      })

      const data = await response.json()
      console.log('[Create] Limit check result:', data)

      if (!response.ok || !data.allowed) {
        // Show limit reached modal
        setLimitModalData({
          resourceType: 'website',
          currentUsage: data.current_usage || 0,
          limit: data.limit || 1,
          canBuyAddon: data.can_buy_addon || false,
          addonPrice: data.addon_price
        })
        setShowLimitModal(true)
        return false
      }

      // Show warning if approaching limit
      if (data.limit && !data.unlimited && data.current_usage >= data.limit * 0.8) {
        setLimitWarning(`Amaran: Anda telah menggunakan ${data.current_usage}/${data.limit} website.`)
      } else {
        setLimitWarning(null)
      }

      return true
    } catch (error) {
      console.error('[Create] Limit check error:', error)
      // FAIL CLOSED: Block action when limit check fails
      setError('Gagal menyemak had penggunaan. Sila cuba lagi.')
      return false
    }
  }

  // Check if user can use AI images
  async function checkAIImageLimit(): Promise<boolean> {
    if (imageChoice !== 'ai') return true

    try {
      const token = getStoredToken()
      if (!token) return true

      const response = await fetch(`${API_BASE_URL}/api/v1/subscription/check-limit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'generate_ai_image' })
      })

      const data = await response.json()

      if (!response.ok || !data.allowed) {
        setLimitModalData({
          resourceType: 'ai_image',
          currentUsage: data.current_usage || 0,
          limit: data.limit || 5,
          canBuyAddon: data.can_buy_addon || false,
          addonPrice: data.addon_price
        })
        setShowLimitModal(true)
        return false
      }

      return true
    } catch (error) {
      console.error('[Create] AI image limit check error:', error)
      // FAIL CLOSED: Block action when limit check fails
      setError('Gagal menyemak had penggunaan imej AI. Sila cuba lagi.')
      return false
    }
  }

  // Handle when a limit is reached - show upgrade or addon modal
  const handleLimitReached = (limitData: {
    addon_option?: { type: string; label: string; price: number; is_recurring?: boolean };
    upgrade_options?: { tier: string; price: number }[];
  }) => {
    if (limitData.addon_option) {
      setSelectedAddon(limitData.addon_option)
      setShowAddonModal(true)
    } else if (limitData.upgrade_options && limitData.upgrade_options.length > 0) {
      setTargetTier(limitData.upgrade_options[0].tier)
      setShowUpgradeModal(true)
    }
  }

  // Show upgrade modal directly
  const showUpgrade = (tier: string = 'basic') => {
    setTargetTier(tier)
    setShowUpgradeModal(true)
  }

  // Show addon purchase modal
  const showAddonPurchase = (addon: { type: string; label: string; price: number; is_recurring?: boolean }) => {
    setSelectedAddon(addon)
    setShowAddonModal(true)
  }

  const handleGenerate = async () => {
    if (!description.trim()) return;

    // Hard block if already at limit (checked on page load)
    if (isAtLimit) {
      setShowLimitModal(true)
      return
    }

    // Check if user is logged in
    if (!user) {
      setError('Sila log masuk untuk mencipta website')
      return
    }

    // Check if user has active subscription
    if (hasActiveSubscription === false) {
      setError('Sila langgan pelan untuk mencipta website. Bermula dari RM5/bulan.')
      // Show upgrade modal
      setTargetTier('starter')
      setShowUpgradeModal(true)
      return
    }

    // Check subscription limits before generating
    const canCreate = await checkWebsiteLimit()
    if (!canCreate) {
      return // Modal will be shown by checkWebsiteLimit
    }

    // Check AI image limits if AI images selected
    const canUseAI = await checkAIImageLimit()
    if (!canUseAI) {
      return
    }

    // CRITICAL: Clear any existing polling interval to prevent stale job ID polling
    if (pollIntervalRef.current) {
      console.log('🧹 Clearing previous polling interval before starting new generation');
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    // Clear old job ID and reset stale detection
    setCurrentJobId(null);
    setLastProgressUpdate(null);
    setLastProgress(0);
    setStaleWarning(false);
    staleCheckRef.current = 0;

    setLoading(true);
    setError('');
    setStyleVariations([]);
    setProgress(0);

    try {
      console.log('🚀 Starting async generation...');

      // Step 1: Start the job (returns immediately with job_id)
      // Prepare images array - combine hero and gallery images with metadata
      const galleryWithMetadata = uploadedImages.gallery.map(g => ({
        url: g.url,
        name: g.name || '',  // Ensure name is always a string
        price: g.price || ''  // Include price
      }));

      const allImages = uploadedImages.hero
        ? [{ url: uploadedImages.hero, name: 'Hero Image' }, ...galleryWithMetadata]
        : galleryWithMetadata;

      // STRICT IMAGE CONTROL: Determine final image choice
      // If user uploaded images, force 'upload' mode
      // Otherwise, use the user's explicit selection
      const finalImageChoice = allImages.length > 0 ? 'upload' : imageChoice;
      console.log(`🖼️ Image Choice: ${finalImageChoice} (user selected: ${imageChoice}, has uploads: ${allImages.length > 0})`);

      // ===== COMPREHENSIVE DEBUG LOGGING =====
      console.log('==========================================');
      console.log('📤 SENDING TO BACKEND:');
      console.log('  🖼️ Image Choice:', finalImageChoice);
      console.log('  ✅ Features:', selectedFeatures);
      console.log('  📱 WhatsApp:', selectedFeatures.whatsapp);
      console.log('  🗺️ Google Map:', selectedFeatures.googleMap);
      console.log('  🚚 Delivery:', selectedFeatures.deliverySystem);
      console.log('  📧 Contact Form:', selectedFeatures.contactForm);
      console.log('  📱 Social Media:', selectedFeatures.socialMedia);
      console.log('==========================================');

      const startResponse = await fetch(`${DIRECT_BACKEND_URL}/api/generate/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: description,
          business_description: description,
          language: language,
          user_id: user?.id || 'anonymous',
          email: user?.email,  // Pass user email for founder bypass
          images: allImages.length > 0 ? allImages : undefined,  // Send uploaded images with names
          gallery_metadata: uploadedImages.gallery,  // Pass full gallery metadata separately for AI context
          features: selectedFeatures,  // Pass selected features
          business_type: businessType === 'auto' ? null : businessType,  // Pass business type for dynamic categories
          // STRICT IMAGE CONTROL: Send explicit image choice
          image_choice: finalImageChoice,
          color_mode: colorMode,
          // Template gallery: pass selected design template if any
          template_id: selectedTemplateId || undefined,
          delivery: selectedFeatures.deliverySystem ? {
            area: deliveryArea,
            fee: deliveryFee,
            minimum: minimumOrder,
            hours: deliveryHours
          } : null,
          address: fullAddress || null,
          social_media: selectedFeatures.socialMedia ? {
            instagram: instagram,
            facebook: facebook,
            tiktok: tiktok
          } : null,
          payment: {
            cod: paymentMethods.cod,
            qr: paymentMethods.qr,
            qr_image: paymentQRPreview || null
          },
          fulfillment: {
            delivery: fulfillment.delivery,
            delivery_fee: fulfillment.deliveryFee,
            min_order: fulfillment.minOrder,
            delivery_area: fulfillment.deliveryArea,
            pickup: fulfillment.pickup,
            pickup_address: fulfillment.pickupAddress
          }
        }),
      });

      if (!startResponse.ok) {
        const errorData = await startResponse.json();

        // Handle subscription limit reached from backend
        if (startResponse.status === 403 && errorData.error === 'subscription_limit_reached') {
          setLimitModalData({
            resourceType: 'website',
            currentUsage: errorData.current_usage || 0,
            limit: errorData.limit || 1,
            canBuyAddon: errorData.can_buy_addon || false,
            addonPrice: errorData.addon_price
          })
          setShowLimitModal(true)
          setLoading(false)
          return
        }

        // Check if content was blocked
        if (errorData.blocked || errorData.detail?.includes('tidak dibenarkan') || errorData.detail?.includes('mencurigakan')) {
          throw new Error(errorData.detail || '⚠️ Maaf, kandungan ini tidak dibenarkan. Sorry, this content is not allowed.');
        }
        throw new Error(errorData.error || errorData.detail || 'Failed to start generation');
      }

      const startData = await startResponse.json();
      const jobId = startData.job_id;

      // CRITICAL: Store job ID in state so we track which job we're polling
      setCurrentJobId(jobId);
      console.log('✅ Job started:', jobId, '- Stored in state');

      // Step 2: Poll for results
      const maxAttempts = 200; // 200 attempts x 3 seconds = 10 minutes max (increased from 5 min for complex sites)
      let attempt = 0;

      // CRITICAL: Store interval in ref so it can be cleared on retry
      pollIntervalRef.current = setInterval(async () => {
        attempt++;

        if (attempt > maxAttempts) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          const stuckInfo = progress > 0 ? ` (stuck at ${progress}%)` : '';
          setError(`Generation timed out after 10 minutes${stuckInfo}. Job: ${jobId.slice(0, 8)}. Please try again.`);
          console.error(`❌ Generation timeout - Job: ${jobId}, Progress: ${progress}%`);
          // Keep loading=true so the modal stays open with retry button
          return;
        }

        try {
          // Add cache-busting timestamp
          const statusResponse = await fetch(`${DIRECT_BACKEND_URL}/api/generate/status/${jobId}?t=${Date.now()}`);

          if (!statusResponse.ok) {
            console.warn('Status check failed, retrying...', statusResponse.status, statusResponse.statusText);
            return; // Continue polling
          }

          const statusData = await statusResponse.json();

          // DEBUG: Log full response details
          console.log('=== POLL RESPONSE ===');
          console.log('Status:', statusData.status);
          console.log('Progress:', statusData.progress);
          console.log('Polled at:', statusData.polled_at);
          console.log('DB updated_at:', statusData.updated_at);
          console.log('Has variants:', statusData.variants?.length || 0);
          console.log('Has HTML:', statusData.html?.length || 0);
          console.log('=====================');

          // Update progress bar
          const newProgress = statusData.progress || 0;
          setProgress(newProgress);

          // STALE PROGRESS DETECTION: Warn if progress hasn't changed for 10+ polls (30+ seconds)
          if (newProgress === lastProgress && newProgress > 0 && newProgress < 100) {
            staleCheckRef.current += 1;
            if (staleCheckRef.current >= 10 && !staleWarning) {
              console.warn(`⚠️ Progress stuck at ${newProgress}% for ${staleCheckRef.current * 3} seconds`);
              setStaleWarning(true);
            }
          } else {
            staleCheckRef.current = 0;
            setStaleWarning(false);
            setLastProgress(newProgress);
            setLastProgressUpdate(new Date());
          }

          if (statusData.status === 'completed') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            console.log('✅ Generation complete!');

            // Set progress to 100% FIRST (before hiding modal)
            setProgress(100);

            // Handle completed job - backend returns 'variants' not 'styles'
            if (statusData.variants?.length > 0) {
              // Map variants to styleVariations format
              const variations = statusData.variants.map((v: any) => ({
                style: v.style,
                html: v.html,
                preview_image: v.preview_image,
                thumbnail: v.thumbnail,
                social_preview: v.social_preview
              }));
              setStyleVariations(variations);
              setSelectedStyle(null);
              console.log(`✅ Loaded ${variations.length} style variations`);
            } else if (statusData.styles?.length > 0) {
              // Fallback for backwards compatibility
              setStyleVariations(statusData.styles);
              setSelectedStyle(null);
            } else if (statusData.html) {
              setStyleVariations([{ style: 'modern', html: statusData.html }]);
              setSelectedStyle(null);
            }

            // Hide loading modal AFTER setting progress to 100%
            setLoading(false);
          } else if (statusData.status === 'failed') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            setError(statusData.error || 'Generation failed. Please try again.');
            // Keep loading=true so the modal stays open with retry button
            // User can click Cancel or Try Again in the modal
          }
          // If status is still 'processing', continue polling
        } catch (pollError: any) {
          console.warn('Poll error:', pollError);
          // Continue polling on error
        }
      }, 3000); // Poll every 3 seconds

    } catch (err: any) {
      console.error('Generation error:', err);
      setError(err.message || 'Error connecting to server. Please check your internet connection and try again.');
      // Keep loading=true so the modal stays open with retry button
      // User can click Cancel or Try Again in the modal
    }
  };

  const handleSelectVariation = (variation: StyleVariation) => {
    setSelectedStyle(variation.style)
    setGeneratedHtml(variation.html)
  }

  const handleBackToVariations = () => {
    setSelectedStyle(null)
    setGeneratedHtml('')
  }

  const handleShare = async () => {
    const currentVariation = styleVariations.find(v => v.style === selectedStyle)
    if (navigator.share && currentVariation) {
      try {
        await navigator.share({
          title: `${projectName || 'My Website'} - ${selectedStyle?.toUpperCase()} Style`,
          text: 'Check out my AI-generated website design!',
          url: publishedUrl || window.location.href
        })
      } catch (err) {
        console.log('Share cancelled or failed:', err)
      }
    } else {
      const shareUrl = publishedUrl || window.location.href
      navigator.clipboard.writeText(shareUrl)
      alert('Link copied to clipboard!')
    }
  }

  const handleShareSocial = (platform: string) => {
    const url = publishedUrl || window.location.href
    const text = `Check out my AI-generated website design!`
    
    const shareUrls = {
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
      twitter: `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`
    }
    
    const shareUrl = shareUrls[platform as keyof typeof shareUrls]
    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400')
    }
  }

  const handleDownload = () => {
    const blob = new Blob([generatedHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'website.html'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopyHtml = () => {
    navigator.clipboard.writeText(generatedHtml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handlePublish = async () => {
    if (!subdomain || !projectName) {
      setError('Sila isi subdomain dan nama projek')
      return
    }

    // Validate subdomain before publishing
    const cleanSubdomain = subdomain.toLowerCase().replace(/[^a-z0-9-]/g, '')
    const validationError = validateSubdomain(cleanSubdomain)
    if (validationError) {
      setError(validationError)
      setSubdomainError(validationError)
      return
    }

    setError('')

    if (!user) {
      setError('Sila log masuk untuk menerbitkan website')
      return
    }

    // Free-tier gate: free plan can't publish to a subdomain.
    // Uses currentTier already populated by checkSubscriptionStatus().
    // Guarded by !subscriptionLoading so a slow status fetch doesn't
    // misfire on paid users (race: default currentTier is 'free').
    // Backend 403 'subscription_required' catches the race case below.
    if (!subscriptionLoading && currentTier === 'free') {
      setShowPublishModal(false)
      setTargetTier('starter')
      setShowUpgradeModal(true)
      return
    }

    // Check subscription limits before publishing
    const canCreate = await checkWebsiteLimit()
    if (!canCreate) {
      setShowPublishModal(false)
      return // Modal will be shown by checkWebsiteLimit
    }

    // First try to get custom BinaApp token
    let accessToken = getStoredToken()

    // Fallback to Supabase session if no custom token
    if (!accessToken && supabase) {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession()
      if (!sessionError && session?.access_token) {
        accessToken = session.access_token
      }
    }

    if (!accessToken) {
      setError('Sila log masuk semula untuk menerbitkan website')
      return
    }
    setPublishing(true)

    try {
      // Provide backend with stable website id + delivery/menu context (for widget + DB rows)
      const websiteId =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`

      const menuItemsForDelivery = (uploadedImages?.gallery || [])
        .filter(g => !!g?.url)
        .map((g, idx) => ({
          name: g.name || `Menu Item ${idx + 1}`,
          image_url: g.url,
          price: g.price ? parseFloat(g.price) : null
        }))

      const response = await fetch(`${API_BASE_URL}/api/publish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          html_content: generatedHtml,
          subdomain: cleanSubdomain,
          project_name: projectName,
          user_id: user?.id || 'demo-user',
          website_id: websiteId,
          features: selectedFeatures,
          delivery: selectedFeatures.deliverySystem ? {
            area: deliveryArea,
            fee: deliveryFee,
            minimum: minimumOrder,
            hours: deliveryHours
          } : null,
          menu_items: menuItemsForDelivery,
          payment: {
            cod: paymentMethods.cod,
            qr: paymentMethods.qr,
            qr_image: paymentQRPreview || null
          },
          fulfillment: {
            delivery: fulfillment.delivery,
            delivery_fee: fulfillment.deliveryFee,
            min_order: fulfillment.minOrder,
            delivery_area: fulfillment.deliveryArea,
            pickup: fulfillment.pickup,
            pickup_address: fulfillment.pickupAddress
          }
        })
      })

      if (!response.ok) {
        const errorData = await response.json()

        // Handle subscription limit reached from backend enforcement
        if (response.status === 403 && (errorData.error === 'subscription_limit_reached' || errorData.error === 'limit_reached')) {
          setLimitModalData({
            resourceType: 'website',
            currentUsage: errorData.current_usage || 0,
            limit: errorData.limit || 1,
            canBuyAddon: errorData.can_buy_addon || false,
            addonPrice: errorData.addon_price
          })
          setShowLimitModal(true)
          setShowPublishModal(false)
          return
        }

        // Backend free-tier gate (catches race where currentTier hadn't loaded)
        if (response.status === 403 && errorData.error === 'subscription_required') {
          setShowPublishModal(false)
          setTargetTier(errorData.required_plan || 'starter')
          setShowUpgradeModal(true)
          return
        }

        throw new Error(errorData.detail || errorData.message || 'Gagal menerbitkan website')
      }

      const data = await response.json()
      const publishedWebsiteUrl = data.url

      // Backend publish now upserts `websites` + delivery tables (service role),
      // so we no longer duplicate inserts from the client.
      toast.success('Website berjaya diterbitkan!')

      setPublishedUrl(publishedWebsiteUrl)
      setShowPublishModal(false)
    } catch (err: any) {
      setError(err.message || 'Gagal menerbitkan website. Sila cuba lagi.')
    } finally {
      setPublishing(false)
    }
  }

  const fillExample = (example: typeof EXAMPLE_DESCRIPTIONS[0]) => {
    setDescription(example.text)
    setLanguage(example.lang as 'ms' | 'en')
  }

  return (
    <div className="bg-create grain font-geist" style={{ minHeight: '100vh', color: '#F5F5FA' }}>
      {/* ── Nav ── */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', background: 'rgba(5,5,12,.72)', borderBottom: '1px solid rgba(255,255,255,.06)' }}>
        <div className="shell-create" style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
            <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'inherit' }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg, #6B5CFF, #4F3DFF)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 16px rgba(79,61,255,.4), inset 0 1px 0 rgba(255,255,255,.2)', position: 'relative', overflow: 'hidden' }}>
                <Sparkles size={15} color="#fff" />
                <span style={{ position: 'absolute', top: 3, right: 3, width: 4, height: 4, borderRadius: '50%', background: '#C7FF3D', boxShadow: '0 0 6px #C7FF3D' }} />
              </div>
              <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.025em' }}>binaapp</span>
            </Link>
            <div className="hidden sm:flex" style={{ gap: 4, fontSize: 14 }}>
              <span style={{ padding: '8px 12px', borderRadius: 8, color: '#F5F5FA', background: 'rgba(255,255,255,.05)', fontWeight: 500 }}>Create</span>
              <Link href="/dashboard" style={{ padding: '8px 12px', borderRadius: 8, color: '#86869A', textDecoration: 'none' }}>My sites</Link>
              <Link href="/create/templates" style={{ padding: '8px 12px', borderRadius: 8, color: '#86869A', textDecoration: 'none' }}>
                {selectedTemplateId ? `Template: ${selectedTemplateId.replace(/_/g, ' ')}` : 'Templates'}
              </Link>
              <Link href="/dashboard/billing" style={{ padding: '8px 12px', borderRadius: 8, color: '#86869A', textDecoration: 'none' }}>Pricing</Link>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="pill pill-volt" style={{ cursor: 'pointer', padding: '4px 10px', fontSize: 10 }} onClick={() => setLanguage(language === 'ms' ? 'en' : 'ms')}>
              <span className="led" /> {language === 'ms' ? 'BM' : 'EN'}
            </div>
            {!authLoading && (
              user ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button
                    onClick={handleLogout}
                    style={{ padding: '8px 10px', fontSize: 12, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 8, color: '#B8B8C8', cursor: 'pointer' }}
                  >
                    Log Keluar
                  </button>
                  <Link href="/profile" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px 4px 4px', background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 999, textDecoration: 'none', color: 'inherit' }}>
                    <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'linear-gradient(135deg, #C7FF3D, #4F3DFF)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#05050C' }}>
                      {(user.email?.[0] || 'U').toUpperCase()}
                    </div>
                    <span style={{ fontSize: 13, color: '#B8B8C8' }}>{user.user_metadata?.full_name || user.email?.split('@')[0] || 'User'}</span>
                  </Link>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Link href="/login" style={{ padding: '8px 12px', fontSize: 13, color: '#86869A', textDecoration: 'none' }}>Log Masuk</Link>
                  <Link href="/register" className="cr-btn" style={{ padding: '8px 14px', fontSize: 13, background: 'linear-gradient(180deg, #6B5CFF, #4F3DFF)', color: '#fff', textDecoration: 'none', borderRadius: 12, boxShadow: '0 0 0 1px rgba(107,92,255,.5), 0 1px 0 rgba(255,255,255,.18) inset, 0 8px 24px rgba(79,61,255,.35)' }}>
                    Daftar
                  </Link>
                </div>
              )
            )}
          </div>
        </div>
      </nav>

      <main className="shell-create" style={{ paddingTop: 32, paddingBottom: 80, position: 'relative', zIndex: 2 }}>
        {/* ── Limit Reached Banner (top-level, always visible) ── */}
        {isAtLimit && (
          <div className="banner-accent float-in" style={{ background: 'linear-gradient(90deg, rgba(255,176,32,.06), transparent)', border: '1px solid rgba(255,176,32,.22)' }}>
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#FFB020', boxShadow: '0 0 14px #FFB020' }} />
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,176,32,.1)', border: '1px solid rgba(255,176,32,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#FFB020', flexShrink: 0 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2 4 14h7l-2 8 9-12h-7l2-8Z"/></svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA' }}>Had website dicapai</div>
              <div style={{ fontSize: 12, color: '#86869A', marginTop: 2 }}>Upgrade plan atau beli addon untuk mencipta website baru.</div>
            </div>
            <Link href="/dashboard/billing" style={{ height: 32, fontSize: 12, padding: '0 12px', display: 'inline-flex', alignItems: 'center', borderRadius: 8, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,176,32,.4)', color: '#F5F5FA', textDecoration: 'none', cursor: 'pointer', whiteSpace: 'nowrap' }}>
              Upgrade
            </Link>
          </div>
        )}

        {/* ── Hero Card ── */}
        <section className="cr-card cr-card-hairline" style={{ padding: 32, position: 'relative', overflow: 'hidden', marginBottom: 32 }}>
          <div className="dotgrid" style={{ position: 'absolute', inset: 0, opacity: .4, maskImage: 'radial-gradient(ellipse at top right, black 20%, transparent 70%)', WebkitMaskImage: 'radial-gradient(ellipse at top right, black 20%, transparent 70%)' }} />
          <div style={{ position: 'absolute', top: -100, right: -80, width: 320, height: 320, borderRadius: '50%', background: 'radial-gradient(circle, rgba(79,61,255,.22), transparent 60%)', pointerEvents: 'none' }} />
          <div style={{ position: 'relative' }}>
            <div className="pill pill-volt ai-pulse" style={{ marginBottom: 20 }}>
              <span className="led" /> AI ready · powered by claude
            </div>
            <h1 style={{ fontSize: 56, fontWeight: 700, letterSpacing: '-0.045em', lineHeight: 1, margin: 0, color: '#F5F5FA' }}>
              Bina, jual,<br />
              <span style={{ background: 'linear-gradient(120deg, #C7FF3D 30%, #6B5CFF 70%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>bebas.</span>
            </h1>
            <p style={{ color: '#B8B8C8', fontSize: 18, lineHeight: 1.5, margin: '20px 0 28px', maxWidth: 540 }}>
              Cerita pasal kedai anda. AI bina website siap dalam 60 saat — terima pesanan, jual menu, semua dalam satu tempat.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              <span className="eyebrow" style={{ marginRight: 4 }}>Try:</span>
              {EXAMPLE_DESCRIPTIONS.slice(0, 4).map((ex) => (
                <button key={ex.title} className="chip" onClick={() => fillExample(ex)}>
                  <Sparkles size={12} /> {ex.title}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 14, marginTop: 24, fontSize: 13, color: '#5A5A6E' }}>
              <Link href="/create/templates" style={{ color: '#86869A', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <Layout size={14} /> Browse templates
              </Link>
              <span style={{ color: '#3A3A4A' }}>·</span>
              <a href="/menu-designer" style={{ color: '#86869A', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h6"/></svg>
                Create print menu
              </a>
            </div>
          </div>
        </section>

        {!generatedHtml && styleVariations.length === 0 ? (
          <div className="max-w-4xl mx-auto">
            {/* Subscription Required Banner */}
            {!subscriptionLoading && hasActiveSubscription === false && user && (
              <div className="banner-accent float-in" style={{ background: 'linear-gradient(90deg, rgba(199,255,61,.06), transparent)', border: '1px solid rgba(199,255,61,.22)' }}>
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#C7FF3D', boxShadow: '0 0 14px #C7FF3D' }} />
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(199,255,61,.1)', border: '1px solid rgba(199,255,61,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#C7FF3D', flexShrink: 0 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="m3 8 4 4 5-7 5 7 4-4v10H3z"/></svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA' }}>Langganan diperlukan</div>
                  <div style={{ fontSize: 12, color: '#86869A', marginTop: 2 }}>Mula dari RM 5/bulan — batal bila-bila masa.</div>
                </div>
                <a href="/dashboard/billing" style={{ height: 32, fontSize: 12, padding: '0 12px', display: 'inline-flex', alignItems: 'center', borderRadius: 8, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(199,255,61,.3)', color: '#F5F5FA', textDecoration: 'none', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  Pilih Plan
                </a>
              </div>
            )}

            {/* Not Logged In Banner */}
            {!authLoading && !user && (
              <div className="banner-accent float-in" style={{ background: 'linear-gradient(90deg, rgba(63,184,255,.06), transparent)', border: '1px solid rgba(63,184,255,.22)' }}>
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#3FB8FF', boxShadow: '0 0 14px #3FB8FF' }} />
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(63,184,255,.1)', border: '1px solid rgba(63,184,255,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3FB8FF', flexShrink: 0 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 1 1 8 0v4"/></svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA' }}>Sign in to save your work</div>
                  <div style={{ fontSize: 12, color: '#86869A', marginTop: 2 }}>Continue as guest — but save your progress with a free account.</div>
                </div>
                <a href="/login?redirect=/create" style={{ height: 32, fontSize: 12, padding: '0 12px', display: 'inline-flex', alignItems: 'center', borderRadius: 8, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(63,184,255,.3)', color: '#F5F5FA', textDecoration: 'none', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  Sign in
                </a>
              </div>
            )}

            {/* Limit Warning Banner */}
            {limitWarning && (
              <div className="banner-accent float-in" style={{ background: 'linear-gradient(90deg, rgba(255,176,32,.06), transparent)', border: '1px solid rgba(255,176,32,.22)' }}>
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#FFB020', boxShadow: '0 0 14px #FFB020' }} />
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,176,32,.1)', border: '1px solid rgba(255,176,32,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#FFB020', flexShrink: 0 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2 4 14h7l-2 8 9-12h-7l2-8Z"/></svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA' }}>{limitWarning}</div>
                  <div style={{ fontSize: 12, color: '#86869A', marginTop: 2 }}>Upgrade untuk lebih banyak website.</div>
                </div>
                <a href="/dashboard/billing" style={{ height: 32, fontSize: 12, padding: '0 12px', display: 'inline-flex', alignItems: 'center', borderRadius: 8, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,176,32,.3)', color: '#F5F5FA', textDecoration: 'none', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  Upgrade
                </a>
              </div>
            )}

            {/* ── 01 Language & Theme ── */}
            <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 16 }}>01 — BAHASA & TEMA</div>

              {/* Language toggle */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#B8B8C8', marginBottom: 10 }}>Bahasa / Language</div>
                <div style={{ display: 'inline-flex', gap: 8 }}>
                  <button
                    onClick={() => setLanguage('ms')}
                    className={language === 'ms' ? 'cr-toggle cr-toggle-active' : 'cr-toggle'}
                  >
                    Bahasa Malaysia
                  </button>
                  <button
                    onClick={() => setLanguage('en')}
                    className={language === 'en' ? 'cr-toggle cr-toggle-active' : 'cr-toggle'}
                  >
                    English
                  </button>
                </div>
              </div>

              {/* Color mode toggle */}
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#B8B8C8', marginBottom: 10 }}>Tema Warna / Color Theme</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <button
                    type="button"
                    onClick={() => setColorMode('light')}
                    className={colorMode === 'light' ? 'cr-toggle cr-toggle-active' : 'cr-toggle'}
                    style={{ padding: '14px 16px', flexDirection: 'column', gap: 4 }}
                  >
                    <span style={{ fontSize: 22 }}>&#9728;&#65039;</span>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>Cerah / Light</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setColorMode('dark')}
                    className={colorMode === 'dark' ? 'cr-toggle cr-toggle-active' : 'cr-toggle'}
                    style={{ padding: '14px 16px', flexDirection: 'column', gap: 4 }}
                  >
                    <span style={{ fontSize: 22 }}>&#127769;</span>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>Gelap / Dark</span>
                  </button>
                </div>
              </div>
            </div>

            {/* ── 02 Business Type ── */}
            <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 16 }}>02 — JENIS PERNIAGAAN</div>
              <div style={{ fontSize: 13, color: '#86869A', marginBottom: 14 }}>Pilih jenis perniagaan anda</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
                {[
                  { id: 'auto' as const, icon: '🔍', label: 'Auto Detect', desc: 'Kesan automatik', recommended: true },
                  { id: 'food' as const, icon: '🍛', label: 'Restoran / Makanan', desc: 'Nasi, Lauk, Minuman', recommended: false },
                  { id: 'clothing' as const, icon: '👗', label: 'Pakaian / Butik', desc: 'Baju, Tudung, Aksesori', recommended: false },
                  { id: 'salon' as const, icon: '💇', label: 'Salon / Spa', desc: 'Potong, Rawatan, Warna', recommended: false },
                  { id: 'services' as const, icon: '🔧', label: 'Servis / Repair', desc: 'Perkhidmatan, Pakej', recommended: false },
                  { id: 'bakery' as const, icon: '🎂', label: 'Bakeri / Kek', desc: 'Kek, Pastri, Cookies', recommended: false },
                  { id: 'general' as const, icon: '🛒', label: 'Lain-lain', desc: 'Produk Umum', recommended: false }
                ].map(type => (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setBusinessType(type.id)}
                    className={businessType === type.id ? 'cr-type-card cr-type-card-active' : 'cr-type-card'}
                    style={{ position: 'relative' }}
                  >
                    {type.recommended && (
                      <span style={{ position: 'absolute', top: 8, right: 8, fontSize: 9, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', padding: '2px 6px', borderRadius: 6, background: 'rgba(199,255,61,.12)', color: '#C7FF3D', border: '1px solid rgba(199,255,61,.25)' }}>REC</span>
                    )}
                    <span style={{ fontSize: 28, display: 'block', marginBottom: 6 }}>{type.icon}</span>
                    <span style={{ fontSize: 13, fontWeight: 500, color: '#F5F5FA', display: 'block' }}>{type.label}</span>
                    <span style={{ fontSize: 11, color: '#5A5A6E', marginTop: 4, display: 'block' }}>{type.desc}</span>
                  </button>
                ))}
              </div>
              <div style={{ fontSize: 12, color: '#5A5A6E', marginTop: 12 }}>
                {businessType === 'auto' && 'Sistem akan mengesan jenis perniagaan anda secara automatik dari deskripsi'}
                {businessType === 'food' && 'Butang: "Pesan Delivery" | Kategori: Nasi, Lauk, Minuman'}
                {businessType === 'clothing' && 'Butang: "Beli Sekarang" | Pilihan saiz & warna | Penghantaran'}
                {businessType === 'salon' && 'Butang: "Tempah Sekarang" | Tarikh temujanji & pilih staff'}
                {businessType === 'services' && 'Butang: "Tempah Servis" | Tarikh & lokasi servis'}
                {businessType === 'bakery' && 'Butang: "Tempah Kek" | Pilihan saiz & mesej atas kek'}
                {businessType === 'general' && 'Butang: "Beli Sekarang" | Pilihan penghantaran'}
              </div>
            </div>

            {/* ── 03 Multi-style ── */}
            <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20, background: 'linear-gradient(180deg, rgba(79,61,255,.06), rgba(255,255,255,0)), #0F0F1A' }}>
              <label className="cr-check" style={{ marginBottom: multiStyle ? 14 : 0 }}>
                <input
                  type="checkbox"
                  checked={multiStyle}
                  onChange={(e) => setMultiStyle(e.target.checked)}
                />
                <span className="cr-check-box" />
                <div>
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#F5F5FA' }}>
                    Generate Multiple Styles
                  </span>
                  <span style={{ marginLeft: 8, fontSize: 10, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase' as const, padding: '2px 7px', borderRadius: 6, background: 'rgba(199,255,61,.12)', color: '#C7FF3D', border: '1px solid rgba(199,255,61,.25)' }}>REC</span>
                  <p style={{ fontSize: 13, color: '#86869A', marginTop: 4 }}>
                    Get 3 design variations (Modern, Minimal, Bold) and choose your favorite
                  </p>
                </div>
              </label>

              {multiStyle && (
                <label className="cr-check" style={{ marginLeft: 32 }}>
                  <input
                    type="checkbox"
                    checked={generatePreviews}
                    onChange={(e) => setGeneratePreviews(e.target.checked)}
                  />
                  <span className="cr-check-box" />
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 500, color: '#B8B8C8' }}>
                      Generate Preview Thumbnails
                    </span>
                    <p style={{ fontSize: 12, color: '#5A5A6E', marginTop: 2 }}>
                      Takes 10-15 seconds longer but shows better previews
                    </p>
                  </div>
                </label>
              )}
            </div>

            {/* ── 04 Description ── */}
            <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 16 }}>04 — CERITAKAN PERNIAGAAN ANDA</div>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={
                  language === 'ms'
                    ? 'Contoh: Saya ada kedai runcit di Shah Alam yang jual barangan harian, makanan, dan minuman. Harga berpatutan dari RM1. Lokasi di Seksyen 7 Shah Alam. Telefon 019-1234567. Buka 7am-10pm setiap hari...'
                    : 'Example: I have a coffee shop in Kuala Lumpur serving specialty coffee, cakes, and light meals. Prices from RM8. Located at TTDI. Contact via WhatsApp 012-3456789. Open daily 8am-6pm...'
                }
                className="cr-textarea"
                style={{ width: '100%', height: 220, resize: 'none' }}
              />
              <div className="cr-counter" style={{ color: description.length >= 100 ? '#34D399' : description.length >= 50 ? '#C7FF3D' : '#5A5A6E' }}>
                <span className="num">{description.length}</span> characters
              </div>
            </div>

            <VisualImageUpload onImagesUploaded={setUploadedImages} />

            {/* ── 05 Image Source ── */}
            <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 16 }}>05 — SUMBER GAMBAR</div>
              <div style={{ fontSize: 13, color: '#86869A', marginBottom: 14 }}>Pilih bagaimana anda mahu gambar dalam website anda</div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Option 1: No Images */}
                <label className={imageChoice === 'none' ? 'cr-radio cr-radio-active' : 'cr-radio'}>
                  <input type="radio" name="imageChoice" value="none" checked={imageChoice === 'none'} onChange={() => setImageChoice('none')} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                  <span style={{ fontSize: 22, flexShrink: 0 }}>📝</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', display: 'block' }}>Tiada Gambar</span>
                    <span style={{ fontSize: 12, color: '#5A5A6E', marginTop: 2, display: 'block' }}>Website teks sahaja, tanpa gambar</span>
                  </div>
                </label>

                {/* Option 2: Upload Own Images */}
                <label className={imageChoice === 'upload' ? 'cr-radio cr-radio-active' : 'cr-radio'}>
                  <input type="radio" name="imageChoice" value="upload" checked={imageChoice === 'upload'} onChange={() => setImageChoice('upload')} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                  <span style={{ fontSize: 22, flexShrink: 0 }}>📷</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', display: 'block' }}>Muat Naik Gambar Sendiri</span>
                    <span style={{ fontSize: 12, color: '#5A5A6E', marginTop: 2, display: 'block' }}>Gunakan gambar yang anda upload di atas</span>
                  </div>
                  {uploadedImages.gallery.length > 0 && (
                    <span style={{ fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 8, background: 'rgba(199,255,61,.12)', color: '#C7FF3D', border: '1px solid rgba(199,255,61,.25)', whiteSpace: 'nowrap' }}>
                      {uploadedImages.gallery.length} dimuat naik
                    </span>
                  )}
                </label>

                {/* Option 3: Generate AI Images */}
                <label className={imageChoice === 'ai' ? 'cr-radio cr-radio-active' : 'cr-radio'}>
                  <input type="radio" name="imageChoice" value="ai" checked={imageChoice === 'ai'} onChange={() => setImageChoice('ai')} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                  <span style={{ fontSize: 22, flexShrink: 0 }}>✨</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', display: 'block' }}>Jana Gambar AI</span>
                    <span style={{ fontSize: 12, color: '#5A5A6E', marginTop: 2, display: 'block' }}>AI akan jana gambar untuk perniagaan anda</span>
                  </div>
                  <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase' as const, padding: '2px 7px', borderRadius: 6, background: 'rgba(107,92,255,.15)', color: '#BAB0FF', border: '1px solid rgba(107,92,255,.3)' }}>PREMIUM</span>
                </label>
              </div>

              {/* Warning if upload selected but no images */}
              {imageChoice === 'upload' && uploadedImages.gallery.length === 0 && !uploadedImages.hero && (
                <div className="banner-accent float-in" style={{ marginTop: 14, marginBottom: 0, background: 'linear-gradient(90deg, rgba(255,176,32,.06), transparent)', border: '1px solid rgba(255,176,32,.22)' }}>
                  <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#FFB020' }} />
                  <span style={{ fontSize: 13, color: '#FFB020' }}>Anda belum muat naik gambar. Sila muat naik gambar di bahagian atas atau pilih pilihan lain.</span>
                </div>
              )}
            </div>

            {/* ── 06 Features ── */}
            <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 16 }}>06 — CIRI-CIRI WEBSITE</div>
              <div style={{ fontSize: 13, color: '#86869A', marginBottom: 14 }}>Pilih apa yang anda mahu dalam website anda</div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { key: 'whatsapp' as const, icon: '💬', label: 'WhatsApp' },
                  { key: 'googleMap' as const, icon: '📍', label: 'Google Map' },
                  { key: 'deliverySystem' as const, icon: '🛵', label: 'Delivery Sendiri' },
                  { key: 'contactForm' as const, icon: '📧', label: 'Borang Hubungi' },
                  { key: 'socialMedia' as const, icon: '📱', label: 'Social Media' },
                  { key: 'priceList' as const, icon: '💰', label: 'Senarai Harga' },
                ].map(f => (
                  <label key={f.key} className={selectedFeatures[f.key] ? 'cr-feature-pill cr-feature-active' : 'cr-feature-pill'}>
                    <input
                      type="checkbox"
                      checked={selectedFeatures[f.key]}
                      onChange={(e) => setSelectedFeatures({...selectedFeatures, [f.key]: e.target.checked})}
                      style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }}
                    />
                    <span style={{ fontSize: 18 }}>{f.icon}</span>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{f.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Google Map expand */}
            {selectedFeatures.googleMap && (
              <div className="cr-sub-card float-in">
                <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', marginBottom: 10 }}>📍 Google Map</div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, color: '#86869A', marginBottom: 6 }}>Alamat Penuh</label>
                  <input
                    type="text"
                    placeholder="cth: 123, Jalan Sultan, Shah Alam, Selangor"
                    className="cr-input"
                    value={fullAddress}
                    onChange={(e) => setFullAddress(e.target.value)}
                  />
                </div>
              </div>
            )}

            {/* Social Media expand */}
            {selectedFeatures.socialMedia && (
              <div className="cr-sub-card float-in">
                <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', marginBottom: 10 }}>📱 Social Media</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <input type="text" placeholder="Instagram: @username" className="cr-input" value={instagram} onChange={(e) => setInstagram(e.target.value)} />
                  <input type="text" placeholder="Facebook: page name or URL" className="cr-input" value={facebook} onChange={(e) => setFacebook(e.target.value)} />
                  <input type="text" placeholder="TikTok: @username" className="cr-input" value={tiktok} onChange={(e) => setTiktok(e.target.value)} />
                </div>
              </div>
            )}

            {/* Delivery Settings expand */}
            {selectedFeatures.deliverySystem && (
              <div className="cr-sub-card float-in">
                <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', marginBottom: 10 }}>🛵 Tetapan Delivery</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, color: '#86869A', marginBottom: 6 }}>Caj Delivery (RM)</label>
                    <input type="number" placeholder="5.00" step="0.50" className="cr-input" value={fulfillment.deliveryFee} onChange={(e) => setFulfillment({...fulfillment, deliveryFee: e.target.value})} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, color: '#86869A', marginBottom: 6 }}>Min. Order (RM)</label>
                    <input type="number" placeholder="20.00" step="1" className="cr-input" value={fulfillment.minOrder} onChange={(e) => setFulfillment({...fulfillment, minOrder: e.target.value})} />
                  </div>
                  <div style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', fontSize: 12, color: '#86869A', marginBottom: 6 }}>Kawasan Delivery</label>
                    <input type="text" placeholder="Shah Alam, Klang, Subang" className="cr-input" value={fulfillment.deliveryArea} onChange={(e) => setFulfillment({...fulfillment, deliveryArea: e.target.value})} />
                  </div>
                </div>

                {/* Self Pickup */}
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid rgba(255,255,255,.06)' }}>
                  <label className="cr-check">
                    <input type="checkbox" checked={fulfillment.pickup} onChange={(e) => setFulfillment({...fulfillment, pickup: e.target.checked})} />
                    <span className="cr-check-box" />
                    <span style={{ fontSize: 18 }}>🏪</span>
                    <div style={{ flex: 1 }}>
                      <span style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', display: 'block' }}>Self Pickup</span>
                      <span style={{ fontSize: 12, color: '#5A5A6E', display: 'block' }}>Pelanggan ambil di kedai</span>
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#34D399' }}>FREE</span>
                  </label>

                  {fulfillment.pickup && (
                    <div style={{ marginTop: 10, marginLeft: 32 }}>
                      <label style={{ display: 'block', fontSize: 12, color: '#86869A', marginBottom: 6 }}>Alamat Pickup</label>
                      <input type="text" placeholder="No. 123, Jalan ABC, Shah Alam" className="cr-input" value={fulfillment.pickupAddress} onChange={(e) => setFulfillment({...fulfillment, pickupAddress: e.target.value})} />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── 07 Payment ── */}
            <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20 }}>
              <div className="eyebrow" style={{ marginBottom: 16 }}>07 — PEMBAYARAN</div>
              <div style={{ fontSize: 13, color: '#86869A', marginBottom: 14 }}>Pilih cara pembayaran yang anda terima</div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: paymentMethods.qr ? 16 : 0 }}>
                {/* COD */}
                <label className={paymentMethods.cod ? 'cr-radio cr-radio-active' : 'cr-radio'}>
                  <input type="checkbox" checked={paymentMethods.cod} onChange={(e) => setPaymentMethods({...paymentMethods, cod: e.target.checked})} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                  <span style={{ fontSize: 22, flexShrink: 0 }}>💵</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', display: 'block' }}>Cash on Delivery (COD)</span>
                    <span style={{ fontSize: 12, color: '#5A5A6E', marginTop: 2, display: 'block' }}>Bayar tunai bila terima</span>
                  </div>
                  <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase' as const, padding: '2px 7px', borderRadius: 6, background: 'rgba(199,255,61,.12)', color: '#C7FF3D', border: '1px solid rgba(199,255,61,.25)' }}>POPULAR</span>
                </label>

                {/* QR Payment */}
                <label className={paymentMethods.qr ? 'cr-radio cr-radio-active' : 'cr-radio'}>
                  <input type="checkbox" checked={paymentMethods.qr} onChange={(e) => setPaymentMethods({...paymentMethods, qr: e.target.checked})} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                  <span style={{ fontSize: 22, flexShrink: 0 }}>📱</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA', display: 'block' }}>QR Payment</span>
                    <span style={{ fontSize: 12, color: '#5A5A6E', marginTop: 2, display: 'block' }}>DuitNow / TNG / Bank QR</span>
                  </div>
                </label>
              </div>

              {/* QR Upload */}
              {paymentMethods.qr && (
                <div className="cr-sub-card float-in" style={{ marginTop: 0, marginBottom: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#B8B8C8', marginBottom: 10 }}>Muat Naik QR Pembayaran Anda</div>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                    {/* QR Upload Box */}
                    <div style={{ width: 120, height: 120, border: '2px dashed rgba(255,255,255,.12)', borderRadius: 14, background: 'rgba(255,255,255,.02)', flexShrink: 0, overflow: 'hidden' }}>
                      <label style={{ cursor: 'pointer', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                        <input type="file" accept="image/*" style={{ display: 'none' }} onChange={handleQRUpload} />
                        {paymentQRPreview ? (
                          <img src={paymentQRPreview} alt="Payment QR" style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 4, borderRadius: 12 }} />
                        ) : (
                          <>
                            <span style={{ fontSize: 28, marginBottom: 4 }}>📷</span>
                            <span style={{ fontSize: 11, color: '#5A5A6E' }}>Upload QR</span>
                          </>
                        )}
                      </label>
                    </div>

                    {/* Instructions */}
                    <div style={{ flex: 1, fontSize: 13, color: '#86869A' }}>
                      <div style={{ fontSize: 13, fontWeight: 500, color: '#B8B8C8', marginBottom: 8 }}>Cara mendapatkan QR:</div>
                      <ol style={{ listStyleType: 'decimal', paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <li>Buka app bank / TNG / DuitNow</li>
                        <li>Pergi ke &quot;Receive Money&quot; atau &quot;My QR&quot;</li>
                        <li>Screenshot QR code anda</li>
                        <li>Upload di sini</li>
                      </ol>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={loading || description.length < 10 || isAtLimit}
              className="w-full btn btn-primary text-lg py-4 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Generating your website...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 mr-2" />
                  Generate Website with AI
                </>
              )}
            </button>

            {loading && (
              <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
                <div className="bg-gray-900 rounded-2xl p-8 max-w-2xl w-full mx-4">
                  {error ? (
                    /* Error State in Modal */
                    <div className="text-center">
                      <div className="mb-6">
                        <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                          <span className="text-4xl">❌</span>
                        </div>
                        <h3 className="text-2xl font-bold text-white mb-2">Generation Failed</h3>
                        <p className="text-gray-400 mb-4">Something went wrong while generating your website</p>
                      </div>

                      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-left">
                        <p className="text-red-400 text-sm">{error}</p>
                      </div>

                      <div className="flex gap-3 justify-center">
                        <button
                          onClick={() => {
                            setLoading(false);
                            setError('');
                            setProgress(0);
                          }}
                          className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => {
                            setError('');
                            setProgress(0);
                            handleGenerate();
                          }}
                          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition flex items-center gap-2"
                        >
                          <span>🔄</span> Try Again
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Normal Loading State */
                    <>
                      <div className="mb-6 relative">
                        <CodeAnimation />
                        <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full animate-ping"></div>
                      </div>

                      <div className="text-white mb-4 text-center">
                        <div className="flex items-center justify-center gap-2 mb-2">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                          <h3 className="text-2xl font-bold">Building your website...</h3>
                        </div>
                        <p className="text-gray-400">
                          AI is writing production-ready HTML code for you
                        </p>
                      </div>

                  {/* Progress bar */}
                  <div className="mb-6">
                    <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 transition-all duration-500 ease-out"
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                    <p className="text-center text-blue-400 mt-2 font-semibold">
                      {progress}% Complete
                    </p>
                  </div>

                  <div className="mt-6 space-y-3 text-left max-w-md mx-auto">
                    {/* Step 1: Analyzing (10-25%) */}
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                        progress >= 10 && progress < 30 ? 'bg-blue-500 animate-pulse' :
                        progress >= 30 ? 'bg-green-500' : 'bg-gray-600'
                      }`}></div>
                      <span className={`text-sm ${progress >= 30 ? 'text-green-400' : ''}`}>
                        {progress >= 30 ? '✓ ' : ''}Analyzing your business description...
                      </span>
                    </div>
                    {/* Step 2: Modern Style (30-50%) */}
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                        progress >= 30 && progress < 50 ? 'bg-purple-500 animate-pulse' :
                        progress >= 50 ? 'bg-green-500' : 'bg-gray-600'
                      }`}></div>
                      <span className={`text-sm ${progress >= 50 ? 'text-green-400' : ''}`}>
                        {progress >= 50 ? '✓ ' : ''}Generating Modern style...
                      </span>
                    </div>
                    {/* Step 3: Minimal Style (50-70%) */}
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                        progress >= 50 && progress < 70 ? 'bg-pink-500 animate-pulse' :
                        progress >= 70 ? 'bg-green-500' : 'bg-gray-600'
                      }`}></div>
                      <span className={`text-sm ${progress >= 70 ? 'text-green-400' : ''}`}>
                        {progress >= 70 ? '✓ ' : ''}Generating Minimal style...
                      </span>
                    </div>
                    {/* Step 4: Bold Style (70-90%) */}
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                        progress >= 70 && progress < 90 ? 'bg-orange-500 animate-pulse' :
                        progress >= 90 ? 'bg-green-500' : 'bg-gray-600'
                      }`}></div>
                      <span className={`text-sm ${progress >= 90 ? 'text-green-400' : ''}`}>
                        {progress >= 90 ? '✓ ' : ''}Generating Bold style...
                      </span>
                    </div>
                    {/* Step 5: Finalizing (90-100%) */}
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                        progress >= 90 && progress < 100 ? 'bg-yellow-500 animate-pulse' :
                        progress >= 100 ? 'bg-green-500' : 'bg-gray-600'
                      }`}></div>
                      <span className={`text-sm ${progress >= 100 ? 'text-green-400' : ''}`}>
                        {progress >= 100 ? '✓ ' : ''}Finalizing website...
                      </span>
                    </div>
                  </div>

                  {/* Stale Progress Warning */}
                  {staleWarning && (
                    <div className="mt-4 p-3 bg-yellow-500/20 border border-yellow-500/50 rounded-lg">
                      <p className="text-yellow-400 text-sm text-center">
                        ⚠️ Progress appears to be stuck at {progress}%. The backend may be experiencing issues.
                        <br />
                        <span className="text-xs text-yellow-500">Job may still complete - please wait or try again.</span>
                      </p>
                    </div>
                  )}

                  <p className="text-xs text-gray-500 mt-6 text-center">
                    This usually takes 45-90 seconds. Progress updates every 3 seconds ⏱️
                  </p>

                  {/* Debug: Show Job ID for troubleshooting */}
                  {currentJobId && (
                    <p className="text-xs text-gray-600 mt-2 text-center font-mono">
                      Job: {currentJobId.slice(0, 8)}...
                    </p>
                  )}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : styleVariations.length > 0 && !selectedStyle ? (
          <div className="max-w-7xl mx-auto">
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 text-green-800 font-semibold mb-2">
                <Check className="w-5 h-5" />
                3 Design Variations Generated!
              </div>
              <p className="text-sm text-green-700">
                Template: <span className="font-semibold">{templateUsed}</span> •
                Features: <span className="font-semibold">{detectedFeatures.join(', ')}</span>
              </p>
              <p className="text-sm text-green-700 mt-2">
                Click on any design below to view and customize it
              </p>
            </div>

            <button
              onClick={() => {
                setStyleVariations([])
                setGeneratedHtml('')
                setError('')
                setPublishedUrl('')
              }}
              className="mb-6 btn btn-outline"
            >
              Create Another
            </button>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              {styleVariations.map((variation, idx) => {
                const styleInfo = {
                  modern: {
                    name: 'Modern',
                    icon: '🎨',
                    color: 'from-purple-500 to-blue-500',
                    description: 'Vibrant gradients, glassmorphism, contemporary design'
                  },
                  minimal: {
                    name: 'Minimal',
                    icon: '✨',
                    color: 'from-gray-700 to-gray-900',
                    description: 'Clean, simple, elegant with lots of white space'
                  },
                  bold: {
                    name: 'Bold',
                    icon: '⚡',
                    color: 'from-orange-500 to-red-500',
                    description: 'High contrast, dramatic, attention-grabbing'
                  }
                }[variation.style] || {
                  name: variation.style,
                  icon: '🎯',
                  color: 'from-blue-500 to-indigo-500',
                  description: 'Custom style'
                }

                return (
                  <div
                    key={idx}
                    className="group bg-white rounded-xl shadow-lg overflow-hidden border-2 border-transparent hover:border-primary-500 transition-all duration-300 cursor-pointer transform hover:scale-105"
                    onClick={() => {
                      console.log('Selecting variation:', variation)
                      handleSelectVariation(variation)
                    }}
                  >
                    <div className={`bg-gradient-to-r ${styleInfo.color} p-4 text-white`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-2xl">{styleInfo.icon}</span>
                        <h3 className="text-xl font-bold">{styleInfo.name}</h3>
                      </div>
                      <p className="text-sm opacity-90">{styleInfo.description}</p>
                    </div>

                    <div className="relative bg-gray-100" style={{ height: '400px' }}>
                      {variation.html ? (
                        <iframe
                          srcDoc={variation.html}
                          className="w-full h-full border-0 pointer-events-none"
                          title={`${styleInfo.name} Preview`}
                          sandbox="allow-same-origin"
                          onLoad={() => console.log(`Iframe loaded for ${variation.style}`)}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">
                          <div className="text-center">
                            <p className="text-sm">No preview available</p>
                            <p className="text-xs mt-2">HTML length: {variation.html?.length || 0}</p>
                          </div>
                        </div>
                      )}
                      
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center">
                        <button className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-white text-primary-600 px-6 py-3 rounded-lg font-semibold shadow-lg">
                          <Eye className="w-5 h-5 inline-block mr-2" />
                          View Full Design
                        </button>
                      </div>
                    </div>

                    <div className="p-4 bg-gray-50 text-center">
                      <p className="text-sm text-gray-600">
                        {variation.html ? `Click to view (${Math.round(variation.html.length / 1024)}KB)` : 'No content'}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ) : (
          <div className="max-w-7xl mx-auto">
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 text-green-800 font-semibold mb-2">
                <Check className="w-5 h-5" />
                Website Generated Successfully!
              </div>
              <p className="text-sm text-green-700">
                Template: <span className="font-semibold">{templateUsed}</span> •
                Features: <span className="font-semibold">{detectedFeatures.join(', ')}</span>
                {selectedStyle && (
                  <>
                    {' • '}
                    Style: <span className="font-semibold capitalize">{selectedStyle}</span>
                  </>
                )}
              </p>
            </div>

            {publishedUrl && (
              <div className="mb-6 p-6 bg-blue-50 border-2 border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 text-blue-800 font-bold mb-3 text-lg">
                  🎉 Website Published!
                </div>
                <p className="text-blue-700 mb-3">
                  Your website is now live at:
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={publishedUrl}
                    readOnly
                    className="flex-1 px-4 py-2 bg-white border border-blue-300 rounded-lg"
                  />
                  <a
                    href={publishedUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    View Live
                  </a>
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-3 mb-6">
              {selectedStyle && styleVariations.length > 0 && (
                <button
                  onClick={handleBackToVariations}
                  className="btn btn-outline"
                >
                  ← Back to Variations
                </button>
              )}
              
              <button
                onClick={() => setPreviewMode(previewMode === 'single' ? 'multi' : 'single')}
                className="btn btn-outline"
                title={previewMode === 'single' ? 'View on all devices' : 'View single device'}
              >
                <Layout className="w-4 h-4 mr-2" />
                {previewMode === 'single' ? 'Multi-Device' : 'Single Device'}
              </button>

              <button
                onClick={handleDownload}
                className="btn btn-outline"
              >
                <Download className="w-4 h-4 mr-2" />
                Download HTML
              </button>

              <button
                onClick={handleCopyHtml}
                className="btn btn-outline"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-2" />
                    Copy HTML
                  </>
                )}
              </button>

              <button
                onClick={() => setShowPublishModal(true)}
                className="btn btn-primary"
              >
                <Upload className="w-4 h-4 mr-2" />
                Publish Website
              </button>

              <div className="relative group">
                <button
                  onClick={handleShare}
                  className="btn btn-outline"
                >
                  <Share2 className="w-4 h-4 mr-2" />
                  Share
                </button>
                <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-xl border border-gray-200 p-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10 min-w-[150px]">
                  <button
                    onClick={() => handleShareSocial('whatsapp')}
                    className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded flex items-center gap-2"
                  >
                    <span className="text-xl">💬</span> WhatsApp
                  </button>
                  <button
                    onClick={() => handleShareSocial('facebook')}
                    className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded flex items-center gap-2"
                  >
                    <span className="text-xl">📘</span> Facebook
                  </button>
                  <button
                    onClick={() => handleShareSocial('twitter')}
                    className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded flex items-center gap-2"
                  >
                    <span className="text-xl">🐦</span> Twitter
                  </button>
                  <button
                    onClick={() => handleShareSocial('linkedin')}
                    className="w-full text-left px-3 py-2 hover:bg-gray-100 rounded flex items-center gap-2"
                  >
                    <span className="text-xl">💼</span> LinkedIn
                  </button>
                </div>
              </div>

              <button
                onClick={() => {
                  setGeneratedHtml('')
                  setStyleVariations([])
                  setSelectedStyle(null)
                  setError('')
                  setPublishedUrl('')
                }}
                className="btn btn-outline"
              >
                Create Another
              </button>
            </div>

            {previewMode === 'single' ? (
              <DevicePreview
                htmlContent={generatedHtml}
                title={selectedStyle ? `Preview - ${selectedStyle.toUpperCase()} Style` : "Preview"}
              />
            ) : (
              <MultiDevicePreview
                htmlContent={generatedHtml}
                title={selectedStyle ? `Multi-Device Preview - ${selectedStyle.toUpperCase()} Style` : "Multi-Device Preview"}
              />
            )}
          </div>
        )}
      </main>

      {showPublishModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-2xl font-bold mb-4">Publish Your Website</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="My Restaurant"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">
                Choose Subdomain
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={subdomain}
                  onChange={(e) => {
                    const value = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '')
                    setSubdomain(value)
                    const validationError = validateSubdomain(value)
                    setSubdomainError(validationError)
                  }}
                  placeholder="kedaiayam"
                  className={`flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 ${
                    subdomainError ? 'border-red-500' : 'border-gray-300'
                  }`}
                />
                <span className="text-gray-600">.binaapp.my</span>
              </div>
              {subdomainError ? (
                <p className="text-xs text-red-600 mt-1 font-medium">
                  ❌ {subdomainError}
                </p>
              ) : (
                <p className="text-xs text-gray-500 mt-1">
                  Only lowercase letters, numbers, and hyphens
                </p>
              )}
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowPublishModal(false)
                  setError('')
                  setSubdomainError(null)
                }}
                className="flex-1 btn btn-outline"
                disabled={publishing}
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                className="flex-1 btn btn-primary"
                disabled={publishing || !subdomain || !projectName || !!subdomainError}
              >
                {publishing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Publishing...
                  </>
                ) : (
                  'Publish Now'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upgrade Modal */}
      <UpgradeModal
        show={showUpgradeModal}
        currentTier={currentTier}
        targetTier={targetTier}
        onClose={() => setShowUpgradeModal(false)}
      />

      {/* Addon Purchase Modal */}
      <AddonPurchaseModal
        show={showAddonModal}
        addon={selectedAddon}
        onClose={() => setShowAddonModal(false)}
      />

      {/* Limit Reached Modal */}
      {limitModalData && (
        <LimitReachedModal
          show={showLimitModal}
          onClose={() => setShowLimitModal(false)}
          resourceType={limitModalData.resourceType}
          currentUsage={limitModalData.currentUsage}
          limit={limitModalData.limit}
          canBuyAddon={limitModalData.canBuyAddon}
          addonPrice={limitModalData.addonPrice}
        />
      )}
    </div>
  )
}
