/**
 * Create Page - AI Website Generation
 */
'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Sparkles, Download, Upload, Eye, Copy, Check, Share2, Layout } from 'lucide-react'
import VisualImageUpload from './components/VisualImageUpload'
import DevicePreview from './components/DevicePreview'
import MultiDevicePreview from './components/MultiDevicePreview'
import CodeAnimation from '@/components/CodeAnimation'
import { API_BASE_URL, DIRECT_BACKEND_URL } from '@/lib/env'
import { supabase, signOut } from '@/lib/supabase'
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
  const [businessType, setBusinessType] = useState<'auto' | 'food' | 'clothing' | 'services' | 'general'>('auto')

  // Delivery system states
  const [deliveryArea, setDeliveryArea] = useState('')
  const [deliveryFee, setDeliveryFee] = useState('')
  const [minimumOrder, setMinimumOrder] = useState('')
  const [deliveryHours, setDeliveryHours] = useState('')

  // Google Map state
  const [fullAddress, setFullAddress] = useState('')

  // Social media states
  const [instagram, setInstagram] = useState('')
  const [facebook, setFacebook] = useState('')
  const [tiktok, setTiktok] = useState('')

  useEffect(() => {
    checkUser()
  }, [])

  async function checkUser() {
    if (!supabase) {
      setAuthLoading(false)
      return
    }

    try {
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
      await signOut()
      setUser(null)
      router.push('/')
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  const handleGenerate = async () => {
    if (!description.trim()) return;

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

      const startResponse = await fetch('https://binaapp-backend.onrender.com/api/generate/start', {
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
          } : null
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

      console.log('✅ Job started:', jobId);

      // Step 2: Poll for results
      const maxAttempts = 100; // 100 attempts x 3 seconds = 5 minutes max (increased from 3 min)
      let attempt = 0;

      const pollInterval = setInterval(async () => {
        attempt++;

        if (attempt > maxAttempts) {
          clearInterval(pollInterval);
          setError('Generation timed out after 5 minutes. Please try again with a shorter description.');
          setLoading(false);
          return;
        }

        try {
          const statusResponse = await fetch(
            `https://binaapp-backend.onrender.com/api/generate/status/${jobId}`
          );

          if (!statusResponse.ok) {
            console.warn('Status check failed, retrying...');
            return; // Continue polling
          }

          const statusData = await statusResponse.json();
          console.log(`📊 Progress: ${statusData.progress}%`, statusData.status);

          // Update progress bar
          setProgress(statusData.progress || 0);

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            console.log('✅ Generation complete!');

            // Set progress to 100% FIRST (before hiding modal)
            setProgress(100);

            // Handle completed job
            if (statusData.styles?.length > 0) {
              setStyleVariations(statusData.styles);
              setSelectedStyle(null);
            } else if (statusData.html) {
              setStyleVariations([{ style: 'modern', html: statusData.html }]);
              setSelectedStyle(null);
            }

            // Hide loading modal AFTER setting progress to 100%
            setLoading(false);
          } else if (statusData.status === 'failed') {
            clearInterval(pollInterval);
            setError(statusData.error || 'Generation failed. Please try again.');
            setLoading(false);
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
      setLoading(false);
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

    setPublishing(true)
    setError('')

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
          menu_items: menuItemsForDelivery
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
            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2 text-gray-700">
                Jenis Perniagaan / Business Type:
              </label>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                <button
                  onClick={() => setBusinessType('auto')}
                  className={`btn ${businessType === 'auto' ? 'btn-primary' : 'btn-outline'} text-sm`}
                >
                  🔍 Auto Detect
                </button>
                <button
                  onClick={() => setBusinessType('food')}
                  className={`btn ${businessType === 'food' ? 'btn-primary' : 'btn-outline'} text-sm`}
                >
                  🍛 Makanan
                </button>
                <button
                  onClick={() => setBusinessType('clothing')}
                  className={`btn ${businessType === 'clothing' ? 'btn-primary' : 'btn-outline'} text-sm`}
                >
                  👗 Pakaian
                </button>
                <button
                  onClick={() => setBusinessType('services')}
                  className={`btn ${businessType === 'services' ? 'btn-primary' : 'btn-outline'} text-sm`}
                >
                  🔧 Servis
                </button>
                <button
                  onClick={() => setBusinessType('general')}
                  className={`btn ${businessType === 'general' ? 'btn-primary' : 'btn-outline'} text-sm`}
                >
                  🛒 Lain-lain
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {businessType === 'auto' && 'Sistem akan mengesan jenis perniagaan anda secara automatik'}
                {businessType === 'food' && 'Kategori: Nasi, Lauk, Minuman | Label: Pesan Delivery'}
                {businessType === 'clothing' && 'Kategori: Baju, Tudung, Aksesori | Label: Order Sekarang'}
                {businessType === 'services' && 'Kategori: Perkhidmatan, Pakej | Label: Tempah Sekarang'}
                {businessType === 'general' && 'Kategori: Produk, Lain-lain | Label: Beli Sekarang'}
              </p>
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

            {/* If Delivery selected, show delivery settings */}
            {selectedFeatures.deliverySystem && (
              <div className="bg-orange-50 rounded-xl p-6 mt-4 border border-orange-200">
                <h4 className="font-bold text-orange-800 mb-3">🛵 Tetapan Delivery</h4>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Kawasan Delivery</label>
                    <input
                      type="text"
                      placeholder="cth: Shah Alam, Klang, Subang (5km radius)"
                      className="w-full px-4 py-2 border rounded-lg"
                      value={deliveryArea}
                      onChange={(e) => setDeliveryArea(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Caj Delivery</label>
                    <input
                      type="text"
                      placeholder="cth: RM5 (dalam 3km), RM8 (3-5km)"
                      className="w-full px-4 py-2 border rounded-lg"
                      value={deliveryFee}
                      onChange={(e) => setDeliveryFee(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Minimum Order</label>
                    <input
                      type="text"
                      placeholder="cth: RM20"
                      className="w-full px-4 py-2 border rounded-lg"
                      value={minimumOrder}
                      onChange={(e) => setMinimumOrder(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Waktu Delivery</label>
                    <input
                      type="text"
                      placeholder="cth: 11am - 9pm"
                      className="w-full px-4 py-2 border rounded-lg"
                      value={deliveryHours}
                      onChange={(e) => setDeliveryHours(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}

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
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-2 h-2 rounded-full ${progress >= 10 ? 'bg-blue-500 animate-pulse' : 'bg-gray-600'}`}></div>
                      <span className="text-sm">Analyzing your business description...</span>
                    </div>
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-2 h-2 rounded-full ${progress >= 33 ? 'bg-purple-500 animate-pulse' : 'bg-gray-600'}`}></div>
                      <span className="text-sm">Generating Modern style...</span>
                    </div>
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-2 h-2 rounded-full ${progress >= 66 ? 'bg-pink-500 animate-pulse' : 'bg-gray-600'}`}></div>
                      <span className="text-sm">Generating Minimal style...</span>
                    </div>
                    <div className="flex items-center gap-3 text-gray-300">
                      <div className={`w-2 h-2 rounded-full ${progress >= 99 ? 'bg-orange-500 animate-pulse' : 'bg-gray-600'}`}></div>
                      <span className="text-sm">Generating Bold style...</span>
                    </div>
                  </div>

                  <p className="text-xs text-gray-500 mt-6 text-center">
                    This usually takes 45-90 seconds. Progress updates every 3 seconds ⏱️
                  </p>
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
    </div>
  )
}
