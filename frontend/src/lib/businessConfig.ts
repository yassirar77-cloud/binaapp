/**
 * Business Configuration for Universal Order System
 *
 * This module provides dynamic configuration for different business types.
 * Each business type has its own set of labels, categories, and features
 * to support various ordering workflows (delivery, booking, purchasing).
 */

export interface Category {
  id: string;
  name: string;
  icon: string;
}

export interface ShippingOption {
  id: string;
  name: string;
  price: number;
  desc: string;
}

export interface StaffMember {
  id: number;
  name: string;
  icon: string;
}

export interface LocationOption {
  id: string;
  name: string;
  icon: string;
  extraFee: number;
}

export interface BusinessFeatures {
  deliveryZones: boolean;
  timeSlots: boolean;
  specialInstructions: boolean;
  promoCode: boolean;
  sizeOptions: boolean;
  colorOptions: boolean;
  appointmentDate: boolean;
  staffSelection: boolean;
  shippingOptions: boolean;
  customMessage: boolean;
  locationChoice?: boolean;
}

export interface BusinessLabels {
  instructionPlaceholder: string;
  deliveryFee: string | null;
  minOrder: string | null;
  addToCart: string;
  checkout: string;
}

export interface BusinessConfig {
  icon: string;
  buttonLabel: string;
  pageTitle: string;
  orderTitle: string;
  emoji: string;
  cartIcon: string;
  cartLabel: string;
  categories: Category[];
  features: BusinessFeatures;
  labels: BusinessLabels;
  sizes?: string[];
  shippingOptions?: ShippingOption[];
  defaultStaff?: StaffMember[];
  locationOptions?: LocationOption[];
  customMessagePlaceholder?: string;
  primaryColor: string;
}

