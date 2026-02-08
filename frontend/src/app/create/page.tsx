/**
 * Create Page - AI Website Generation
 */
'use client'
import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
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
        setCurrentTier(data.plan_name || 'free')
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

      const response = await fetch(`${DIRECT_BACKEND_URL}/api/v1/subscription/check-limit`, {
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
      // Allow on error (backend will enforce anyway)
      return true
    }
  }

  // Check if user can use AI images
  async function checkAIImageLimit(): Promise<boolean> {
    if (imageChoice !== 'ai') return true

    try {
      const token = getStoredToken()
      if (!token) return true

      const response = await fetch(`${DIRECT_BACKEND_URL}/api/v1/subscription/check-limit`, {
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
      return true
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
        throw new Error(errorData.detail || 'Gagal menerbitkan website')
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
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
            {!authLoading && (
              user ? (
                <>
                  <Link href="/profile" className="text-sm text-gray-600 hover:text-gray-900">
                    Profil
                  </Link>
                  <Link href="/my-projects" className="text-sm text-gray-600 hover:text-gray-900">
                    Website Saya
                  </Link>
                  <Link href="/dashboard/billing" className="text-sm text-gray-600 hover:text-gray-900">
                    💎 Langganan
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-sm text-red-500 hover:text-red-600"
                  >
                    Log Keluar
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">
                    Log Masuk
                  </Link>
                  <Link href="/register" className="btn btn-primary btn-sm">
                    Daftar
                  </Link>
                </>
              )
            )}
          </div>
        </nav>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-3">
            ✨ Create Your Website with AI
          </h1>
          <p className="text-gray-600 text-lg">
            Describe your business in Bahasa Malaysia or English, and let AI build your website
          </p>
        </div>

        {!generatedHtml && styleVariations.length === 0 ? (
          <div className="max-w-4xl mx-auto">
            {/* Subscription Required Banner */}
            {!subscriptionLoading && hasActiveSubscription === false && user && (
              <div className="mb-6 p-6 bg-red-50 border-2 border-red-300 rounded-xl">
                <div className="flex flex-col md:flex-row items-center gap-4">
                  <span className="text-4xl">🔒</span>
                  <div className="flex-1 text-center md:text-left">
                    <h3 className="text-red-800 font-bold text-lg mb-1">Langganan Diperlukan</h3>
                    <p className="text-red-700 text-sm">
                      Anda perlu melanggan pelan untuk mencipta website. Bermula dari RM5/bulan sahaja.
                    </p>
                  </div>
                  <a
                    href="/dashboard/billing"
                    className="px-6 py-3 bg-red-600 text-white font-bold rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap"
                  >
                    Langgan Sekarang
                  </a>
                </div>
              </div>
            )}

            {/* Not Logged In Banner */}
            {!authLoading && !user && (
              <div className="mb-6 p-6 bg-blue-50 border-2 border-blue-300 rounded-xl">
                <div className="flex flex-col md:flex-row items-center gap-4">
                  <span className="text-4xl">👤</span>
                  <div className="flex-1 text-center md:text-left">
                    <h3 className="text-blue-800 font-bold text-lg mb-1">Log Masuk Diperlukan</h3>
                    <p className="text-blue-700 text-sm">
                      Sila log masuk dan langgan untuk mencipta website. Bermula dari RM5/bulan sahaja.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href="/login?redirect=/create"
                      className="px-6 py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
                    >
                      Log Masuk
                    </a>
                    <a
                      href="/register"
                      className="px-6 py-3 border-2 border-blue-600 text-blue-600 font-bold rounded-lg hover:bg-blue-50 transition-colors whitespace-nowrap"
                    >
                      Daftar
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* Limit Warning Banner */}
            {limitWarning && (
              <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">⚠️</span>
                  <div className="flex-1">
                    <p className="text-orange-800 font-medium">{limitWarning}</p>
                    <p className="text-orange-700 text-sm mt-1">
                      Naik taraf pelan anda untuk lebih banyak website.
                    </p>
                  </div>
                  <a
                    href="/dashboard/billing"
                    className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 transition-colors"
                  >
                    Naik Taraf
                  </a>
                </div>
              </div>
            )}

            <div style={{ marginBottom: '20px' }}>
              <a href="/menu-designer" style={{
                display: 'inline-block',
                padding: '12px 24px',
                background: '#16a34a',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '8px',
                fontWeight: 'bold'
              }}>
                🍽️ Create Print Menu
              </a>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold mb-3 text-gray-700">
                Try an example:
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {EXAMPLE_DESCRIPTIONS.map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => fillExample(example)}
                    className="btn btn-outline btn-sm text-left justify-start"
                  >
                    {example.title}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2 text-gray-700">
                Language:
              </label>
              <div className="flex gap-3">
                <button
                  onClick={() => setLanguage('ms')}
                  className={`btn ${language === 'ms' ? 'btn-primary' : 'btn-outline'}`}
                >
                  🇲🇾 Bahasa Malaysia
                </button>
                <button
                  onClick={() => setLanguage('en')}
                  className={`btn ${language === 'en' ? 'btn-primary' : 'btn-outline'}`}
                >
                  🇬🇧 English
                </button>
              </div>
            </div>

            {/* Business Type Selector - for dynamic categories */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3">🏪 Jenis Perniagaan</h3>
              <p className="text-gray-500 text-sm mb-3">Pilih jenis perniagaan anda</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { id: 'auto' as const, icon: '🔍', label: 'Auto Detect', desc: 'Sistem akan kesan automatik' },
                  { id: 'food' as const, icon: '🍛', label: 'Restoran / Makanan', desc: 'Nasi, Lauk, Minuman' },
                  { id: 'clothing' as const, icon: '👗', label: 'Pakaian / Butik', desc: 'Baju, Tudung, Aksesori' },
                  { id: 'salon' as const, icon: '💇', label: 'Salon / Spa', desc: 'Potong, Rawatan, Warna' },
                  { id: 'services' as const, icon: '🔧', label: 'Servis / Repair', desc: 'Perkhidmatan, Pakej' },
                  { id: 'bakery' as const, icon: '🎂', label: 'Bakeri / Kek', desc: 'Kek, Pastri, Cookies' },
                  { id: 'general' as const, icon: '🛒', label: 'Lain-lain', desc: 'Produk Umum' }
                ].map(type => (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setBusinessType(type.id)}
                    className={`p-4 border-2 rounded-xl text-center transition ${
                      businessType === type.id
                        ? 'border-orange-500 bg-orange-50'
                        : 'border-gray-200 hover:border-orange-300'
                    }`}
                  >
                    <span className="text-3xl block mb-1">{type.icon}</span>
                    <p className="text-sm font-medium">{type.label}</p>
                    <p className="text-xs text-gray-500 mt-1">{type.desc}</p>
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-2">
                {businessType === 'auto' && '💡 Sistem akan mengesan jenis perniagaan anda secara automatik dari deskripsi'}
                {businessType === 'food' && '🛵 Butang: "Pesan Delivery" | Kategori: Nasi, Lauk, Minuman'}
                {businessType === 'clothing' && '🛍️ Butang: "Beli Sekarang" | Pilihan saiz & warna | Penghantaran'}
                {businessType === 'salon' && '📅 Butang: "Tempah Sekarang" | Tarikh temujanji & pilih staff'}
                {businessType === 'services' && '🔧 Butang: "Tempah Servis" | Tarikh & lokasi servis'}
                {businessType === 'bakery' && '🎂 Butang: "Tempah Kek" | Pilihan saiz & mesej atas kek'}
                {businessType === 'general' && '🛒 Butang: "Beli Sekarang" | Pilihan penghantaran'}
              </p>
            </div>

            {/* Color Mode Selector */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3">🎨 Tema Warna / Color Theme</h3>
              <p className="text-gray-500 text-sm mb-3">Pilih tema warna untuk website anda</p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setColorMode('light')}
                  className={`p-4 border-2 rounded-xl text-center transition ${
                    colorMode === 'light'
                      ? 'border-orange-500 bg-orange-50'
                      : 'border-gray-200 hover:border-orange-300'
                  }`}
                >
                  <span className="text-3xl block mb-1">&#9728;&#65039;</span>
                  <p className="text-sm font-medium">Cerah / Light</p>
                  <p className="text-xs text-gray-500 mt-1">Latar belakang terang</p>
                </button>
                <button
                  type="button"
                  onClick={() => setColorMode('dark')}
                  className={`p-4 border-2 rounded-xl text-center transition ${
                    colorMode === 'dark'
                      ? 'border-orange-500 bg-orange-50'
                      : 'border-gray-200 hover:border-orange-300'
                  }`}
                >
                  <span className="text-3xl block mb-1">&#127769;</span>
                  <p className="text-sm font-medium">Gelap / Dark</p>
                  <p className="text-xs text-gray-500 mt-1">Latar belakang gelap</p>
                </button>
              </div>
            </div>

            <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
              <label className="flex items-center gap-3 cursor-pointer mb-3">
                <input
                  type="checkbox"
                  checked={multiStyle}
                  onChange={(e) => setMultiStyle(e.target.checked)}
                  className="w-5 h-5 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <div>
                  <span className="font-semibold text-gray-900">
                    ✨ Generate Multiple Styles (Recommended)
                  </span>
                  <p className="text-sm text-gray-600 mt-1">
                    Get 3 design variations (Modern, Minimal, Bold) and choose your favorite
                  </p>
                </div>
              </label>
              
              {multiStyle && (
                <label className="flex items-center gap-3 cursor-pointer ml-8">
                  <input
                    type="checkbox"
                    checked={generatePreviews}
                    onChange={(e) => setGeneratePreviews(e.target.checked)}
                    className="w-5 h-5 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                  <div>
                    <span className="font-medium text-gray-800">
                      📸 Generate Preview Thumbnails
                    </span>
                    <p className="text-xs text-gray-600 mt-0.5">
                      Takes 10-15 seconds longer but shows better previews
                    </p>
                  </div>
                </label>
              )}
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2 text-gray-700">
                Describe your business:
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={
                  language === 'ms'
                    ? 'Contoh: Saya ada kedai runcit di Shah Alam yang jual barangan harian, makanan, dan minuman. Harga berpatutan dari RM1. Lokasi di Seksyen 7 Shah Alam. Telefon 019-1234567. Buka 7am-10pm setiap hari...'
                    : 'Example: I have a coffee shop in Kuala Lumpur serving specialty coffee, cakes, and light meals. Prices from RM8. Located at TTDI. Contact via WhatsApp 012-3456789. Open daily 8am-6pm...'
                }
                className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              />
              <div className="text-right text-sm text-gray-500 mt-1">
                {description.length} characters
              </div>
            </div>

            <VisualImageUpload onImagesUploaded={setUploadedImages} />

            {/* STRICT IMAGE CONTROL - Explicit User Choice */}
            <div className="bg-white rounded-xl p-6 shadow-lg mt-6 border-2 border-purple-200">
              <h3 className="text-lg font-bold mb-2">🖼️ Gambar untuk Website</h3>
              <p className="text-gray-500 text-sm mb-4">Pilih bagaimana anda mahu gambar dalam website anda</p>

              <div className="space-y-3">
                {/* Option 1: No Images */}
                <label className={`flex items-center gap-3 p-4 border-2 rounded-xl cursor-pointer transition-colors ${
                  imageChoice === 'none' ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-300'
                }`}>
                  <input
                    type="radio"
                    name="imageChoice"
                    value="none"
                    checked={imageChoice === 'none'}
                    onChange={() => setImageChoice('none')}
                    className="w-5 h-5 text-purple-600"
                  />
                  <span className="text-2xl">📝</span>
                  <div className="flex-1">
                    <p className="font-semibold">Tiada Gambar</p>
                    <p className="text-sm text-gray-500">Website teks sahaja, tanpa gambar</p>
                  </div>
                </label>

                {/* Option 2: Upload Own Images */}
                <label className={`flex items-center gap-3 p-4 border-2 rounded-xl cursor-pointer transition-colors ${
                  imageChoice === 'upload' ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-300'
                }`}>
                  <input
                    type="radio"
                    name="imageChoice"
                    value="upload"
                    checked={imageChoice === 'upload'}
                    onChange={() => setImageChoice('upload')}
                    className="w-5 h-5 text-purple-600"
                  />
                  <span className="text-2xl">📷</span>
                  <div className="flex-1">
                    <p className="font-semibold">Muat Naik Gambar Sendiri</p>
                    <p className="text-sm text-gray-500">Gunakan gambar yang anda upload di atas</p>
                  </div>
                  {uploadedImages.gallery.length > 0 && (
                    <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                      {uploadedImages.gallery.length} gambar dimuat naik
                    </span>
                  )}
                </label>

                {/* Option 3: Generate AI Images */}
                <label className={`flex items-center gap-3 p-4 border-2 rounded-xl cursor-pointer transition-colors ${
                  imageChoice === 'ai' ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-300'
                }`}>
                  <input
                    type="radio"
                    name="imageChoice"
                    value="ai"
                    checked={imageChoice === 'ai'}
                    onChange={() => setImageChoice('ai')}
                    className="w-5 h-5 text-purple-600"
                  />
                  <span className="text-2xl">✨</span>
                  <div className="flex-1">
                    <p className="font-semibold">Jana Gambar AI</p>
                    <p className="text-sm text-gray-500">AI akan jana gambar untuk perniagaan anda</p>
                  </div>
                  <span className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded-full">
                    Premium
                  </span>
                </label>
              </div>

              {/* Warning if upload selected but no images */}
              {imageChoice === 'upload' && uploadedImages.gallery.length === 0 && !uploadedImages.hero && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-yellow-800 text-sm">
                    ⚠️ Anda belum muat naik gambar. Sila muat naik gambar di bahagian atas atau pilih pilihan lain.
                  </p>
                </div>
              )}
            </div>

            {/* Feature Selector */}
            <div className="bg-white rounded-xl p-6 shadow-lg mt-6">
              <h3 className="text-lg font-bold mb-2">⚡ Pilih Ciri-ciri Website</h3>
              <p className="text-gray-500 text-sm mb-4">Pilih apa yang anda mahu dalam website anda</p>

              <div className="grid grid-cols-2 gap-3">
                {/* WhatsApp */}
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedFeatures.whatsapp}
                    onChange={(e) => setSelectedFeatures({...selectedFeatures, whatsapp: e.target.checked})}
                    className="w-5 h-5 text-green-600"
                  />
                  <span className="ml-3">
                    <span className="text-xl">💬</span>
                    <span className="ml-2 font-medium">WhatsApp</span>
                  </span>
                </label>

                {/* Google Map */}
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedFeatures.googleMap}
                    onChange={(e) => setSelectedFeatures({...selectedFeatures, googleMap: e.target.checked})}
                    className="w-5 h-5 text-blue-600"
                  />
                  <span className="ml-3">
                    <span className="text-xl">📍</span>
                    <span className="ml-2 font-medium">Google Map</span>
                  </span>
                </label>

                {/* Delivery System */}
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedFeatures.deliverySystem}
                    onChange={(e) => setSelectedFeatures({...selectedFeatures, deliverySystem: e.target.checked})}
                    className="w-5 h-5 text-orange-600"
                  />
                  <span className="ml-3">
                    <span className="text-xl">🛵</span>
                    <span className="ml-2 font-medium">Delivery Sendiri</span>
                  </span>
                </label>

                {/* Contact Form */}
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedFeatures.contactForm}
                    onChange={(e) => setSelectedFeatures({...selectedFeatures, contactForm: e.target.checked})}
                    className="w-5 h-5 text-purple-600"
                  />
                  <span className="ml-3">
                    <span className="text-xl">📧</span>
                    <span className="ml-2 font-medium">Borang Hubungi</span>
                  </span>
                </label>

                {/* Social Media */}
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedFeatures.socialMedia}
                    onChange={(e) => setSelectedFeatures({...selectedFeatures, socialMedia: e.target.checked})}
                    className="w-5 h-5 text-pink-600"
                  />
                  <span className="ml-3">
                    <span className="text-xl">📱</span>
                    <span className="ml-2 font-medium">Social Media</span>
                  </span>
                </label>

                {/* Price List */}
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedFeatures.priceList}
                    onChange={(e) => setSelectedFeatures({...selectedFeatures, priceList: e.target.checked})}
                    className="w-5 h-5 text-yellow-600"
                  />
                  <span className="ml-3">
                    <span className="text-xl">💰</span>
                    <span className="ml-2 font-medium">Senarai Harga</span>
                  </span>
                </label>
              </div>
            </div>

            {/* If Google Map selected, ask for address */}
            {selectedFeatures.googleMap && (
              <div className="bg-blue-50 rounded-xl p-6 mt-4 border border-blue-200">
                <h4 className="font-bold text-blue-800 mb-3">📍 Google Map</h4>
                <div>
                  <label className="block text-sm font-medium mb-1">Alamat Penuh</label>
                  <input
                    type="text"
                    placeholder="cth: 123, Jalan Sultan, Shah Alam, Selangor"
                    className="w-full px-4 py-2 border rounded-lg"
                    value={fullAddress}
                    onChange={(e) => setFullAddress(e.target.value)}
                  />
                </div>
              </div>
            )}

            {/* If Social Media selected */}
            {selectedFeatures.socialMedia && (
              <div className="bg-pink-50 rounded-xl p-6 mt-4 border border-pink-200">
                <h4 className="font-bold text-pink-800 mb-3">📱 Social Media</h4>
                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Instagram: @username"
                    className="w-full px-4 py-2 border rounded-lg"
                    value={instagram}
                    onChange={(e) => setInstagram(e.target.value)}
                  />
                  <input
                    type="text"
                    placeholder="Facebook: page name or URL"
                    className="w-full px-4 py-2 border rounded-lg"
                    value={facebook}
                    onChange={(e) => setFacebook(e.target.value)}
                  />
                  <input
                    type="text"
                    placeholder="TikTok: @username"
                    className="w-full px-4 py-2 border rounded-lg"
                    value={tiktok}
                    onChange={(e) => setTiktok(e.target.value)}
                  />
                </div>
              </div>
            )}

            {/* Delivery Settings - Only show if Delivery Sendiri is checked */}
            {selectedFeatures.deliverySystem && (
              <div className="bg-orange-50 rounded-xl p-6 mt-4 border border-orange-200">
                <h4 className="font-bold text-orange-800 mb-3">🛵 Tetapan Delivery</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm text-gray-600">Caj Delivery (RM)</label>
                    <input 
                      type="number" 
                      placeholder="5.00" 
                      step="0.50"
                      value={fulfillment.deliveryFee}
                      onChange={(e) => setFulfillment({...fulfillment, deliveryFee: e.target.value})}
                      className="w-full p-2 border rounded-lg mt-1" 
                    />
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Min. Order (RM)</label>
                    <input 
                      type="number" 
                      placeholder="20.00" 
                      step="1"
                      value={fulfillment.minOrder}
                      onChange={(e) => setFulfillment({...fulfillment, minOrder: e.target.value})}
                      className="w-full p-2 border rounded-lg mt-1" 
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="text-sm text-gray-600">Kawasan Delivery</label>
                    <input 
                      type="text" 
                      placeholder="Shah Alam, Klang, Subang"
                      value={fulfillment.deliveryArea}
                      onChange={(e) => setFulfillment({...fulfillment, deliveryArea: e.target.value})}
                      className="w-full p-2 border rounded-lg mt-1" 
                    />
                  </div>
                </div>

                {/* Self Pickup Option - Nested under Delivery */}
                <div className="mt-4 pt-4 border-t border-orange-200">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={fulfillment.pickup}
                      onChange={(e) => setFulfillment({...fulfillment, pickup: e.target.checked})}
                      className="w-5 h-5 rounded accent-orange-500" 
                    />
                    <span className="text-xl">🏪</span>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-800">Self Pickup</p>
                      <p className="text-sm text-gray-500">Pelanggan ambil di kedai</p>
                    </div>
                    <span className="text-green-600 font-bold">FREE</span>
                  </label>
                  
                  {fulfillment.pickup && (
                    <div className="mt-3 pl-10">
                      <label className="text-sm text-gray-600">Alamat Pickup</label>
                      <input 
                        type="text" 
                        placeholder="No. 123, Jalan ABC, Shah Alam"
                        value={fulfillment.pickupAddress}
                        onChange={(e) => setFulfillment({...fulfillment, pickupAddress: e.target.value})}
                        className="w-full p-2 border rounded-lg mt-1" 
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Payment Settings - QR + COD only */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border mt-6">
              <h3 className="text-lg font-semibold mb-2">💳 Tetapan Pembayaran</h3>
              <p className="text-gray-500 text-sm mb-4">Pilih cara pembayaran yang anda terima</p>
              
              {/* Payment Methods */}
              <div className="space-y-3 mb-4">
                {/* COD */}
                <label className="flex items-center gap-3 p-4 border-2 rounded-xl cursor-pointer hover:border-orange-300 transition-colors">
                  <input 
                    type="checkbox" 
                    checked={paymentMethods.cod}
                    onChange={(e) => setPaymentMethods({...paymentMethods, cod: e.target.checked})}
                    className="w-5 h-5 rounded accent-orange-500" 
                  />
                  <span className="text-2xl">💵</span>
                  <div>
                    <p className="font-semibold">Cash on Delivery (COD)</p>
                    <p className="text-sm text-gray-500">Bayar tunai bila terima</p>
                  </div>
                </label>
                
                {/* QR Payment */}
                <label className="flex items-center gap-3 p-4 border-2 rounded-xl cursor-pointer hover:border-orange-300 transition-colors">
                  <input 
                    type="checkbox"
                    checked={paymentMethods.qr}
                    onChange={(e) => setPaymentMethods({...paymentMethods, qr: e.target.checked})}
                    className="w-5 h-5 rounded accent-orange-500" 
                  />
                  <span className="text-2xl">📱</span>
                  <div>
                    <p className="font-semibold">QR Payment</p>
                    <p className="text-sm text-gray-500">DuitNow / TNG / Bank QR</p>
                  </div>
                </label>
              </div>
              
              {/* QR Upload - Only show if QR payment enabled */}
              {paymentMethods.qr && (
                <div className="bg-orange-50 rounded-xl p-4 border border-orange-200">
                  <p className="font-medium mb-3">📱 Muat Naik QR Pembayaran Anda</p>
                  <div className="flex gap-4 items-start">
                    {/* QR Upload Box */}
                    <div className="w-32 h-32 border-2 border-dashed border-orange-300 rounded-xl bg-white flex-shrink-0">
                      <label className="cursor-pointer w-full h-full flex flex-col items-center justify-center">
                        <input 
                          type="file" 
                          accept="image/*" 
                          className="hidden"
                          onChange={handleQRUpload} 
                        />
                        {paymentQRPreview ? (
                          <img 
                            src={paymentQRPreview} 
                            alt="Payment QR"
                            className="w-full h-full object-contain rounded-xl p-1" 
                          />
                        ) : (
                          <>
                            <span className="text-3xl mb-1">📷</span>
                            <span className="text-xs text-gray-500">Upload QR</span>
                          </>
                        )}
                      </label>
                    </div>
                    
                    {/* Instructions */}
                    <div className="flex-1 text-sm text-gray-600">
                      <p className="font-medium text-gray-800 mb-2">Cara mendapatkan QR:</p>
                      <ol className="list-decimal list-inside space-y-1">
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
              disabled={loading || description.length < 10}
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
      </div>

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
