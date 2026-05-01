/**
 * Create Page - AI Website Generation
 */
'use client'
import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Sparkles, Download, Upload, Eye, Copy, Check, Share2, Layout, FileText, MapPin, Truck, ListChecks } from 'lucide-react'
import VisualImageUpload from './components/VisualImageUpload'
import DevicePreview from './components/DevicePreview'
import MultiDevicePreview from './components/MultiDevicePreview'
// CodeAnimation removed — loading overlay uses pure CSS spinner
import { UpgradeModal } from '@/components/UpgradeModal'
import { AddonPurchaseModal } from '@/components/AddonPurchaseModal'
import { LimitReachedModal } from '@/components/LimitReachedModal'
import { API_BASE_URL, DIRECT_BACKEND_URL } from '@/lib/env'
import { supabase, signOut as customSignOut, getCurrentUser, getStoredToken } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { checkImageSafety } from '@/utils/imageModeration'
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

  // V3 inline upload UI state (replaces VisualImageUpload sub-component).
  // These are ephemeral UX-only refs — uploadedImages above remains the
  // source of truth that flows to the backend.
  const [heroPreview, setHeroPreview] = useState<string>('')
  const [uploadingHero, setUploadingHero] = useState(false)
  const [menuPreviews, setMenuPreviews] = useState<Record<number, string>>({})
  const [uploadingMenuIdx, setUploadingMenuIdx] = useState<number | null>(null)

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

  // ─────────────────────────────────────────────
  // Inline hero/menu image upload (V3, Path 2)
  // Mirrors VisualImageUpload's contract:
  //   - POST ${API_BASE_URL}/api/upload-image multipart
  //   - checkImageSafety() before upload, fail-open on errors
  //   - Stores final url in uploadedImages.{hero|gallery[].url}
  // ─────────────────────────────────────────────
  const validateImageFile = (file: File): string | null => {
    if (file.size > 8 * 1024 * 1024) return 'Saiz fail melebihi 8MB. Max 8MB.'
    if (!/^image\/(png|jpeg|jpg|webp)$/.test(file.type)) return 'Format tidak disokong. Use PNG, JPG, atau WebP.'
    return null
  }

  const uploadImageToBackend = async (file: File): Promise<string> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE_URL}/api/upload-image`, { method: 'POST', body: formData })
    const data = await res.json()
    if (data.success && data.url) return data.url as string
    throw new Error(data.error || data.detail || 'Upload failed')
  }

  const handleHeroFile = async (file: File) => {
    const v = validateImageFile(file)
    if (v) { toast.error(v); return }
    const moderation = await checkImageSafety(file)
    if (!moderation.allowed) { toast.error(moderation.message); return }
    const preview = URL.createObjectURL(file)
    if (heroPreview) URL.revokeObjectURL(heroPreview)
    setHeroPreview(preview)
    setUploadingHero(true)
    try {
      const url = await uploadImageToBackend(file)
      setUploadedImages(prev => ({ ...prev, hero: url }))
    } catch (err: any) {
      toast.error(err.message || 'Gagal muat naik gambar')
      URL.revokeObjectURL(preview)
      setHeroPreview('')
    } finally {
      setUploadingHero(false)
    }
  }

  const removeHero = () => {
    if (heroPreview) URL.revokeObjectURL(heroPreview)
    setHeroPreview('')
    setUploadedImages(prev => ({ ...prev, hero: null }))
  }

  const handleHeroInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleHeroFile(file)
    e.target.value = ''
  }

  const handleHeroDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) handleHeroFile(file)
  }

  // Menu items (uploadedImages.gallery is source of truth)
  const ensureGalleryRow = (idx: number): { url: string; name: string; price: string }[] => {
    const cur = uploadedImages.gallery
    if (idx < cur.length) return cur
    const next = [...cur]
    while (next.length <= idx) next.push({ url: '', name: '', price: '' })
    return next
  }

  const updateMenuField = (idx: number, patch: Partial<{ url: string; name: string; price: string }>) => {
    setUploadedImages(prev => {
      const arr = [...prev.gallery]
      while (arr.length <= idx) arr.push({ url: '', name: '', price: '' })
      arr[idx] = { ...arr[idx], ...patch }
      return { ...prev, gallery: arr }
    })
  }

  const addMenuItemRow = () => {
    setUploadedImages(prev => ({ ...prev, gallery: [...prev.gallery, { url: '', name: '', price: '' }] }))
  }

  const removeMenuItemRow = (idx: number) => {
    setMenuPreviews(prev => {
      const next = { ...prev }
      if (next[idx]) URL.revokeObjectURL(next[idx])
      delete next[idx]
      const shifted: Record<number, string> = {}
      Object.entries(next).forEach(([k, v]) => {
        const n = Number(k)
        shifted[n > idx ? n - 1 : n] = v
      })
      return shifted
    })
    setUploadedImages(prev => ({ ...prev, gallery: prev.gallery.filter((_, i) => i !== idx) }))
  }

  const handleMenuFile = async (idx: number, file: File) => {
    const v = validateImageFile(file)
    if (v) { toast.error(v); return }
    const moderation = await checkImageSafety(file)
    if (!moderation.allowed) { toast.error(moderation.message); return }
    const preview = URL.createObjectURL(file)
    setMenuPreviews(prev => {
      const next = { ...prev }
      if (next[idx]) URL.revokeObjectURL(next[idx])
      next[idx] = preview
      return next
    })
    // Make sure a row exists at this index
    const baseline = ensureGalleryRow(idx)
    if (baseline !== uploadedImages.gallery) {
      setUploadedImages(prev => ({ ...prev, gallery: baseline }))
    }
    setUploadingMenuIdx(idx)
    try {
      const url = await uploadImageToBackend(file)
      updateMenuField(idx, { url })
    } catch (err: any) {
      toast.error(err.message || 'Gagal muat naik gambar')
      URL.revokeObjectURL(preview)
      setMenuPreviews(prev => { const n = { ...prev }; delete n[idx]; return n })
    } finally {
      setUploadingMenuIdx(null)
    }
  }

  const handleMenuInputChange = (idx: number) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleMenuFile(idx, file)
    e.target.value = ''
  }

  const clearMenuImage = (idx: number) => {
    setMenuPreviews(prev => {
      const n = { ...prev }
      if (n[idx]) URL.revokeObjectURL(n[idx])
      delete n[idx]
      return n
    })
    updateMenuField(idx, { url: '' })
  }

  // Cleanup blob preview URLs on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (heroPreview) URL.revokeObjectURL(heroPreview)
      Object.values(menuPreviews).forEach(u => { if (u) URL.revokeObjectURL(u) })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
          <div className="cr-layout">
          <div className="cr-form-col">
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

            {/* ── 02 Bahasa & Tema ── */}
            <section style={{ marginBottom: 32 }}>
              <div style={{ marginBottom: 20 }}>
                <div className="section-num" style={{ marginBottom: 10 }}>
                  <span className="dot" />02 — BAHASA &amp; TEMA
                </div>
                <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#F5F5FA', lineHeight: 1.1 }}>Bahasa &amp; tema</h2>
                <p style={{ color: '#86869A', fontSize: 14, margin: '8px 0 0', maxWidth: 540, lineHeight: 1.5 }}>Pilihan asas — boleh tukar bila-bila masa selepas generate.</p>
              </div>
              <div className="basics-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="cr-card cr-card-hairline" style={{ padding: 18, minWidth: 0 }}>
                  <div className="eyebrow" style={{ marginBottom: 12 }}>Bahasa website</div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <div
                      className={'opt ' + (language === 'ms' ? 'selected' : '')}
                      onClick={() => setLanguage('ms')}
                      style={{ flex: 1, padding: '12px 10px', minWidth: 0 }}
                    >
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#F5F5FA', lineHeight: 1.2, wordBreak: 'break-word' }}>Bahasa Malaysia</div>
                      <div style={{ fontSize: 11, color: '#86869A', marginTop: 3 }}>Default</div>
                    </div>
                    <div
                      className={'opt ' + (language === 'en' ? 'selected' : '')}
                      onClick={() => setLanguage('en')}
                      style={{ flex: 1, padding: '12px 10px', minWidth: 0 }}
                    >
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#F5F5FA', lineHeight: 1.2, wordBreak: 'break-word' }}>English</div>
                      <div style={{ fontSize: 11, color: '#86869A', marginTop: 3 }}>For tourists</div>
                    </div>
                  </div>
                </div>
                <div className="cr-card cr-card-hairline" style={{ padding: 18, minWidth: 0 }}>
                  <div className="eyebrow" style={{ marginBottom: 12 }}>Color theme</div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <div
                      className={'opt ' + (colorMode === 'light' ? 'selected' : '')}
                      onClick={() => setColorMode('light')}
                      style={{ flex: 1, padding: 0, minWidth: 0, overflow: 'hidden' }}
                    >
                      <div style={{ height: 48, background: 'linear-gradient(135deg,#F7F7FA,#EEEEF3)', borderRadius: '13px 13px 0 0' }} />
                      <div style={{ padding: '10px 10px' }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#F5F5FA' }}>Cerah</div>
                        <div style={{ fontSize: 11, color: '#86869A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Light · putih</div>
                      </div>
                    </div>
                    <div
                      className={'opt ' + (colorMode === 'dark' ? 'selected' : '')}
                      onClick={() => setColorMode('dark')}
                      style={{ flex: 1, padding: 0, minWidth: 0, overflow: 'hidden' }}
                    >
                      <div style={{ height: 48, background: 'linear-gradient(135deg,#1F1F2A,#0B0B15)', borderRadius: '13px 13px 0 0' }} />
                      <div style={{ padding: '10px 10px' }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#F5F5FA' }}>Gelap</div>
                        <div style={{ fontSize: 11, color: '#86869A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Dark · premium</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* ── 03 Apa jenis kedai anda? ── */}
            <section style={{ marginBottom: 32 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24, marginBottom: 20, flexWrap: 'wrap' }}>
                <div>
                  <div className="section-num" style={{ marginBottom: 10 }}>
                    <span className="dot" />03 — APA JENIS KEDAI ANDA?
                  </div>
                  <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#F5F5FA', lineHeight: 1.1 }}>Apa jenis kedai anda?</h2>
                  <p style={{ color: '#86869A', fontSize: 14, margin: '8px 0 0', maxWidth: 540, lineHeight: 1.5 }}>AI guna pilihan ni untuk pilih layout, content &amp; menu structure yang sesuai.</p>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                  <div
                    role="switch"
                    aria-checked={multiStyle}
                    tabIndex={0}
                    onClick={() => setMultiStyle(!multiStyle)}
                    onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setMultiStyle(!multiStyle); } }}
                    className={'toggle ' + (multiStyle ? 'on' : '')}
                  />
                  <span style={{ fontSize: 13, color: '#B8B8C8' }}>
                    Multi-style preview
                    <span className="pill pill-indigo" style={{ marginLeft: 6, padding: '2px 7px' }}>
                      <span style={{ display: 'inline-flex', width: 10, height: 10 }}>
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#C7FF3D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></svg>
                      </span>
                      AI
                    </span>
                  </span>
                </div>
              </div>
              <div className="biz-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: 12 }}>
                {([
                  { id: 'auto' as const, icon: '✨', label: 'Auto Detect', sub: 'AI pilih sesuai dengan deskripsi anda', recommended: true },
                  { id: 'food' as const, icon: '🍜', label: 'Restoran', sub: 'Mamak, kafe, kedai makan', recommended: false },
                  { id: 'clothing' as const, icon: '👗', label: 'Pakaian', sub: 'Butik, fashion, lifestyle', recommended: false },
                  { id: 'salon' as const, icon: '💇', label: 'Salon', sub: 'Hair, beauty, spa', recommended: false },
                  { id: 'services' as const, icon: '🔧', label: 'Servis', sub: 'Bengkel, plumbing, repair', recommended: false },
                  { id: 'bakery' as const, icon: '🥐', label: 'Bakeri', sub: 'Roti, kek, pastri', recommended: false },
                  { id: 'general' as const, icon: '✦', label: 'Lain-lain', sub: 'Custom — beritahu AI', recommended: false }
                ]).map(type => (
                  <div
                    key={type.id}
                    onClick={() => setBusinessType(type.id)}
                    className={'opt ' + (businessType === type.id ? 'selected' : '')}
                    style={{ padding: 14, minHeight: 110, minWidth: 0 }}
                  >
                    {type.recommended && (
                      <div className="pill pill-volt" style={{ position: 'absolute', top: 8, right: 8, padding: '2px 6px', fontSize: 9 }}>RECOMMENDED</div>
                    )}
                    <div style={{ fontSize: 22, marginBottom: 10, filter: 'grayscale(.2)' }}>{type.icon}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F5F5FA', marginBottom: 3, lineHeight: 1.2 }}>{type.label}</div>
                    <div style={{ fontSize: 11, color: '#86869A', lineHeight: 1.35 }}>{type.sub}</div>
                  </div>
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
              {multiStyle && (
                <label className="cr-check" style={{ marginTop: 14, padding: '10px 12px', background: 'rgba(255,255,255,.02)', border: '1px solid rgba(255,255,255,.04)', borderRadius: 10 }}>
                  <input
                    type="checkbox"
                    checked={generatePreviews}
                    onChange={(e) => setGeneratePreviews(e.target.checked)}
                  />
                  <span className="cr-check-box" />
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 500, color: '#B8B8C8' }}>Generate Preview Thumbnails</span>
                    <p style={{ fontSize: 12, color: '#5A5A6E', marginTop: 2 }}>Takes 10-15 seconds longer but shows better previews</p>
                  </div>
                </label>
              )}
            </section>

            {/* ── 04 Cerita pasal kedai anda ── */}
            {(() => {
              const DESC_MIN = 200;
              const DESC_MAX = 1000;
              const len = description.length;
              const pct = Math.min(100, (len / DESC_MIN) * 100);
              type DescStatus = 'empty' | 'tooshort' | 'ok' | 'great' | 'plenty';
              const status: DescStatus =
                len === 0 ? 'empty'
                : len < DESC_MIN ? 'tooshort'
                : len < 600 ? 'ok'
                : len < 900 ? 'great'
                : 'plenty';
              const helpers: Record<DescStatus, { c: string; t: string }> = {
                empty:    { c: '#5A5A6E', t: 'AI akan tanya soalan dengan deskripsi anda.' },
                tooshort: { c: '#FFB020', t: `Tambah ${DESC_MIN - len} aksara lagi untuk hasil terbaik.` },
                ok:       { c: '#22C08F', t: 'Bagus — AI dah ada cukup info.' },
                great:    { c: '#C7FF3D', t: 'Premium quality output dijangka. AI ready.' },
                plenty:   { c: '#C7FF3D', t: `Sangat detailed. ${DESC_MAX - len} aksara baki.` },
              };
              const helper = helpers[status];
              return (
                <section style={{ marginBottom: 32 }}>
                  <div style={{ marginBottom: 20 }}>
                    <div className="section-num" style={{ marginBottom: 10 }}>
                      <span className="dot" />04 — CERITA PASAL KEDAI ANDA
                    </div>
                    <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#F5F5FA', lineHeight: 1.1 }}>Cerita pasal kedai anda</h2>
                    <p style={{ color: '#86869A', fontSize: 14, margin: '8px 0 0', maxWidth: 540, lineHeight: 1.5 }}>Lebih detail = website lebih baik. Cakap pasal vibe, pelanggan, signature menu, sejarah — semua membantu AI.</p>
                  </div>
                  <div className="cr-card cr-card-hairline" style={{ padding: 4, position: 'relative', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', top: 16, right: 16, display: 'flex', alignItems: 'center', gap: 8, zIndex: 2 }}>
                      <span className="pill pill-indigo" style={{ padding: '4px 10px' }}>
                        <span style={{ display: 'inline-flex', width: 10, height: 10 }}>
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#C7FF3D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></svg>
                        </span>
                        AI listening
                      </span>
                    </div>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value.slice(0, DESC_MAX))}
                      placeholder={
                        language === 'ms'
                          ? 'Contoh: Kedai mamak family-run di Shah Alam since 1998. Kami famous dengan nasi kandar daging crystal kuah pedas — customer datang dari KL khas untuk makan. Vibe authentic, tak fancy. Open 24 jam, weekends penuh dengan family ramai-ramai.'
                          : 'Example: I have a coffee shop in Kuala Lumpur serving specialty coffee, cakes, and light meals. Prices from RM8. Located at TTDI. Contact via WhatsApp 012-3456789. Open daily 8am-6pm.'
                      }
                      style={{
                        width: '100%',
                        background: 'transparent',
                        border: 'none',
                        minHeight: 180,
                        fontSize: 15,
                        padding: '20px 22px 64px',
                        boxShadow: 'none',
                        outline: 'none',
                        resize: 'vertical',
                        color: '#F5F5FA',
                        lineHeight: 1.55,
                        fontFamily: "'Geist', 'Inter', -apple-system, sans-serif",
                        letterSpacing: '-0.005em',
                      }}
                    />
                    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '12px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderTop: '1px solid rgba(255,255,255,.04)', background: 'linear-gradient(180deg, transparent, rgba(0,0,0,.2))', flexWrap: 'wrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 200, maxWidth: 480 }}>
                        <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,.06)', borderRadius: 999, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: helper.c, transition: 'all 300ms', boxShadow: `0 0 8px ${helper.c}` }} />
                        </div>
                        <div className="num" style={{ fontSize: 11, color: helper.c, minWidth: 60 }}>{len} / {DESC_MAX}</div>
                      </div>
                      <div style={{ fontSize: 12, color: helper.c, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Sparkles size={11} /> {helper.t}
                      </div>
                    </div>
                  </div>
                </section>
              );
            })()}

            {/* ── 05 Hero image ── */}
            <section style={{ marginBottom: 32 }}>
              <div style={{ marginBottom: 20 }}>
                <div className="section-num" style={{ marginBottom: 10 }}>
                  <span className="dot" />05 — HERO IMAGE
                </div>
                <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#F5F5FA', lineHeight: 1.1 }}>Hero image</h2>
                <p style={{ color: '#86869A', fontSize: 14, margin: '8px 0 0', maxWidth: 540, lineHeight: 1.5 }}>Image utama untuk header website. Optional — AI boleh suggest dari brief anda.</p>
              </div>
              <div className="cr-card cr-card-hairline" style={{ padding: 16, display: 'flex', gap: 14, alignItems: 'stretch', flexWrap: 'wrap' }}>
                <div
                  onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = 'rgba(107,92,255,.5)'; e.currentTarget.style.background = 'rgba(79,61,255,.04)'; }}
                  onDragLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,.12)'; e.currentTarget.style.background = 'rgba(255,255,255,.015)'; }}
                  onDrop={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,.12)'; e.currentTarget.style.background = 'rgba(255,255,255,.015)'; handleHeroDrop(e); }}
                  onClick={() => document.getElementById('v3-hero-upload')?.click()}
                  style={{ flex: '1 1 280px', minWidth: 240, minHeight: 160, border: '1.5px dashed rgba(255,255,255,.12)', borderRadius: 14, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, cursor: 'pointer', background: 'rgba(255,255,255,.015)', transition: 'all 220ms', position: 'relative', overflow: 'hidden', padding: 16 }}
                >
                  {(uploadedImages.hero || heroPreview) ? (
                    <>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={heroPreview || uploadedImages.hero || ''} alt="Hero" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
                      {uploadingHero && (
                        <div style={{ position: 'absolute', inset: 0, background: 'rgba(5,5,12,.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                          <div style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,.25)', borderTopColor: '#C7FF3D', borderRadius: '50%', animation: 'spin .8s linear infinite' }} />
                          <span style={{ fontSize: 12, color: '#F5F5FA' }}>Memuat naik…</span>
                        </div>
                      )}
                      {uploadedImages.hero && !uploadingHero && (
                        <span className="pill pill-volt" style={{ position: 'absolute', bottom: 8, left: 8, padding: '2px 8px', fontSize: 9 }}>
                          <span className="led" /> UPLOADED
                        </span>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); removeHero(); }}
                        type="button"
                        aria-label="Buang gambar"
                        style={{ position: 'absolute', top: 8, right: 8, width: 26, height: 26, borderRadius: '50%', background: 'rgba(5,5,12,.7)', border: '1px solid rgba(255,255,255,.15)', color: '#F5F5FA', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}
                      >
                        ✕
                      </button>
                    </>
                  ) : (
                    <>
                      <div style={{ width: 40, height: 40, borderRadius: 11, background: 'rgba(79,61,255,.1)', border: '1px solid rgba(107,92,255,.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#BAB0FF' }}>
                        <Upload size={18} />
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 13, color: '#F5F5FA', fontWeight: 500 }}>Drop image atau <span style={{ color: '#BAB0FF' }}>browse</span></div>
                        <div style={{ fontSize: 11, color: '#5A5A6E', marginTop: 4 }}>PNG, JPG, WebP · max 8MB</div>
                      </div>
                    </>
                  )}
                  <input id="v3-hero-upload" type="file" accept="image/png,image/jpeg,image/jpg,image/webp" onChange={handleHeroInputChange} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                </div>
                <div style={{ flex: '1 1 200px', minWidth: 180, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <button
                    type="button"
                    onClick={() => setImageChoice('ai')}
                    className="cr-btn cr-btn-ghost"
                    style={{ justifyContent: 'flex-start', height: 52, gap: 10, padding: '0 12px', textAlign: 'left' }}
                  >
                    <div style={{ width: 30, height: 30, borderRadius: 8, background: 'rgba(199,255,61,.1)', border: '1px solid rgba(199,255,61,.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#C7FF3D', flexShrink: 0 }}>
                      <Sparkles size={14} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>Generate AI</div>
                      <div style={{ fontSize: 11, color: '#86869A' }}>Premium · 1 credit</div>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => toast('Stock library — coming soon')}
                    className="cr-btn cr-btn-ghost"
                    style={{ justifyContent: 'flex-start', height: 52, gap: 10, padding: '0 12px', textAlign: 'left' }}
                  >
                    <div style={{ width: 30, height: 30, borderRadius: 8, background: 'rgba(255,255,255,.04)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86869A', flexShrink: 0 }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/></svg>
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>Stock library</div>
                      <div style={{ fontSize: 11, color: '#86869A' }}>2,400+ free</div>
                    </div>
                  </button>
                </div>
              </div>
            </section>

            {/* ── 06 Menu items ── */}
            <section style={{ marginBottom: 32 }}>
              <div style={{ marginBottom: 20 }}>
                <div className="section-num" style={{ marginBottom: 10 }}>
                  <span className="dot" />06 — MENU ITEMS
                </div>
                <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#F5F5FA', lineHeight: 1.1 }}>Menu items</h2>
                <p style={{ color: '#86869A', fontSize: 14, margin: '8px 0 0', maxWidth: 540, lineHeight: 1.5 }}>Tambah signature items anda. AI akan suggest description + format harga.</p>
              </div>
              <div className="cr-card cr-card-hairline" style={{ padding: 20 }}>
                <div style={{ marginBottom: 16 }}>
                  <div className="eyebrow" style={{ marginBottom: 10 }}>Image source</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
                    {(() => {
                      const uploadedCount = (uploadedImages.hero ? 1 : 0) + uploadedImages.gallery.filter(g => g.url).length
                      const sources = [
                        { id: 'none' as const,   l: 'Tiada gambar',   s: 'Text-only menu', icon: <FileText size={16} />, premium: false, badge: '' },
                        { id: 'upload' as const, l: 'Upload sendiri', s: 'Drag drop images', icon: <Upload size={16} />, premium: false, badge: uploadedCount > 0 ? `${uploadedCount} uploaded` : '' },
                        { id: 'ai' as const,     l: 'AI generate',    s: 'Premium · auto-match', icon: <Sparkles size={16} />, premium: true, badge: '' },
                      ]
                      return sources.map(s => (
                        <div
                          key={s.id}
                          className={'opt ' + (imageChoice === s.id ? 'selected' : '')}
                          onClick={() => setImageChoice(s.id)}
                          style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}
                        >
                          <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#B8B8C8', flexShrink: 0 }}>
                            {s.icon}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 13, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                              {s.l}
                              {s.premium && <span className="pill pill-volt" style={{ padding: '1px 6px', fontSize: 9 }}>PREMIUM</span>}
                              {s.badge && <span className="pill pill-volt" style={{ padding: '1px 6px', fontSize: 9 }}>{s.badge}</span>}
                            </div>
                            <div style={{ fontSize: 11, color: '#86869A', marginTop: 1 }}>{s.s}</div>
                          </div>
                        </div>
                      ))
                    })()}
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {(uploadedImages.gallery.length > 0 ? uploadedImages.gallery : [{ url: '', name: '', price: '' }]).map((it, i) => {
                    const showImg = menuPreviews[i] || it.url
                    const canRemove = uploadedImages.gallery.length > 0
                    return (
                      <div key={i} className="float-in menu-row" style={{ display: 'grid', gridTemplateColumns: '48px minmax(0,1fr) 100px 32px', gap: 8, alignItems: 'center', padding: '8px 10px 8px 8px', background: '#0F0F1A', border: '1px solid rgba(255,255,255,.06)', borderRadius: 12 }}>
                        <div
                          onClick={() => document.getElementById(`v3-menu-upload-${i}`)?.click()}
                          style={{ width: 40, height: 40, borderRadius: 8, background: showImg ? '#000' : 'rgba(255,255,255,.04)', border: showImg ? '1px solid rgba(255,255,255,.08)' : '1px dashed rgba(255,255,255,.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#5A5A6E', cursor: 'pointer', overflow: 'hidden', position: 'relative' }}
                        >
                          {showImg ? (
                            <>
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img src={showImg} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                              {uploadingMenuIdx === i && (
                                <div style={{ position: 'absolute', inset: 0, background: 'rgba(5,5,12,.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                  <div style={{ width: 12, height: 12, border: '1.5px solid rgba(255,255,255,.25)', borderTopColor: '#C7FF3D', borderRadius: '50%', animation: 'spin .8s linear infinite' }} />
                                </div>
                              )}
                              {it.url && uploadingMenuIdx !== i && (
                                <>
                                  <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 12, background: 'linear-gradient(180deg, transparent, rgba(5,5,12,.8))', display: 'flex', alignItems: 'flex-end', justifyContent: 'center', color: '#C7FF3D', fontSize: 9, fontWeight: 700, lineHeight: 1, paddingBottom: 1, pointerEvents: 'none' }}>✓</div>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); clearMenuImage(i); }}
                                    type="button"
                                    aria-label="Buang gambar"
                                    style={{ position: 'absolute', top: 0, right: 0, width: 16, height: 16, borderRadius: '0 8px 0 4px', background: 'rgba(5,5,12,.8)', border: 0, color: '#F5F5FA', fontSize: 9, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                                  >✕</button>
                                </>
                              )}
                            </>
                          ) : (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/></svg>
                          )}
                          <input id={`v3-menu-upload-${i}`} type="file" accept="image/png,image/jpeg,image/jpg,image/webp" onChange={handleMenuInputChange(i)} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                        </div>
                        <input
                          className="cr-input"
                          placeholder="Nasi Kandar Daging Crystal"
                          value={it.name}
                          onChange={(e) => updateMenuField(i, { name: e.target.value })}
                          style={{ background: 'transparent', border: '1px solid rgba(255,255,255,.04)', height: 40, padding: '0 12px', minWidth: 0, width: '100%' }}
                        />
                        <div className="menu-row-price" style={{ position: 'relative', minWidth: 0 }}>
                          <span className="num" style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', fontSize: 11, color: '#5A5A6E', pointerEvents: 'none' }}>RM</span>
                          <input
                            className="cr-input"
                            placeholder="12.50"
                            value={it.price}
                            onChange={(e) => updateMenuField(i, { price: e.target.value })}
                            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,.04)', height: 40, padding: '0 10px 0 32px', fontFamily: "'Geist Mono', monospace", width: '100%', minWidth: 0 }}
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeMenuItemRow(i)}
                          aria-label="Buang item"
                          className="cr-btn-icon menu-row-trash"
                          style={{ width: 32, height: 40, opacity: canRemove ? 1 : 0.35, cursor: canRemove ? 'pointer' : 'not-allowed' }}
                          disabled={!canRemove}
                          title={canRemove ? 'Buang item ini' : 'Tambah item lain dahulu'}
                        >
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M5 6l1 14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-14"/></svg>
                        </button>
                      </div>
                    )
                  })}
                </div>
                <button
                  type="button"
                  onClick={addMenuItemRow}
                  style={{ marginTop: 10, width: '100%', padding: 12, background: 'transparent', border: '1.5px dashed rgba(199,255,61,.25)', borderRadius: 12, color: '#C7FF3D', fontSize: 13, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontWeight: 500, fontFamily: "'Geist', 'Inter', -apple-system, sans-serif", transition: 'all 180ms' }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(199,255,61,.04)'; e.currentTarget.style.borderColor = 'rgba(199,255,61,.4)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(199,255,61,.25)'; }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>
                  Add item
                </button>

                {(() => {
                  const filled = uploadedImages.gallery.filter(g => g.name || g.price || g.url).length
                  return filled > 0 ? (
                    <div className="num" style={{ marginTop: 10, fontSize: 11, color: '#5A5A6E', textAlign: 'center' }}>
                      {filled} item{filled === 1 ? '' : 's'} added
                    </div>
                  ) : null
                })()}

                {imageChoice === 'upload' && uploadedImages.gallery.filter(g => g.url).length === 0 && !uploadedImages.hero && (
                  <div className="banner-accent float-in" style={{ marginTop: 14, marginBottom: 0, background: 'linear-gradient(90deg, rgba(255,176,32,.06), transparent)', border: '1px solid rgba(255,176,32,.22)' }}>
                    <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#FFB020' }} />
                    <span style={{ fontSize: 13, color: '#FFB020' }}>Anda belum muat naik gambar. Drop hero image di atas atau pilih pilihan lain.</span>
                  </div>
                )}
              </div>
            </section>

            {/* ── 07 Features yang anda nak ── */}
            <section style={{ marginBottom: 32 }}>
              <div style={{ marginBottom: 20 }}>
                <div className="section-num" style={{ marginBottom: 10 }}>
                  <span className="dot" />07 — FEATURES YANG ANDA NAK
                </div>
                <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#F5F5FA', lineHeight: 1.1 }}>Features yang anda nak</h2>
                <p style={{ color: '#86869A', fontSize: 14, margin: '8px 0 0', maxWidth: 540, lineHeight: 1.5 }}>Pilih mana yang relevant. Boleh tukar/tambah selepas generate.</p>
              </div>
              <div className="features-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0,1fr))', gap: 12 }}>
                {(() => {
                  const WhatsAppIcon = ({ size = 16 }: { size?: number }) => (
                    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 11.5a8.4 8.4 0 0 1-1.2 4.4L21 21l-5.2-1.4a8.5 8.5 0 1 1 5.2-8.1Z" />
                      <path d="M8.5 9.5c.2 1 .8 2.2 1.7 3.1.9 1 2 1.5 3 1.7l1.2-1.1 2 .9c-.1.6-.5 1.2-1.1 1.5-1.4.7-3.7.2-5.6-1.7-1.8-1.8-2.4-4.2-1.7-5.6.3-.6.8-1 1.4-1.1l1 2-1 1.3Z" />
                    </svg>
                  )
                  const features = [
                    { key: 'whatsapp' as const,        label: 'WhatsApp Order',  sub: 'Pesanan terus ke WhatsApp', Icon: WhatsAppIcon, color: '#25D366' },
                    { key: 'googleMap' as const,       label: 'Google Maps',     sub: 'Lokasi & arah ke kedai',     Icon: MapPin,       color: '#4F3DFF' },
                    { key: 'deliverySystem' as const,  label: 'Delivery',        sub: 'Penghantaran sendiri',       Icon: Truck,        color: '#FFB020' },
                    { key: 'contactForm' as const,     label: 'Borang Tempahan', sub: 'Booking / reservation',      Icon: FileText,     color: '#3FB8FF' },
                    { key: 'socialMedia' as const,     label: 'Social Media',    sub: 'IG, FB, TikTok feed',        Icon: Share2,       color: '#FF5A5F' },
                    { key: 'priceList' as const,       label: 'Senarai Harga',   sub: 'Menu / katalog harga',       Icon: ListChecks,   color: '#C7FF3D' },
                  ]
                  return features.map(f => {
                    const on = selectedFeatures[f.key]
                    return (
                      <div
                        key={f.key}
                        role="checkbox"
                        aria-checked={on}
                        tabIndex={0}
                        className={'opt ' + (on ? 'selected' : '')}
                        onClick={() => setSelectedFeatures({ ...selectedFeatures, [f.key]: !on })}
                        onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setSelectedFeatures({ ...selectedFeatures, [f.key]: !on }); } }}
                        style={{ padding: 14, display: 'flex', gap: 10, alignItems: 'flex-start', minWidth: 0 }}
                      >
                        <div style={{ width: 34, height: 34, borderRadius: 9, background: on ? 'rgba(79,61,255,.18)' : 'rgba(255,255,255,.04)', border: `1px solid ${on ? 'rgba(107,92,255,.4)' : 'rgba(255,255,255,.08)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: on ? '#BAB0FF' : f.color, flexShrink: 0 }}>
                          <f.Icon size={16} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2, lineHeight: 1.25, wordBreak: 'break-word', color: '#F5F5FA' }}>{f.label}</div>
                          <div style={{ fontSize: 11, color: '#86869A', lineHeight: 1.35 }}>{f.sub}</div>
                        </div>
                        <div style={{ width: 16, height: 16, borderRadius: 4, border: `1.5px solid ${on ? '#6B5CFF' : 'rgba(255,255,255,.15)'}`, background: on ? '#4F3DFF' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2, color: '#fff' }}>
                          {on && <Check size={10} strokeWidth={3} />}
                        </div>
                      </div>
                    )
                  })
                })()}
              </div>
            </section>

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

            {/* ── 08 Cara terima bayaran ── */}
            <section style={{ marginBottom: 32 }}>
              <div style={{ marginBottom: 20 }}>
                <div className="section-num" style={{ marginBottom: 10 }}>
                  <span className="dot" />08 — CARA TERIMA BAYARAN
                </div>
                <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#F5F5FA', lineHeight: 1.1 }}>Cara terima bayaran</h2>
                <p style={{ color: '#86869A', fontSize: 14, margin: '8px 0 0', maxWidth: 540, lineHeight: 1.5 }}>Pilih method pembayaran. ToyyibPay &amp; QR boleh setup lepas generate.</p>
              </div>
              <div className="payment-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {(() => {
                  const CashIcon = ({ size = 20 }: { size?: number }) => (
                    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="6" width="20" height="12" rx="2" />
                      <circle cx="12" cy="12" r="2.5" />
                      <path d="M6 10v.01M18 14v.01" />
                    </svg>
                  )
                  const QRIcon = ({ size = 20 }: { size?: number }) => (
                    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="7" height="7" rx="1" />
                      <rect x="14" y="3" width="7" height="7" rx="1" />
                      <rect x="3" y="14" width="7" height="7" rx="1" />
                      <path d="M14 14h3v3M21 14v3M14 21h3M21 17v4" />
                    </svg>
                  )
                  const methods = [
                    { id: 'cod' as const, l: 'Cash on Delivery', s: 'Customer bayar masa terima · simple', Icon: CashIcon, recommended: false },
                    { id: 'qr'  as const, l: 'QR / Online Payment', s: 'DuitNow QR · ToyyibPay · Stripe', Icon: QRIcon, recommended: true },
                  ]
                  return methods.map(p => {
                    const on = paymentMethods[p.id]
                    return (
                      <div
                        key={p.id}
                        role="checkbox"
                        aria-checked={on}
                        tabIndex={0}
                        className={'opt ' + (on ? 'selected' : '')}
                        onClick={() => setPaymentMethods({ ...paymentMethods, [p.id]: !on })}
                        onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setPaymentMethods({ ...paymentMethods, [p.id]: !on }); } }}
                        style={{ padding: 18, display: 'flex', gap: 14, alignItems: 'center' }}
                      >
                        <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#B8B8C8', flexShrink: 0 }}>
                          <p.Icon size={20} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                            <div style={{ fontSize: 15, fontWeight: 600, color: '#F5F5FA' }}>{p.l}</div>
                            {p.recommended && <span className="pill pill-volt" style={{ padding: '2px 7px', fontSize: 9 }}>POPULAR</span>}
                          </div>
                          <div style={{ fontSize: 12, color: '#86869A', marginTop: 3 }}>{p.s}</div>
                        </div>
                        <div style={{ width: 16, height: 16, borderRadius: 4, border: `1.5px solid ${on ? '#6B5CFF' : 'rgba(255,255,255,.15)'}`, background: on ? '#4F3DFF' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: '#fff' }}>
                          {on && <Check size={10} strokeWidth={3} />}
                        </div>
                      </div>
                    )
                  })
                })()}
              </div>

              {/* QR Upload (expand when QR enabled) */}
              {paymentMethods.qr && (
                <div className="cr-sub-card float-in" style={{ marginTop: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#B8B8C8', marginBottom: 10 }}>Muat Naik QR Pembayaran Anda</div>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                    <div style={{ width: 120, height: 120, border: '2px dashed rgba(255,255,255,.12)', borderRadius: 14, background: 'rgba(255,255,255,.02)', flexShrink: 0, overflow: 'hidden' }}>
                      <label style={{ cursor: 'pointer', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                        <input type="file" accept="image/*" style={{ display: 'none' }} onChange={handleQRUpload} />
                        {paymentQRPreview ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={paymentQRPreview} alt="Payment QR" style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 4, borderRadius: 12 }} />
                        ) : (
                          <>
                            <span style={{ fontSize: 28, marginBottom: 4 }}>📷</span>
                            <span style={{ fontSize: 11, color: '#5A5A6E' }}>Upload QR</span>
                          </>
                        )}
                      </label>
                    </div>
                    <div style={{ flex: 1, minWidth: 200, fontSize: 13, color: '#86869A' }}>
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
            </section>

            {error && (
              <div className="banner-accent" style={{ background: 'linear-gradient(90deg, rgba(239,68,68,.06), transparent)', border: '1px solid rgba(239,68,68,.22)' }}>
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#EF4444' }} />
                <span style={{ fontSize: 13, color: '#FCA5A5' }}>{error}</span>
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={loading || description.length < 10 || isAtLimit}
              className="cr-gen-btn"
            >
              {loading ? (
                <>
                  <div style={{ width: 18, height: 18, border: '2px solid rgba(5,5,12,.3)', borderTopColor: '#05050C', borderRadius: '50%', animation: 'spin .6s linear infinite' }} />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Generate Website with AI
                </>
              )}
            </button>

            {loading && (
              <div style={{ position: 'fixed', inset: 0, background: 'rgba(5,5,12,.85)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
                <div className="cr-card cr-card-hairline" style={{ padding: 40, maxWidth: 560, width: '100%', margin: '0 16px' }}>
                  {error ? (
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', fontSize: 28 }}>❌</div>
                      <h3 style={{ fontSize: 22, fontWeight: 700, color: '#F5F5FA', margin: '0 0 8px' }}>Generation Failed</h3>
                      <p style={{ fontSize: 14, color: '#86869A', margin: '0 0 20px' }}>Something went wrong while generating your website</p>
                      <div style={{ padding: 14, background: 'rgba(239,68,68,.06)', border: '1px solid rgba(239,68,68,.2)', borderRadius: 12, marginBottom: 24, textAlign: 'left' }}>
                        <p style={{ fontSize: 13, color: '#FCA5A5', margin: 0 }}>{error}</p>
                      </div>
                      <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                        <button onClick={() => { setLoading(false); setError(''); setProgress(0); }} className="cr-btn-ghost cr-btn">Cancel</button>
                        <button onClick={() => { setError(''); setProgress(0); handleGenerate(); }} className="cr-btn" style={{ background: 'linear-gradient(180deg, #6B5CFF, #4F3DFF)', color: '#fff', boxShadow: '0 0 0 1px rgba(107,92,255,.5), 0 8px 24px rgba(79,61,255,.35)' }}>Try Again</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* AI Spinner */}
                      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 28 }}>
                        <div className="cr-spinner" />
                      </div>

                      <div style={{ textAlign: 'center', marginBottom: 28 }}>
                        <h3 style={{ fontSize: 22, fontWeight: 700, color: '#F5F5FA', margin: '0 0 6px' }}>Building your website...</h3>
                        <p style={{ fontSize: 14, color: '#86869A', margin: 0 }}>AI is writing production-ready HTML code for you</p>
                      </div>

                      {/* Progress bar */}
                      <div style={{ marginBottom: 28 }}>
                        <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,.06)', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${progress}%`, background: 'linear-gradient(90deg, #4F3DFF, #C7FF3D)', borderRadius: 99, transition: 'width 500ms cubic-bezier(.25,1,.5,1)' }} />
                        </div>
                        <div style={{ textAlign: 'center', marginTop: 8 }}>
                          <span className="num" style={{ fontSize: 13, color: '#C7FF3D', fontWeight: 600 }}>{progress}%</span>
                          <span style={{ fontSize: 13, color: '#5A5A6E', marginLeft: 6 }}>Complete</span>
                        </div>
                      </div>

                      {/* 5-step indicators */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 380, margin: '0 auto' }}>
                        {[
                          { label: 'Analyzing your business description...', start: 10, end: 30 },
                          { label: 'Generating Modern style...', start: 30, end: 50 },
                          { label: 'Generating Minimal style...', start: 50, end: 70 },
                          { label: 'Generating Bold style...', start: 70, end: 90 },
                          { label: 'Finalizing website...', start: 90, end: 100 },
                        ].map((step, i) => {
                          const done = progress >= step.end;
                          const active = progress >= step.start && progress < step.end;
                          return (
                            <div key={i} className={`cr-step ${active ? 'cr-step-active' : ''} ${done ? 'cr-step-done' : ''}`}>
                              <div className="cr-step-dot" />
                              <span style={{ fontSize: 13 }}>{done ? '✓ ' : ''}{step.label}</span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Stale Progress Warning */}
                      {staleWarning && (
                        <div className="banner-accent" style={{ marginTop: 20, marginBottom: 0, background: 'linear-gradient(90deg, rgba(255,176,32,.06), transparent)', border: '1px solid rgba(255,176,32,.22)' }}>
                          <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#FFB020' }} />
                          <span style={{ fontSize: 13, color: '#FFB020' }}>Progress appears stuck at {progress}%. The backend may be experiencing issues. Job may still complete.</span>
                        </div>
                      )}

                      <p style={{ fontSize: 12, color: '#5A5A6E', marginTop: 20, textAlign: 'center' }}>
                        This usually takes 45-90 seconds. Progress updates every 3 seconds.
                      </p>

                      {currentJobId && (
                        <p className="num" style={{ fontSize: 11, color: '#3A3A4A', marginTop: 8, textAlign: 'center' }}>
                          Job: {currentJobId.slice(0, 8)}...
                        </p>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* ── AI Preview Rail ── */}
          <aside className="cr-rail">
            <div className="cr-rail-card cr-card cr-card-hairline">
              <div className="eyebrow" style={{ marginBottom: 14 }}>PREVIEW</div>

              {/* Completeness meter */}
              {(() => {
                const pct =
                  (description.length >= 50 ? 30 : 0) +
                  (businessType !== 'auto' ? 15 : 0) +
                  (imageChoice !== 'none' ? 15 : 0) +
                  (selectedFeatures.whatsapp || selectedFeatures.googleMap || selectedFeatures.deliverySystem || selectedFeatures.contactForm || selectedFeatures.socialMedia || selectedFeatures.priceList ? 15 : 0) +
                  (paymentMethods.cod || paymentMethods.qr ? 15 : 0) +
                  10; // language always selected
                return (
                  <div style={{ marginBottom: 18 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 12, color: '#86869A' }}>Completeness</span>
                      <span className="num" style={{ fontSize: 12, color: pct >= 80 ? '#C7FF3D' : '#86869A' }}>{pct}%</span>
                    </div>
                    <div className="cr-meter">
                      <div className="cr-meter-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })()}

              {/* Wireframe blocks */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div className={`cr-wireframe-block ${description.length >= 50 ? 'cr-wireframe-lit' : ''}`}>
                  <span style={{ fontSize: 13 }}>📝</span>
                  <span style={{ fontSize: 12 }}>Deskripsi</span>
                </div>
                <div className={`cr-wireframe-block ${businessType !== 'auto' ? 'cr-wireframe-lit' : ''}`}>
                  <span style={{ fontSize: 13 }}>🏪</span>
                  <span style={{ fontSize: 12 }}>Jenis</span>
                </div>
                <div className={`cr-wireframe-block ${imageChoice !== 'none' ? 'cr-wireframe-lit' : ''}`}>
                  <span style={{ fontSize: 13 }}>🖼️</span>
                  <span style={{ fontSize: 12 }}>Gambar</span>
                </div>
                <div className={`cr-wireframe-block ${selectedFeatures.whatsapp || selectedFeatures.googleMap || selectedFeatures.deliverySystem || selectedFeatures.contactForm || selectedFeatures.socialMedia || selectedFeatures.priceList ? 'cr-wireframe-lit' : ''}`}>
                  <span style={{ fontSize: 13 }}>⚡</span>
                  <span style={{ fontSize: 12 }}>Ciri-ciri</span>
                </div>
                <div className={`cr-wireframe-block ${paymentMethods.cod || paymentMethods.qr ? 'cr-wireframe-lit' : ''}`}>
                  <span style={{ fontSize: 13 }}>💳</span>
                  <span style={{ fontSize: 12 }}>Bayaran</span>
                </div>
              </div>
            </div>
          </aside>

          </div>
        ) : styleVariations.length > 0 && !selectedStyle ? (
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            {/* Success banner */}
            <div className="banner-accent float-in" style={{ background: 'linear-gradient(90deg, rgba(199,255,61,.06), transparent)', border: '1px solid rgba(199,255,61,.22)' }}>
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#C7FF3D' }} />
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(199,255,61,.1)', border: '1px solid rgba(199,255,61,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Check size={16} style={{ color: '#C7FF3D' }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA' }}>3 Design Variations Generated!</div>
                <div style={{ fontSize: 12, color: '#86869A', marginTop: 2 }}>
                  Template: <span style={{ fontWeight: 600 }}>{templateUsed}</span> · Features: <span style={{ fontWeight: 600 }}>{detectedFeatures.join(', ')}</span>
                </div>
                <div style={{ fontSize: 12, color: '#86869A', marginTop: 4 }}>Click on any design below to view and customize it</div>
              </div>
            </div>

            <button
              onClick={() => { setStyleVariations([]); setGeneratedHtml(''); setError(''); setPublishedUrl(''); }}
              className="cr-btn cr-btn-ghost"
              style={{ marginBottom: 24 }}
            >
              Create Another
            </button>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20, marginBottom: 32 }}>
              {styleVariations.map((variation, idx) => {
                const styleInfo: Record<string, { name: string; icon: string; gradient: string; description: string }> = {
                  modern: { name: 'Modern', icon: '🎨', gradient: 'linear-gradient(135deg, #6B5CFF, #4F3DFF)', description: 'Vibrant gradients, glassmorphism, contemporary design' },
                  minimal: { name: 'Minimal', icon: '✨', gradient: 'linear-gradient(135deg, #5A5A6E, #3A3A4A)', description: 'Clean, simple, elegant with lots of white space' },
                  bold: { name: 'Bold', icon: '⚡', gradient: 'linear-gradient(135deg, #F97316, #EF4444)', description: 'High contrast, dramatic, attention-grabbing' },
                };
                const info = styleInfo[variation.style] || { name: variation.style, icon: '🎯', gradient: 'linear-gradient(135deg, #6B5CFF, #4F3DFF)', description: 'Custom style' };

                return (
                  <div
                    key={idx}
                    className="cr-var-card"
                    onClick={() => { console.log('Selecting variation:', variation); handleSelectVariation(variation); }}
                  >
                    {/* Style header bar */}
                    <div style={{ padding: '16px 20px', background: info.gradient, borderRadius: '20px 20px 0 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 20 }}>{info.icon}</span>
                        <span style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>{info.name}</span>
                      </div>
                      <p style={{ fontSize: 12, color: 'rgba(255,255,255,.75)', margin: 0 }}>{info.description}</p>
                    </div>

                    {/* Preview iframe */}
                    <div style={{ position: 'relative', height: 380, background: '#0A0A14' }}>
                      {variation.html ? (
                        <iframe
                          srcDoc={variation.html}
                          style={{ width: '100%', height: '100%', border: 0, pointerEvents: 'none' }}
                          title={`${info.name} Preview`}
                          sandbox="allow-same-origin"
                        />
                      ) : (
                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#5A5A6E', fontSize: 13 }}>
                          No preview available
                        </div>
                      )}
                      {/* Hover overlay */}
                      <div className="cr-var-overlay">
                        <span className="cr-btn" style={{ background: 'linear-gradient(180deg, #6B5CFF, #4F3DFF)', color: '#fff', boxShadow: '0 8px 24px rgba(79,61,255,.4)' }}>
                          <Eye size={16} /> View Full Design
                        </span>
                      </div>
                    </div>

                    {/* Footer */}
                    <div style={{ padding: '12px 20px', borderTop: '1px solid rgba(255,255,255,.04)', textAlign: 'center' }}>
                      <span style={{ fontSize: 12, color: '#5A5A6E' }}>
                        {variation.html ? `Click to view (${Math.round(variation.html.length / 1024)}KB)` : 'No content'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            {/* Success banner */}
            <div className="banner-accent float-in" style={{ background: 'linear-gradient(90deg, rgba(199,255,61,.06), transparent)', border: '1px solid rgba(199,255,61,.22)' }}>
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#C7FF3D' }} />
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(199,255,61,.1)', border: '1px solid rgba(199,255,61,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Check size={16} style={{ color: '#C7FF3D' }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#F5F5FA' }}>Website Generated Successfully!</div>
                <div style={{ fontSize: 12, color: '#86869A', marginTop: 2 }}>
                  Template: <span style={{ fontWeight: 600 }}>{templateUsed}</span> · Features: <span style={{ fontWeight: 600 }}>{detectedFeatures.join(', ')}</span>
                  {selectedStyle && <> · Style: <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{selectedStyle}</span></>}
                </div>
              </div>
            </div>

            {/* Published URL bar */}
            {publishedUrl && (
              <div className="cr-card cr-card-hairline float-in" style={{ padding: '20px 24px', marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#C7FF3D', marginBottom: 8 }}>Website Published!</div>
                <div style={{ fontSize: 13, color: '#86869A', marginBottom: 12 }}>Your website is now live at:</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input type="text" value={publishedUrl} readOnly className="cr-input" style={{ flex: 1 }} />
                  <a href={publishedUrl} target="_blank" rel="noopener noreferrer" className="cr-btn" style={{ background: 'linear-gradient(180deg, #6B5CFF, #4F3DFF)', color: '#fff', textDecoration: 'none', boxShadow: '0 0 0 1px rgba(107,92,255,.5), 0 8px 24px rgba(79,61,255,.35)' }}>
                    <Eye size={14} /> View Live
                  </a>
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 24 }}>
              {selectedStyle && styleVariations.length > 0 && (
                <button onClick={handleBackToVariations} className="cr-btn cr-btn-ghost">← Back to Variations</button>
              )}
              <button onClick={() => setPreviewMode(previewMode === 'single' ? 'multi' : 'single')} className="cr-btn cr-btn-ghost" title={previewMode === 'single' ? 'View on all devices' : 'View single device'}>
                <Layout size={14} /> {previewMode === 'single' ? 'Multi-Device' : 'Single Device'}
              </button>
              <button onClick={handleDownload} className="cr-btn cr-btn-ghost"><Download size={14} /> Download HTML</button>
              <button onClick={handleCopyHtml} className="cr-btn cr-btn-ghost">
                {copied ? <><Check size={14} /> Copied!</> : <><Copy size={14} /> Copy HTML</>}
              </button>
              <button onClick={() => setShowPublishModal(true)} className="cr-btn" style={{ background: 'linear-gradient(180deg, #DDFF7A, #C7FF3D)', color: '#05050C', boxShadow: '0 0 0 1px rgba(199,255,61,.5), 0 8px 24px rgba(199,255,61,.25)' }}>
                <Upload size={14} /> Publish Website
              </button>

              {/* Share dropdown */}
              <div style={{ position: 'relative' }} className="group">
                <button onClick={handleShare} className="cr-btn cr-btn-ghost"><Share2 size={14} /> Share</button>
                <div className="cr-share-menu">
                  <button onClick={() => handleShareSocial('whatsapp')} className="cr-share-item"><span style={{ fontSize: 16 }}>💬</span> WhatsApp</button>
                  <button onClick={() => handleShareSocial('facebook')} className="cr-share-item"><span style={{ fontSize: 16 }}>📘</span> Facebook</button>
                  <button onClick={() => handleShareSocial('twitter')} className="cr-share-item"><span style={{ fontSize: 16 }}>🐦</span> Twitter</button>
                  <button onClick={() => handleShareSocial('linkedin')} className="cr-share-item"><span style={{ fontSize: 16 }}>💼</span> LinkedIn</button>
                </div>
              </div>

              <button onClick={() => { setGeneratedHtml(''); setStyleVariations([]); setSelectedStyle(null); setError(''); setPublishedUrl(''); }} className="cr-btn cr-btn-ghost">Create Another</button>
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
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(5,5,12,.85)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16 }}>
          <div className="cr-card cr-card-hairline" style={{ maxWidth: 460, width: '100%', padding: 32 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: '#F5F5FA', margin: 0 }}>Publish Your Website</h2>
              <button onClick={() => { setShowPublishModal(false); setError(''); setSubdomainError(null); }} className="cr-btn-icon" aria-label="Close">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
              </button>
            </div>

            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#86869A', marginBottom: 6 }}>Project Name</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="My Restaurant"
                className="cr-input"
              />
            </div>

            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#86869A', marginBottom: 6 }}>Choose Subdomain</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
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
                  className="cr-input"
                  style={{ flex: 1, borderColor: subdomainError ? 'rgba(239,68,68,.5)' : undefined }}
                />
                <span style={{ fontSize: 13, color: '#5A5A6E', whiteSpace: 'nowrap' }}>.binaapp.my</span>
              </div>
              {subdomainError ? (
                <p style={{ fontSize: 12, color: '#FCA5A5', marginTop: 6, fontWeight: 500 }}>
                  {subdomainError}
                </p>
              ) : (
                <p style={{ fontSize: 12, color: '#5A5A6E', marginTop: 6 }}>
                  Only lowercase letters, numbers, and hyphens
                </p>
              )}
            </div>

            {error && (
              <div className="banner-accent" style={{ marginBottom: 18, background: 'linear-gradient(90deg, rgba(239,68,68,.06), transparent)', border: '1px solid rgba(239,68,68,.22)' }}>
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#EF4444' }} />
                <span style={{ fontSize: 13, color: '#FCA5A5' }}>{error}</span>
              </div>
            )}

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={() => { setShowPublishModal(false); setError(''); setSubdomainError(null); }}
                className="cr-btn cr-btn-ghost"
                style={{ flex: 1 }}
                disabled={publishing}
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                className="cr-btn"
                style={{ flex: 1, background: 'linear-gradient(180deg, #DDFF7A, #C7FF3D)', color: '#05050C', boxShadow: '0 0 0 1px rgba(199,255,61,.5), 0 8px 24px rgba(199,255,61,.25)', opacity: publishing || !subdomain || !projectName || !!subdomainError ? .35 : 1, cursor: publishing || !subdomain || !projectName || !!subdomainError ? 'not-allowed' : 'pointer' }}
                disabled={publishing || !subdomain || !projectName || !!subdomainError}
              >
                {publishing ? 'Publishing...' : 'Publish Now'}
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