export const businessConfig: Record<string, BusinessConfig> = {
  food: {
    icon: '🛵',
    buttonLabel: 'Pesan Delivery',
    pageTitle: 'Pesan Delivery',
    orderTitle: 'PESANAN DELIVERY',
    emoji: '🍛',
    cartIcon: '🛒',
    cartLabel: 'Bakul Pesanan',
    primaryColor: '#ea580c',
    categories: [
      { id: 'all', name: 'Semua', icon: '📋' },
      { id: 'nasi', name: 'Nasi', icon: '🍚' },
      { id: 'lauk', name: 'Lauk', icon: '🍗' },
      { id: 'minuman', name: 'Minuman', icon: '🥤' }
    ],
    features: {
      deliveryZones: true,
      timeSlots: true,
      specialInstructions: true,
      promoCode: true,
      sizeOptions: false,
      colorOptions: false,
      appointmentDate: false,
      staffSelection: false,
      shippingOptions: false,
      customMessage: false
    },
    labels: {
      instructionPlaceholder: 'Arahan khas (cth: tak nak bawang, extra pedas)',
      deliveryFee: 'Caj Penghantaran',
      minOrder: 'Min. order',
      addToCart: '+ Tambah',
      checkout: 'WhatsApp Pesanan'
    }
  },

  clothing: {
    icon: '🛍️',
    buttonLabel: 'Beli Sekarang',
    pageTitle: 'Beli Sekarang',
    orderTitle: 'PESANAN BARU',
    emoji: '👗',
    cartIcon: '🛒',
    cartLabel: 'Troli Anda',
    primaryColor: '#ec4899',
    categories: [
      { id: 'all', name: 'Semua', icon: '📋' },
      { id: 'baju', name: 'Baju', icon: '👗' },
      { id: 'tudung', name: 'Tudung', icon: '🧕' },
      { id: 'aksesori', name: 'Aksesori', icon: '👜' }
    ],
    features: {
      deliveryZones: false,
      timeSlots: false,
      specialInstructions: true,
      promoCode: true,
      sizeOptions: true,
      colorOptions: true,
      appointmentDate: false,
      staffSelection: false,
      shippingOptions: true,
      customMessage: false
    },
    labels: {
      instructionPlaceholder: 'Nota pesanan (cth: gift wrap, tukar size jika tak muat)',
      deliveryFee: 'Kos Postage',
      minOrder: 'Min. pembelian',
      addToCart: '+ Tambah',
      checkout: 'WhatsApp Order'
    },
    sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
    shippingOptions: [
      { id: 'cod', name: 'COD (Cash on Delivery)', price: 8, desc: 'Bayar bila terima' },
      { id: 'jnt', name: 'J&T Express', price: 6, desc: '2-3 hari bekerja' },
      { id: 'pos', name: 'Pos Laju', price: 7, desc: '1-2 hari bekerja' },
      { id: 'pickup', name: 'Self Pickup', price: 0, desc: 'Ambil di kedai' }
    ]
  },

  salon: {
    icon: '📅',
    buttonLabel: 'Tempah Sekarang',
    pageTitle: 'Tempah Temujanji',
    orderTitle: 'TEMPAHAN BARU',
    emoji: '💇',
    cartIcon: '📋',
    cartLabel: 'Tempahan Anda',
    primaryColor: '#8b5cf6',
    categories: [
      { id: 'all', name: 'Semua', icon: '📋' },
      { id: 'potong', name: 'Potong', icon: '✂️' },
      { id: 'warna', name: 'Warna', icon: '🎨' },
      { id: 'rawatan', name: 'Rawatan', icon: '💆' }
    ],
    features: {
      deliveryZones: false,
      timeSlots: true,
      specialInstructions: true,
      promoCode: true,
      sizeOptions: false,
      colorOptions: false,
      appointmentDate: true,
      staffSelection: true,
      shippingOptions: false,
      customMessage: false
    },
    labels: {
      instructionPlaceholder: 'Permintaan khas (cth: potong layer, warna ash brown)',
      deliveryFee: null,
      minOrder: null,
      addToCart: '+ Pilih',
      checkout: 'WhatsApp Tempahan'
    },
    defaultStaff: [
      { id: 1, name: 'Sesiapa', icon: '🙋' },
      { id: 2, name: 'Kak Amy', icon: '👩' },
      { id: 3, name: 'Abg Rizal', icon: '👨' }
    ]
  },

  services: {
    icon: '🔧',
    buttonLabel: 'Tempah Servis',
    pageTitle: 'Tempah Servis',
    orderTitle: 'TEMPAHAN SERVIS',
    emoji: '🔧',
    cartIcon: '📋',
    cartLabel: 'Servis Dipilih',
    primaryColor: '#3b82f6',
    categories: [
      { id: 'all', name: 'Semua', icon: '📋' },
      { id: 'servis', name: 'Servis', icon: '🔧' },
      { id: 'pakej', name: 'Pakej', icon: '📦' }
    ],
    features: {
      deliveryZones: true,
      timeSlots: true,
      specialInstructions: true,
      promoCode: true,
      sizeOptions: false,
      colorOptions: false,
      appointmentDate: true,
      staffSelection: false,
      shippingOptions: false,
      customMessage: false,
      locationChoice: true
    },
    labels: {
      instructionPlaceholder: 'Jelaskan masalah (cth: aircond tak sejuk, bunyi bising)',
      deliveryFee: 'Caj Servis',
      minOrder: null,
      addToCart: '+ Pilih',
      checkout: 'WhatsApp Tempahan'
    },
    locationOptions: [
      { id: 'home', name: 'Ke Rumah/Lokasi Saya', icon: '🏠', extraFee: 20 },
      { id: 'shop', name: 'Di Kedai/Workshop', icon: '🏪', extraFee: 0 }
    ]
  },

  bakery: {
    icon: '🎂',
    buttonLabel: 'Tempah Kek',
    pageTitle: 'Tempah Kek',
    orderTitle: 'TEMPAHAN KEK',
    emoji: '🎂',
    cartIcon: '🛒',
    cartLabel: 'Tempahan Anda',
    primaryColor: '#f59e0b',
    categories: [
      { id: 'all', name: 'Semua', icon: '📋' },
      { id: 'kek', name: 'Kek', icon: '🎂' },
      { id: 'pastri', name: 'Pastri', icon: '🥐' },
      { id: 'cookies', name: 'Cookies', icon: '🍪' }
    ],
    features: {
      deliveryZones: true,
      timeSlots: true,
      specialInstructions: true,
      promoCode: true,
      sizeOptions: true,
      colorOptions: false,
      appointmentDate: true,
      staffSelection: false,
      shippingOptions: false,
      customMessage: true
    },
    labels: {
      instructionPlaceholder: 'Permintaan khas (cth: kurang manis, no nuts)',
      deliveryFee: 'Caj Penghantaran',
      minOrder: 'Min. order',
      addToCart: '+ Tambah',
      checkout: 'WhatsApp Tempahan'
    },
    sizes: ['0.5kg', '1kg', '1.5kg', '2kg', '3kg'],
    customMessagePlaceholder: 'Tulis mesej atas kek (cth: Happy Birthday Ali!)'
  },

  general: {
    icon: '🛒',
    buttonLabel: 'Beli Sekarang',
    pageTitle: 'Beli Sekarang',
    orderTitle: 'PESANAN BARU',
    emoji: '📦',
    cartIcon: '🛒',
    cartLabel: 'Troli Anda',
    primaryColor: '#10b981',
    categories: [
      { id: 'all', name: 'Semua', icon: '📋' },
      { id: 'produk', name: 'Produk', icon: '🎁' },
      { id: 'lain', name: 'Lain-lain', icon: '📦' }
    ],
    features: {
      deliveryZones: true,
      timeSlots: false,
      specialInstructions: true,
      promoCode: true,
      sizeOptions: false,
      colorOptions: false,
      appointmentDate: false,
      staffSelection: false,
      shippingOptions: true,
      customMessage: false
    },
    labels: {
      instructionPlaceholder: 'Nota tambahan',
      deliveryFee: 'Kos Penghantaran',
      minOrder: 'Min. pembelian',
      addToCart: '+ Tambah',
      checkout: 'WhatsApp Order'
    },
    shippingOptions: [
      { id: 'cod', name: 'COD', price: 8, desc: 'Bayar bila terima' },
      { id: 'postage', name: 'Postage', price: 6, desc: '2-4 hari' },
      { id: 'pickup', name: 'Self Pickup', price: 0, desc: 'Ambil sendiri' }
    ]
  }
};

/**
 * Get business configuration by type
 */
export function getBusinessConfig(type: string): BusinessConfig {
  return businessConfig[type] || businessConfig.general;
}

/**
 * Get all business type options for selectors
 */
export function getBusinessTypeOptions() {
  return [
    { id: 'food', icon: '🍛', label: 'Restoran / Makanan' },
    { id: 'clothing', icon: '👗', label: 'Pakaian / Butik' },
    { id: 'salon', icon: '💇', label: 'Salon / Spa' },
    { id: 'services', icon: '🔧', label: 'Servis / Repair' },
    { id: 'bakery', icon: '🎂', label: 'Bakeri / Kek' },
    { id: 'general', icon: '🛒', label: 'Lain-lain' }
  ];
}

/**
 * Get primary color for business type
 */
export function getBusinessPrimaryColor(type: string): string {
  const config = getBusinessConfig(type);
  return config.primaryColor;
}
