/**
 * BinaApp Universal Order Widget
 *
 * Embed this widget on any website to enable ordering for all business types:
 * - Food: Delivery ordering
 * - Clothing: Product ordering with size/color
 * - Salon: Appointment booking with staff selection
 * - Services: Service booking with location choice
 * - Bakery: Cake ordering with custom messages
 * - General: Product ordering
 *
 * Usage:
 * <script src="https://binaapp.my/widgets/delivery-widget.js"></script>
 * <script>
 *   BinaAppDelivery.init({
 *     websiteId: 'your-website-id',
 *     apiUrl: 'https://binaapp-backend.onrender.com/api/v1',
 *     businessType: 'food', // food, clothing, salon, services, bakery, general
 *     primaryColor: '#ea580c',
 *     language: 'ms'  // 'ms' or 'en'
 *   });
 * </script>
 */

(function() {
    'use strict';

    // Business type configurations
    const BUSINESS_CONFIGS = {
        food: {
            icon: '🛵',
            buttonLabel: 'Pesan Delivery',
            buttonLabelEn: 'Order Delivery',
            pageTitle: 'Pesan Delivery',
            pageTitleEn: 'Order Delivery',
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
                sizeOptions: false,
                colorOptions: false,
                appointmentDate: false,
                staffSelection: false,
                shippingOptions: false,
                customMessage: false
            }
        },
        clothing: {
            icon: '🛍️',
            buttonLabel: 'Beli Sekarang',
            buttonLabelEn: 'Buy Now',
            pageTitle: 'Beli Sekarang',
            pageTitleEn: 'Buy Now',
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
                sizeOptions: true,
                colorOptions: true,
                appointmentDate: false,
                staffSelection: false,
                shippingOptions: true,
                customMessage: false
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
            buttonLabelEn: 'Book Now',
            pageTitle: 'Tempah Temujanji',
            pageTitleEn: 'Book Appointment',
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
                sizeOptions: false,
                colorOptions: false,
                appointmentDate: true,
                staffSelection: true,
                shippingOptions: false,
                customMessage: false
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
            buttonLabelEn: 'Book Service',
            pageTitle: 'Tempah Servis',
            pageTitleEn: 'Book Service',
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
                sizeOptions: false,
                colorOptions: false,
                appointmentDate: true,
                staffSelection: false,
                shippingOptions: false,
                customMessage: false,
                locationChoice: true
            },
            locationOptions: [
                { id: 'home', name: 'Ke Rumah/Lokasi Saya', icon: '🏠', extraFee: 20 },
                { id: 'shop', name: 'Di Kedai/Workshop', icon: '🏪', extraFee: 0 }
            ]
        },
        bakery: {
            icon: '🎂',
            buttonLabel: 'Tempah Kek',
            buttonLabelEn: 'Order Cake',
            pageTitle: 'Tempah Kek',
            pageTitleEn: 'Order Cake',
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
                sizeOptions: true,
                colorOptions: false,
                appointmentDate: true,
                staffSelection: false,
                shippingOptions: false,
                customMessage: true
            },
            sizes: ['0.5kg', '1kg', '1.5kg', '2kg', '3kg'],
            customMessagePlaceholder: 'Tulis mesej atas kek (cth: Happy Birthday Ali!)'
        },
        general: {
            icon: '🛒',
            buttonLabel: 'Beli Sekarang',
            buttonLabelEn: 'Buy Now',
            pageTitle: 'Beli Sekarang',
            pageTitleEn: 'Buy Now',
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
                sizeOptions: false,
                colorOptions: false,
                appointmentDate: false,
                staffSelection: false,
                shippingOptions: true,
                customMessage: false
            },
            shippingOptions: [
                { id: 'cod', name: 'COD', price: 8, desc: 'Bayar bila terima' },
                { id: 'postage', name: 'Postage', price: 6, desc: '2-4 hari' },
                { id: 'pickup', name: 'Self Pickup', price: 0, desc: 'Ambil sendiri' }
            ]
        }
    };

    // Widget namespace
    window.BinaAppDelivery = {
        config: {
            websiteId: null,
            apiUrl: 'https://binaapp-backend.onrender.com/api/v1',
            businessType: 'food',
            primaryColor: '#ea580c',
            language: 'ms',
            whatsappNumber: null,
            businessName: 'Kedai'
        },

        businessConfig: null,

        // Payment & Fulfillment settings (loaded from API or passed in config)
        paymentConfig: {
            cod: true,
            qr: false,
            qrImage: null
        },

        fulfillmentConfig: {
            delivery: true,
            deliveryFee: 5,
            minOrder: 20,
            deliveryArea: '',
            pickup: false,
            pickupAddress: ''
        },

        state: {
            zones: [],
            menu: { categories: [], items: [] },
            cart: [],
            selectedZone: null,
            selectedSize: null,
            selectedColor: null,
            selectedDate: null,
            selectedTime: null,
            selectedStaff: null,
            selectedShipping: null,
            selectedLocation: null,
            cakeMessage: '',
            currentView: 'menu', // menu | cart | checkout | tracking
            orderNumber: null,
            trackingLoading: false,
            trackingError: null,
            trackingData: null,
            // New payment & fulfillment selections
            selectedFulfillment: null, // 'delivery' | 'pickup'
            selectedPayment: null, // 'cod' | 'qr'
            // Leaflet Map (FREE - No API key needed!) - Phase 3
            riderMap: null,
            riderMarker: null,
            customerMarker: null,
            routeLine: null,
            mapDistance: null,
            mapETA: null,
            trackingInterval: null,
            deliveryAddress: '',
            conversationId: null
        },

        // Initialize widget
        init: function(options) {
            this.config = { ...this.config, ...options };

            if (!this.config.websiteId) {
                console.error('[BinaApp] websiteId is required');
                return;
            }

            // Get business config
            this.businessConfig = BUSINESS_CONFIGS[this.config.businessType] || BUSINESS_CONFIGS.general;

            // Override primary color if specified
            if (!options.primaryColor) {
                this.config.primaryColor = this.businessConfig.primaryColor;
            }

            // Apply payment config if provided
            if (options.payment) {
                this.paymentConfig = {
                    cod: options.payment.cod !== false,
                    qr: options.payment.qr === true,
                    qrImage: options.payment.qr_image || options.payment.qrImage || null
                };
            }

            // Apply fulfillment config if provided
            if (options.fulfillment) {
                this.fulfillmentConfig = {
                    delivery: options.fulfillment.delivery !== false,
                    deliveryFee: parseFloat(options.fulfillment.delivery_fee || options.fulfillment.deliveryFee) || 5,
                    minOrder: parseFloat(options.fulfillment.min_order || options.fulfillment.minOrder) || 20,
                    deliveryArea: options.fulfillment.delivery_area || options.fulfillment.deliveryArea || '',
                    pickup: options.fulfillment.pickup === true,
                    pickupAddress: options.fulfillment.pickup_address || options.fulfillment.pickupAddress || ''
                };
            }

            // Store WhatsApp number and business name
            if (options.whatsappNumber) {
                this.config.whatsappNumber = options.whatsappNumber.replace(/[^0-9]/g, '');
            }
            if (options.businessName) {
                this.config.businessName = options.businessName;
            }

            this.injectStyles();
            this.createWidget();
            this.loadData();
            this.initEventListeners();

            console.log('[BinaApp] Universal order widget initialized for:', this.config.businessType);
            console.log('[BinaApp] Payment config:', this.paymentConfig);
            console.log('[BinaApp] Fulfillment config:', this.fulfillmentConfig);
        },

        // Get business config helper
        getConfig: function() {
            return this.businessConfig || BUSINESS_CONFIGS.general;
        },

        // Inject widget styles
        injectStyles: function() {
            const primaryColor = this.config.primaryColor;
            const styles = `
                /* BinaApp Universal Order Widget Styles */
                #binaapp-widget {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 99999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                #binaapp-order-btn {
                    background: linear-gradient(135deg, ${primaryColor} 0%, ${this.adjustColor(primaryColor, -20)} 100%);
                    color: white;
                    border: none;
                    border-radius: 50px;
                    padding: 16px 24px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    transition: transform 0.2s;
                }

                #binaapp-order-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 24px rgba(0,0,0,0.3);
                }

                .binaapp-cart-badge {
                    background: #fbbf24;
                    color: #78350f;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: bold;
                }

                #binaapp-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.5);
                    z-index: 100000;
                    display: none;
                    justify-content: center;
                    align-items: center;
                    overflow-y: auto;
                }

                #binaapp-modal.active {
                    display: flex;
                }

                .binaapp-modal-content {
                    background: white;
                    border-radius: 16px;
                    max-width: 900px;
                    width: 90%;
                    max-height: 90vh;
                    overflow-y: auto;
                    margin: 20px;
                }

                .binaapp-modal-header {
                    background: linear-gradient(135deg, ${primaryColor} 0%, ${this.adjustColor(primaryColor, -20)} 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 16px 16px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .binaapp-modal-close {
                    background: rgba(255,255,255,0.2);
                    border: none;
                    color: white;
                    font-size: 24px;
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    cursor: pointer;
                }

                .binaapp-modal-body {
                    padding: 20px;
                }

                .binaapp-categories {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                    margin-bottom: 16px;
                }

                .binaapp-category-btn {
                    padding: 8px 16px;
                    border-radius: 20px;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                    background: #f3f4f6;
                    color: #374151;
                    transition: all 0.2s;
                }

                .binaapp-category-btn.active {
                    background: ${primaryColor};
                    color: white;
                }

                .binaapp-menu-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 16px;
                    margin-top: 20px;
                }

                .binaapp-menu-item {
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    overflow: hidden;
                    transition: transform 0.2s, box-shadow 0.2s;
                    cursor: pointer;
                }

                .binaapp-menu-item:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
                }

                .binaapp-menu-item img {
                    width: 100%;
                    height: 180px;
                    object-fit: cover;
                }

                .binaapp-menu-item-content {
                    padding: 12px;
                }

                .binaapp-menu-item-name {
                    font-weight: 600;
                    font-size: 16px;
                    margin-bottom: 4px;
                }

                .binaapp-menu-item-desc {
                    font-size: 14px;
                    color: #6b7280;
                    margin-bottom: 8px;
                }

                .binaapp-menu-item-price {
                    font-size: 18px;
                    font-weight: 700;
                    color: ${primaryColor};
                }

                .binaapp-add-to-cart-btn {
                    background: ${primaryColor};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    width: 100%;
                    margin-top: 8px;
                    cursor: pointer;
                    font-weight: 600;
                }

                .binaapp-option-group {
                    margin: 12px 0;
                    padding: 12px;
                    background: #f9fafb;
                    border-radius: 8px;
                }

                .binaapp-option-label {
                    font-weight: 600;
                    margin-bottom: 8px;
                    display: block;
                }

                .binaapp-option-buttons {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                }

                .binaapp-option-btn {
                    padding: 8px 16px;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    background: white;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .binaapp-option-btn.selected {
                    border-color: ${primaryColor};
                    background: ${primaryColor}10;
                }

                .binaapp-color-btn {
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    border: 2px solid #e5e7eb;
                    cursor: pointer;
                }

                .binaapp-color-btn.selected {
                    border-color: ${primaryColor};
                    box-shadow: 0 0 0 2px white, 0 0 0 4px ${primaryColor};
                }

                .binaapp-cart-empty {
                    text-align: center;
                    padding: 40px;
                    color: #6b7280;
                }

                .binaapp-cart-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    border-bottom: 1px solid #e5e7eb;
                }

                .binaapp-qty-controls {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }

                .binaapp-qty-btn {
                    background: #f3f4f6;
                    border: none;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    cursor: pointer;
                    font-weight: bold;
                }

                .binaapp-checkout-btn {
                    background: linear-gradient(to right, #10b981, #059669);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 16px;
                    width: 100%;
                    font-size: 16px;
                    font-weight: 700;
                    cursor: pointer;
                    margin-top: 16px;
                }

                .binaapp-form-group {
                    margin-bottom: 16px;
                }

                .binaapp-form-label {
                    display: block;
                    font-weight: 600;
                    margin-bottom: 4px;
                }

                .binaapp-form-input,
                .binaapp-form-select,
                .binaapp-form-textarea {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    font-size: 14px;
                    box-sizing: border-box;
                }

                .binaapp-shipping-option {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 12px;
                    border: 2px solid #e5e7eb;
                    border-radius: 12px;
                    cursor: pointer;
                    margin-bottom: 8px;
                }

                .binaapp-shipping-option.selected {
                    border-color: ${primaryColor};
                    background: ${primaryColor}10;
                }

                .binaapp-staff-btn {
                    padding: 12px;
                    border: 2px solid #e5e7eb;
                    border-radius: 12px;
                    background: white;
                    cursor: pointer;
                    text-align: center;
                    transition: all 0.2s;
                }

                .binaapp-staff-btn.selected {
                    border-color: ${primaryColor};
                    background: ${primaryColor}10;
                }

                .binaapp-tracking-status {
                    text-align: center;
                    padding: 20px;
                }

                .binaapp-status-badge {
                    display: inline-block;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    margin: 10px 0;
                }

                .binaapp-loading {
                    text-align: center;
                    padding: 40px;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .binaapp-spinner {
                    border: 3px solid #f3f4f6;
                    border-top-color: ${primaryColor};
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto;
                }
            `;

            const styleSheet = document.createElement('style');
            styleSheet.textContent = styles;
            document.head.appendChild(styleSheet);
        },

        // Adjust color brightness
        adjustColor: function(color, amount) {
            const hex = color.replace('#', '');
            const num = parseInt(hex, 16);
            const r = Math.min(255, Math.max(0, (num >> 16) + amount));
            const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amount));
            const b = Math.min(255, Math.max(0, (num & 0x0000FF) + amount));
            return '#' + (b | (g << 8) | (r << 16)).toString(16).padStart(6, '0');
        },

        // Create widget DOM
        createWidget: function() {
            const config = this.getConfig();
            const lang = this.config.language;

            // Create floating button
            const widgetContainer = document.createElement('div');
            widgetContainer.id = 'binaapp-widget';
            widgetContainer.innerHTML = `
                <button id="binaapp-order-btn">
                    <span>${config.icon}</span>
                    <span>${lang === 'en' ? config.buttonLabelEn : config.buttonLabel}</span>
                    <span class="binaapp-cart-badge" id="binaapp-cart-count" style="display:none;">0</span>
                </button>
            `;

            // Create modal
            const modal = document.createElement('div');
            modal.id = 'binaapp-modal';
            modal.innerHTML = `
                <div class="binaapp-modal-content">
                    <div class="binaapp-modal-header">
                        <h2 id="binaapp-modal-title">${config.emoji} ${lang === 'en' ? config.pageTitleEn : config.pageTitle}</h2>
                        <button class="binaapp-modal-close" id="binaapp-modal-close">&times;</button>
                    </div>
                    <div class="binaapp-modal-body" id="binaapp-modal-body">
                        <div class="binaapp-loading">
                            <div class="binaapp-spinner"></div>
                            <p>${this.t('loading')}</p>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(widgetContainer);
            document.body.appendChild(modal);
        },

        // Event listeners
        initEventListeners: function() {
            const self = this;

            // Open modal
            document.getElementById('binaapp-order-btn').addEventListener('click', function() {
                self.openModal();
            });

            // Close modal
            document.getElementById('binaapp-modal-close').addEventListener('click', function() {
                self.closeModal();
            });

            // Close on backdrop click
            document.getElementById('binaapp-modal').addEventListener('click', function(e) {
                if (e.target.id === 'binaapp-modal') {
                    self.closeModal();
                }
            });
        },

        // Load data from API
        loadData: async function() {
            try {
                // Load zones (if applicable)
                const config = this.getConfig();
                if (config.features.deliveryZones) {
                    const zonesRes = await fetch(`${this.config.apiUrl}/delivery/zones/${this.config.websiteId}`);
                    const zonesData = await zonesRes.json();
                    this.state.zones = zonesData.zones || [];
                }

                // Load menu
                const menuRes = await fetch(`${this.config.apiUrl}/delivery/menu/${this.config.websiteId}`);
                const menuData = await menuRes.json();
                this.state.menu = menuData;

                // Load website config for payment/fulfillment settings if not already set
                try {
                    const configRes = await fetch(`${this.config.apiUrl}/delivery/config/${this.config.websiteId}`);
                    if (configRes.ok) {
                        const websiteConfig = await configRes.json();

                        // Apply business type from API if not already set
                        if (websiteConfig.business_type && !this.config.businessType) {
                            this.config.businessType = websiteConfig.business_type;
                            this.businessConfig = BUSINESS_CONFIGS[websiteConfig.business_type] || BUSINESS_CONFIGS.general;
                        }

                        // Apply custom categories from API if provided
                        if (websiteConfig.categories && websiteConfig.categories.length > 0) {
                            // Merge API categories with the 'all' category
                            this.businessConfig.categories = [
                                { id: 'all', name: 'Semua', icon: '📋' },
                                ...websiteConfig.categories
                            ];
                            console.log('[BinaApp] Using API categories:', this.businessConfig.categories);
                        }

                        // Apply payment config from API if not overridden
                        if (websiteConfig.payment) {
                            this.paymentConfig = {
                                cod: websiteConfig.payment.cod !== false,
                                qr: websiteConfig.payment.qr === true,
                                qrImage: websiteConfig.payment.qr_image || this.paymentConfig.qrImage
                            };
                        }

                        // Apply fulfillment config from API if not overridden
                        if (websiteConfig.fulfillment) {
                            this.fulfillmentConfig = {
                                delivery: websiteConfig.fulfillment.delivery !== false,
                                deliveryFee: parseFloat(websiteConfig.fulfillment.delivery_fee) || this.fulfillmentConfig.deliveryFee,
                                minOrder: parseFloat(websiteConfig.fulfillment.min_order) || this.fulfillmentConfig.minOrder,
                                deliveryArea: websiteConfig.fulfillment.delivery_area || this.fulfillmentConfig.deliveryArea,
                                pickup: websiteConfig.fulfillment.pickup === true,
                                pickupAddress: websiteConfig.fulfillment.pickup_address || this.fulfillmentConfig.pickupAddress
                            };
                        }

                        // Get WhatsApp number and business name
                        if (websiteConfig.whatsapp_number) {
                            this.config.whatsappNumber = websiteConfig.whatsapp_number.replace(/[^0-9]/g, '');
                        }
                        if (websiteConfig.business_name) {
                            this.config.businessName = websiteConfig.business_name;
                        }

                        // Apply primary color from API
                        if (websiteConfig.primary_color) {
                            this.config.primaryColor = websiteConfig.primary_color;
                        }
                    }
                } catch (configError) {
                    console.log('[BinaApp] No additional config loaded, using defaults');
                }

                console.log('[BinaApp] Data loaded:', this.state);
                console.log('[BinaApp] Payment config:', this.paymentConfig);
                console.log('[BinaApp] Fulfillment config:', this.fulfillmentConfig);
            } catch (error) {
                console.error('[BinaApp] Error loading data:', error);
            }
        },

        // Open modal
        openModal: function() {
            document.getElementById('binaapp-modal').classList.add('active');
            this.showView('menu');
        },

        // Close modal
        closeModal: function() {
            document.getElementById('binaapp-modal').classList.remove('active');
            // Stop tracking polling when modal is closed (Phase 2)
            this.stopTrackingPolling();
        },

        // Show different views
        showView: function(view) {
            this.state.currentView = view;

            const body = document.getElementById('binaapp-modal-body');
            const title = document.getElementById('binaapp-modal-title');
            const config = this.getConfig();
            const lang = this.config.language;

            switch(view) {
                case 'menu':
                    title.textContent = `${config.emoji} ${lang === 'en' ? config.pageTitleEn : config.pageTitle}`;
                    body.innerHTML = this.renderMenu();
                    break;
                case 'cart':
                    title.textContent = `${config.cartIcon} ${config.cartLabel}`;
                    body.innerHTML = this.renderCart();
                    break;
                case 'checkout':
                    title.textContent = this.t('checkout');
                    body.innerHTML = this.renderCheckout();
                    break;
                case 'tracking':
                    title.textContent = this.t('trackOrder');
                    body.innerHTML = this.renderTracking();
                    this.loadTracking();
                    break;
            }

            this.attachViewEventListeners(view);
        },

        // Load order tracking data (Phase 1: no live GPS maps)
        loadTracking: async function() {
            try {
                if (!this.state.orderNumber) return;

                this.state.trackingLoading = true;
                this.state.trackingError = null;
                this.state.trackingData = null;

                const body = document.getElementById('binaapp-modal-body');
                if (body && this.state.currentView === 'tracking') {
                    body.innerHTML = this.renderTracking();
                }

                const res = await fetch(`${this.config.apiUrl}/delivery/orders/${this.state.orderNumber}/track`);
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(text || 'Failed to load tracking');
                }
                const data = await res.json();

                this.state.trackingData = data;
                this.state.trackingLoading = false;

                if (body && this.state.currentView === 'tracking') {
                    body.innerHTML = this.renderTracking();

                    // Initialize map if rider has GPS (Phase 2)
                    setTimeout(() => {
                        this.initializeMap();
                    }, 200);

                    // Start polling if not already started
                    if (!this.state.trackingInterval) {
                        this.startTrackingPolling();
                    }
                } else {
                    // Update marker if map already initialized
                    this.updateRiderMarker();
                }
            } catch (err) {
                console.error('[BinaApp] Tracking load error:', err);
                this.state.trackingLoading = false;
                this.state.trackingError = this.t('trackingLoadFailed');
                const body = document.getElementById('binaapp-modal-body');
                if (body && this.state.currentView === 'tracking') {
                    body.innerHTML = this.renderTracking();
                }
            }
        },

        // Load Leaflet (FREE - No API key required!)
        loadLeaflet: function() {
            return new Promise((resolve, reject) => {
                // Check if already loaded
                if (window.L) {
                    this.state.mapsLoaded = true;
                    resolve();
                    return;
                }

                // Check if script is already being loaded
                if (this.state.mapsLoading) {
                    // Wait for existing load
                    const checkInterval = setInterval(() => {
                        if (this.state.mapsLoaded) {
                            clearInterval(checkInterval);
                            resolve();
                        }
                    }, 100);
                    return;
                }

                this.state.mapsLoading = true;

                // Add Leaflet CSS
                if (!document.querySelector('link[href*="leaflet"]')) {
                    const css = document.createElement('link');
                    css.rel = 'stylesheet';
                    css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
                    css.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
                    css.crossOrigin = '';
                    document.head.appendChild(css);
                }

                // Load Leaflet JS (FREE - No API key needed!)
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
                script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
                script.crossOrigin = '';
                script.async = true;
                script.onload = () => {
                    this.state.mapsLoaded = true;
                    this.state.mapsLoading = false;
                    console.log('[BinaApp] Leaflet loaded successfully (FREE!)');
                    resolve();
                };
                script.onerror = () => {
                    this.state.mapsLoading = false;
                    console.error('[BinaApp] Failed to load Leaflet');
                    reject(new Error('Failed to load Leaflet'));
                };
                document.head.appendChild(script);
            });
        },

        // Initialize Map with Leaflet + OpenStreetMap (FREE!) - Updated for Phase 3
        initializeMap: async function() {
            try {
                if (!this.state.trackingData) return;

                const rider = this.state.trackingData.rider;
                const order = this.state.trackingData.order;

                // Check if rider has GPS coordinates
                if (!rider || !rider.current_latitude || !rider.current_longitude) {
                    console.log('[BinaApp] Rider GPS not available yet');
                    return;
                }

                // Get rider and customer coordinates
                const riderLat = parseFloat(rider.current_latitude);
                const riderLng = parseFloat(rider.current_longitude);

                // Use customer delivery coordinates if available, otherwise default to KL
                const customerLat = order.delivery_latitude ? parseFloat(order.delivery_latitude) : 3.1390;
                const customerLng = order.delivery_longitude ? parseFloat(order.delivery_longitude) : 101.6869;

                // Call the new Leaflet.js initialization function
                await this.initRiderTrackingMap(
                    riderLat,
                    riderLng,
                    customerLat,
                    customerLng,
                    rider.name || 'Rider'
                );

                console.log('[BinaApp] Map initialized successfully via initRiderTrackingMap');
            } catch (error) {
                console.error('[BinaApp] Map initialization error:', error);
            }
        },

        // Update rider marker position (Leaflet) - Updated for Phase 3
        updateRiderMarker: function() {
            if (!this.state.trackingData || !this.state.riderMarker) return;

            const rider = this.state.trackingData.rider;
            if (!rider || !rider.current_latitude || !rider.current_longitude) return;

            const newLat = parseFloat(rider.current_latitude);
            const newLng = parseFloat(rider.current_longitude);

            // Call our new updateRiderPosition function
            this.updateRiderPosition(newLat, newLng);

            // Pan map to keep rider visible (use correct state variable)
            if (this.state.riderMap) {
                this.state.riderMap.panTo([newLat, newLng]);
            }
        },

        // Calculate distance between two coordinates (in km)
        calculateDistance: function(lat1, lng1, lat2, lng2) {
            const R = 6371; // Earth's radius in km
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLng = (lng2 - lng1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                     Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                     Math.sin(dLng/2) * Math.sin(dLng/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        },

        // Start automatic tracking polling (Phase 2)
        startTrackingPolling: function() {
            // Stop any existing interval
            this.stopTrackingPolling();

            // Poll every 15 seconds
            this.state.trackingInterval = setInterval(() => {
                if (this.state.currentView === 'tracking' && this.state.orderNumber) {
                    this.loadTracking();
                }
            }, 15000);

            console.log('[BinaApp] Started tracking polling');
        },

        // Stop tracking polling
        stopTrackingPolling: function() {
            if (this.state.trackingInterval) {
                clearInterval(this.state.trackingInterval);
                this.state.trackingInterval = null;
                console.log('[BinaApp] Stopped tracking polling');
            }
        },

        // Render category buttons
        renderCategories: function() {
            const config = this.getConfig();
            let html = '<div class="binaapp-categories">';

            config.categories.forEach((cat, idx) => {
                html += `
                    <button class="binaapp-category-btn ${idx === 0 ? 'active' : ''}"
                            onclick="BinaAppDelivery.filterCategory('${cat.id}')">
                        ${cat.icon} ${cat.name}
                    </button>
                `;
            });

            html += '</div>';
            return html;
        },

        // Filter by category
        filterCategory: function(catId) {
            const buttons = document.querySelectorAll('.binaapp-category-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            const items = document.querySelectorAll('.binaapp-menu-item');
            items.forEach(item => {
                if (catId === 'all' || item.dataset.category === catId) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        },

        // Render menu view
        renderMenu: function() {
            const items = this.state.menu.items;
            const config = this.getConfig();

            if (!items || items.length === 0) {
                return `<div class="binaapp-cart-empty">${this.t('noMenuAvailable')}</div>`;
            }

            let html = this.renderCategories();
            html += '<div class="binaapp-menu-grid">';

            items.forEach(item => {
                html += `
                    <div class="binaapp-menu-item" data-item-id="${item.id}" data-category="${item.category || 'all'}">
                        <img src="${item.image_url || 'https://via.placeholder.com/300x180?text=No+Image'}" alt="${item.name}">
                        <div class="binaapp-menu-item-content">
                            <div class="binaapp-menu-item-name">${item.name}</div>
                            <div class="binaapp-menu-item-desc">${item.description || ''}</div>
                            <div class="binaapp-menu-item-price">RM ${parseFloat(item.price).toFixed(2)}</div>
                            ${this.renderItemOptions(item)}
                            <button class="binaapp-add-to-cart-btn" onclick="BinaAppDelivery.addToCart('${item.id}')">
                                ${config.features.appointmentDate ? '+ Pilih' : this.t('addToCart')}
                            </button>
                        </div>
                    </div>
                `;
            });

            html += '</div>';

            // Add cart button if items in cart
            if (this.state.cart.length > 0) {
                html += `
                    <button class="binaapp-checkout-btn" onclick="BinaAppDelivery.showView('cart')">
                        ${this.t('viewCart')} (${this.state.cart.length} ${this.t('items')})
                    </button>
                `;
            }

            return html;
        },

        // Render item-specific options
        renderItemOptions: function(item) {
            const config = this.getConfig();
            let html = '';

            // Size options
            if (config.features.sizeOptions && config.sizes) {
                html += `
                    <div class="binaapp-option-group">
                        <span class="binaapp-option-label">📏 ${this.t('selectSize')}</span>
                        <div class="binaapp-option-buttons">
                            ${config.sizes.map(size => `
                                <button class="binaapp-option-btn" onclick="BinaAppDelivery.selectSize('${size}', this)" data-item="${item.id}">
                                    ${size}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            // Color options
            if (config.features.colorOptions) {
                const colors = ['#000000', '#FFFFFF', '#FF0000', '#0000FF', '#00FF00', '#FFC0CB', '#FFD700', '#800080'];
                html += `
                    <div class="binaapp-option-group">
                        <span class="binaapp-option-label">🎨 ${this.t('selectColor')}</span>
                        <div class="binaapp-option-buttons">
                            ${colors.map(color => `
                                <button class="binaapp-color-btn" style="background:${color}"
                                        onclick="BinaAppDelivery.selectColor('${color}', this)" data-item="${item.id}">
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            return html;
        },

        // Select size
        selectSize: function(size, btn) {
            const parent = btn.closest('.binaapp-option-group');
            parent.querySelectorAll('.binaapp-option-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            this.state.selectedSize = size;
        },

        // Select color
        selectColor: function(color, btn) {
            const parent = btn.closest('.binaapp-option-group');
            parent.querySelectorAll('.binaapp-color-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            this.state.selectedColor = color;
        },

        // Render cart view
        renderCart: function() {
            const config = this.getConfig();

            if (this.state.cart.length === 0) {
                return `
                    <div class="binaapp-cart-empty">
                        <p>${this.t('cartEmpty')}</p>
                        <button class="binaapp-checkout-btn" onclick="BinaAppDelivery.showView('menu')">
                            ${this.t('startOrdering')}
                        </button>
                    </div>
                `;
            }

            let html = '<div>';
            let subtotal = 0;

            this.state.cart.forEach((cartItem, index) => {
                const total = cartItem.price * cartItem.quantity;
                subtotal += total;

                let itemDetails = '';
                if (cartItem.size) itemDetails += ` (${cartItem.size})`;
                if (cartItem.color) itemDetails += ` - ${cartItem.color}`;

                html += `
                    <div class="binaapp-cart-item">
                        <div>
                            <strong>${cartItem.name}${itemDetails}</strong><br>
                            <span style="color: #6b7280;">RM ${cartItem.price.toFixed(2)} x ${cartItem.quantity}</span>
                        </div>
                        <div class="binaapp-qty-controls">
                            <button class="binaapp-qty-btn" onclick="BinaAppDelivery.updateQuantity(${index}, ${cartItem.quantity - 1})">−</button>
                            <span>${cartItem.quantity}</span>
                            <button class="binaapp-qty-btn" onclick="BinaAppDelivery.updateQuantity(${index}, ${cartItem.quantity + 1})">+</button>
                            <span style="margin-left: 10px; font-weight: 600;">RM ${total.toFixed(2)}</span>
                        </div>
                    </div>
                `;
            });

            html += `
                <div style="padding: 20px; background: #f9fafb; margin-top: 16px; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; font-size: 18px; font-weight: 700;">
                        <span>${this.t('subtotal')}</span>
                        <span style="color: ${this.config.primaryColor};">RM ${subtotal.toFixed(2)}</span>
                    </div>
                </div>
                <button class="binaapp-checkout-btn" onclick="BinaAppDelivery.showView('checkout')">
                    ${this.t('proceedToCheckout')}
                </button>
            </div>`;

            return html;
        },

        // Render checkout form
        renderCheckout: function() {
            const config = this.getConfig();
            const features = config.features;
            const payment = this.paymentConfig;
            const fulfillment = this.fulfillmentConfig;
            const subtotal = this.state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

            let html = '<form id="binaapp-checkout-form">';

            // ============================================
            // STEP 1: FULFILLMENT SELECTION (Delivery/Pickup)
            // ============================================
            if (fulfillment.delivery || fulfillment.pickup) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">📦 ${this.t('selectFulfillment')}</label>
                        <div style="display:flex;flex-direction:column;gap:8px;">
                `;

                // Delivery option
                if (fulfillment.delivery) {
                    html += `
                        <div class="binaapp-shipping-option" id="fulfillment-delivery"
                             onclick="BinaAppDelivery.selectFulfillment('delivery')">
                            <input type="radio" name="fulfillment" value="delivery">
                            <span style="font-size:24px;">🛵</span>
                            <div style="flex:1;">
                                <p style="font-weight:600;margin:0;">Delivery</p>
                                <p style="font-size:12px;color:#6b7280;margin:0;">${fulfillment.deliveryArea || 'Hantar ke alamat anda'}</p>
                            </div>
                            <span style="font-weight:bold;color:#ea580c;">RM${fulfillment.deliveryFee.toFixed(2)}</span>
                        </div>
                    `;
                }

                // Pickup option
                if (fulfillment.pickup) {
                    html += `
                        <div class="binaapp-shipping-option" id="fulfillment-pickup"
                             onclick="BinaAppDelivery.selectFulfillment('pickup')">
                            <input type="radio" name="fulfillment" value="pickup">
                            <span style="font-size:24px;">🏪</span>
                            <div style="flex:1;">
                                <p style="font-weight:600;margin:0;">Self Pickup</p>
                                <p style="font-size:12px;color:#6b7280;margin:0;">${fulfillment.pickupAddress || 'Ambil di kedai'}</p>
                            </div>
                            <span style="font-weight:bold;color:#10b981;">FREE</span>
                        </div>
                    `;
                }

                html += `
                        </div>
                    </div>
                `;

                // Delivery address input (shown when delivery selected)
                html += `
                    <div class="binaapp-form-group" id="delivery-address-section" style="display:none;">
                        <label class="binaapp-form-label">📍 ${this.t('deliveryAddress')}</label>
                        <textarea class="binaapp-form-textarea" id="delivery-address" name="delivery_address" 
                                  placeholder="Masukkan alamat penuh..." rows="3"></textarea>
                    </div>
                `;

                // Delivery zone selection (shown when delivery selected and zones exist)
                html += `
                    <div class="binaapp-form-group" id="delivery-zone-section" style="display:none;">
                        <label class="binaapp-form-label">🗺️ ${this.t('deliveryZone')}</label>
                        <select class="binaapp-form-select" id="delivery-zone-select" name="delivery_zone_id"
                                onchange="BinaAppDelivery.selectZone(this.value)">
                            <option value="">-- ${this.t('selectZone')} --</option>
                            ${(this.state.zones || []).map(z => `
                                <option value="${z.id}">
                                    ${z.zone_name} • RM${parseFloat(z.delivery_fee || 0).toFixed(2)} • Min RM${parseFloat(z.minimum_order || 0).toFixed(2)}
                                </option>
                            `).join('')}
                        </select>
                        <p style="font-size:12px;color:#6b7280;margin-top:6px;">${this.t('zoneAffectsFees')}</p>
                    </div>
                `;
            }

            // ============================================
            // STEP 2: PAYMENT METHOD SELECTION
            // ============================================
            if (payment.cod || payment.qr) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">💳 ${this.t('selectPayment')}</label>
                        <div style="display:flex;flex-direction:column;gap:8px;">
                `;

                // COD option
                if (payment.cod) {
                    html += `
                        <div class="binaapp-shipping-option" id="payment-cod"
                             onclick="BinaAppDelivery.selectPayment('cod')">
                            <input type="radio" name="payment" value="cod">
                            <span style="font-size:24px;">💵</span>
                            <div>
                                <p style="font-weight:600;margin:0;">Bayar Tunai (COD)</p>
                                <p style="font-size:12px;color:#6b7280;margin:0;">Bayar bila terima pesanan</p>
                            </div>
                        </div>
                    `;
                }

                // QR Payment option
                if (payment.qr) {
                    html += `
                        <div class="binaapp-shipping-option" id="payment-qr"
                             onclick="BinaAppDelivery.selectPayment('qr')">
                            <input type="radio" name="payment" value="qr">
                            <span style="font-size:24px;">📱</span>
                            <div>
                                <p style="font-weight:600;margin:0;">QR Payment</p>
                                <p style="font-size:12px;color:#6b7280;margin:0;">Scan & bayar sekarang</p>
                            </div>
                        </div>
                    `;
                }

                html += `
                        </div>
                    </div>
                `;

                // QR Code Display Section (shown when QR selected)
                if (payment.qr && payment.qrImage) {
                    html += `
                        <div id="qr-payment-section" style="display:none;margin:16px 0;text-align:center;padding:20px;background:#f9fafb;border-radius:16px;">
                            <p style="font-weight:600;margin-bottom:12px;">📱 Scan QR untuk bayar</p>
                            <img src="${payment.qrImage}" alt="Payment QR" 
                                 style="width:200px;height:200px;border:4px solid white;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);margin:0 auto;display:block;">
                            <p style="font-size:14px;color:#6b7280;margin-top:12px;">
                                Jumlah: <strong style="color:#ea580c;font-size:18px;">RM<span id="qr-amount">${subtotal.toFixed(2)}</span></strong>
                            </p>
                            <p style="font-size:12px;color:#9ca3af;margin-top:8px;">
                                Screenshot bukti pembayaran & hantar via WhatsApp
                            </p>
                        </div>
                    `;
                }
            }

            // ============================================
            // LEGACY: Appointment date (salon, services, bakery)
            // ============================================
            if (features.appointmentDate) {
                const today = new Date().toISOString().split('T')[0];
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">📅 ${this.t('selectDate')}</label>
                        <input type="date" class="binaapp-form-input" name="appointment_date" min="${today}" required>
                    </div>
                `;
            }

            // Time slots
            if (features.timeSlots) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">⏰ ${this.t('selectTime')}</label>
                        <select class="binaapp-form-select" name="time_slot">
                            <option value="">-- ${this.t('selectTime')} --</option>
                            <option value="9:00 AM">9:00 AM</option>
                            <option value="10:00 AM">10:00 AM</option>
                            <option value="11:00 AM">11:00 AM</option>
                            <option value="12:00 PM">12:00 PM</option>
                            <option value="2:00 PM">2:00 PM</option>
                            <option value="3:00 PM">3:00 PM</option>
                            <option value="4:00 PM">4:00 PM</option>
                            <option value="5:00 PM">5:00 PM</option>
                        </select>
                    </div>
                `;
            }

            // Staff selection (salon)
            if (features.staffSelection && config.defaultStaff) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">💇 ${this.t('selectStaff')}</label>
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
                            ${config.defaultStaff.map(s => `
                                <button type="button" class="binaapp-staff-btn" onclick="BinaAppDelivery.selectStaff('${s.name}', this)">
                                    <span style="font-size:24px;display:block;">${s.icon}</span>
                                    <span style="font-size:12px;">${s.name}</span>
                                </button>
                            `).join('')}
                        </div>
                        <input type="hidden" name="staff" id="binaapp-staff-input">
                    </div>
                `;
            }

            // Custom message (bakery)
            if (features.customMessage) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">✍️ ${this.t('cakeMessage')}</label>
                        <input type="text" class="binaapp-form-input" name="cake_message"
                               placeholder="${config.customMessagePlaceholder || 'Happy Birthday!'}" maxlength="50">
                        <p style="font-size:12px;color:#9ca3af;margin-top:4px;">Maksimum 50 huruf</p>
                    </div>
                `;
            }

            // ============================================
            // CUSTOMER INFO
            // ============================================
            html += `
                <div class="binaapp-form-group">
                    <label class="binaapp-form-label">${this.t('name')}</label>
                    <input type="text" class="binaapp-form-input" name="customer_name" required>
                </div>

                <div class="binaapp-form-group">
                    <label class="binaapp-form-label">${this.t('phone')}</label>
                    <input type="tel" class="binaapp-form-input" name="customer_phone" required>
                </div>

                <div class="binaapp-form-group">
                    <label class="binaapp-form-label">${this.t('notes')} (${this.t('optional')})</label>
                    <textarea class="binaapp-form-textarea" name="delivery_notes" rows="2" placeholder="Arahan khas..."></textarea>
                </div>
            `;

            // ============================================
            // ORDER SUMMARY
            // ============================================
            const deliveryFee = this.state.selectedFulfillment === 'delivery' ? this.fulfillmentConfig.deliveryFee : 0;
            const total = subtotal + deliveryFee;

            html += `
                <div style="padding:16px;background:#f9fafb;border-radius:12px;margin:16px 0;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span>Subtotal</span>
                        <span>RM${subtotal.toFixed(2)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;" id="delivery-fee-row">
                        <span>Delivery</span>
                        <span id="checkout-delivery-fee">RM${deliveryFee.toFixed(2)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:18px;font-weight:700;padding-top:8px;border-top:1px solid #e5e7eb;">
                        <span>JUMLAH</span>
                        <span style="color:${this.config.primaryColor};" id="checkout-total">RM${total.toFixed(2)}</span>
                    </div>
                </div>

                <button type="submit" class="binaapp-checkout-btn">
                    📱 WhatsApp Pesanan
                </button>
            </form>`;

            return html;
        },

        // Select staff
        selectStaff: function(name, btn) {
            document.querySelectorAll('.binaapp-staff-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            document.getElementById('binaapp-staff-input').value = name;
            this.state.selectedStaff = name;
        },

        // Select shipping
        selectShipping: function(id, price, el) {
            document.querySelectorAll('.binaapp-shipping-option').forEach(opt => opt.classList.remove('selected'));
            el.classList.add('selected');
            el.querySelector('input').checked = true;
            this.state.selectedShipping = { id, price };
        },

        // Select location
        selectLocation: function(id, extraFee, el) {
            document.querySelectorAll('.binaapp-shipping-option').forEach(opt => opt.classList.remove('selected'));
            el.classList.add('selected');
            el.querySelector('input').checked = true;
            this.state.selectedLocation = { id, extraFee };
        },

        // Select fulfillment method (delivery or pickup)
        selectFulfillment: function(method) {
            this.state.selectedFulfillment = method;
            
            // Update UI - clear all selections first
            const deliveryEl = document.getElementById('fulfillment-delivery');
            const pickupEl = document.getElementById('fulfillment-pickup');
            
            if (deliveryEl) {
                deliveryEl.classList.remove('selected');
                const radio = deliveryEl.querySelector('input');
                if (radio) radio.checked = false;
            }
            if (pickupEl) {
                pickupEl.classList.remove('selected');
                const radio = pickupEl.querySelector('input');
                if (radio) radio.checked = false;
            }
            
            // Select the chosen method
            const selectedEl = document.getElementById('fulfillment-' + method);
            if (selectedEl) {
                selectedEl.classList.add('selected');
                const radio = selectedEl.querySelector('input');
                if (radio) radio.checked = true;
            }
            
            // Show/hide address input
            const addressSection = document.getElementById('delivery-address-section');
            if (addressSection) {
                addressSection.style.display = method === 'delivery' ? 'block' : 'none';
            }

            // Show/hide delivery zones (only if zones exist)
            const zoneSection = document.getElementById('delivery-zone-section');
            if (zoneSection) {
                const hasZones = (this.state.zones || []).length > 0;
                zoneSection.style.display = (method === 'delivery' && hasZones) ? 'block' : 'none';
            }
            
            // Update totals
            this.updateCheckoutTotals();
        },

        // Select payment method (cod or qr)
        selectPayment: function(method) {
            this.state.selectedPayment = method;
            
            // Update UI - clear all selections first
            const codEl = document.getElementById('payment-cod');
            const qrEl = document.getElementById('payment-qr');
            
            if (codEl) {
                codEl.classList.remove('selected');
                const radio = codEl.querySelector('input');
                if (radio) radio.checked = false;
            }
            if (qrEl) {
                qrEl.classList.remove('selected');
                const radio = qrEl.querySelector('input');
                if (radio) radio.checked = false;
            }
            
            // Select the chosen method
            const selectedEl = document.getElementById('payment-' + method);
            if (selectedEl) {
                selectedEl.classList.add('selected');
                const radio = selectedEl.querySelector('input');
                if (radio) radio.checked = true;
            }
            
            // Show/hide QR section
            const qrSection = document.getElementById('qr-payment-section');
            if (qrSection) {
                qrSection.style.display = method === 'qr' ? 'block' : 'none';
                
                // Update QR amount
                if (method === 'qr') {
                    const qrAmountEl = document.getElementById('qr-amount');
                    if (qrAmountEl) {
                        const subtotal = this.state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
                        const deliveryFee = this.state.selectedFulfillment === 'delivery' ? this.fulfillmentConfig.deliveryFee : 0;
                        qrAmountEl.textContent = (subtotal + deliveryFee).toFixed(2);
                    }
                }
            }
        },

        // Update checkout totals when fulfillment changes
        updateCheckoutTotals: function() {
            const subtotal = this.state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            const deliveryFee = this.state.selectedFulfillment === 'delivery'
                ? (this.state.selectedZone && this.state.selectedZone.delivery_fee != null
                    ? parseFloat(this.state.selectedZone.delivery_fee)
                    : this.fulfillmentConfig.deliveryFee)
                : 0;
            const total = subtotal + deliveryFee;
            
            const feeEl = document.getElementById('checkout-delivery-fee');
            const totalEl = document.getElementById('checkout-total');
            const qrAmountEl = document.getElementById('qr-amount');
            
            if (feeEl) feeEl.textContent = 'RM' + deliveryFee.toFixed(2);
            if (totalEl) totalEl.textContent = 'RM' + total.toFixed(2);
            if (qrAmountEl) qrAmountEl.textContent = total.toFixed(2);
        },

        // Select delivery zone
        selectZone: function(zoneId) {
            if (!zoneId) {
                this.state.selectedZone = null;
            } else {
                const zone = (this.state.zones || []).find(z => z.id === zoneId);
                this.state.selectedZone = zone || null;

                // Reflect fee/minimum into checkout logic
                if (zone) {
                    if (zone.zone_name) this.fulfillmentConfig.deliveryArea = zone.zone_name;
                    if (zone.delivery_fee != null) this.fulfillmentConfig.deliveryFee = parseFloat(zone.delivery_fee);
                    if (zone.minimum_order != null) this.fulfillmentConfig.minOrder = parseFloat(zone.minimum_order);
                }
            }

            this.updateCheckoutTotals();
        },

        // Render tracking view
        renderTracking: function() {
            if (!this.state.orderNumber) {
                return '<div class="binaapp-cart-empty">' + this.t('noActiveOrder') + '</div>';
            }

            if (this.state.trackingLoading) {
                return `
                    <div class="binaapp-tracking-status">
                        <div class="binaapp-spinner"></div>
                        <p>${this.t('loadingOrderStatus')}</p>
                        <p><strong>${this.t('orderNumber')}: ${this.state.orderNumber}</strong></p>
                    </div>
                `;
            }

            if (this.state.trackingError) {
                return `
                    <div class="binaapp-cart-empty">
                        <p>${this.state.trackingError}</p>
                        <button class="binaapp-checkout-btn" onclick="BinaAppDelivery.loadTracking()">
                            ${this.t('retry')}
                        </button>
                    </div>
                `;
            }

            if (!this.state.trackingData) {
                return `
                    <div class="binaapp-tracking-status">
                        <div class="binaapp-spinner"></div>
                        <p>${this.t('loadingOrderStatus')}</p>
                        <p><strong>${this.t('orderNumber')}: ${this.state.orderNumber}</strong></p>
                    </div>
                `;
            }

            const order = this.state.trackingData.order || {};
            const rider = this.state.trackingData.rider || null;
            const eta = this.state.trackingData.eta_minutes;
            const statusHistory = this.state.trackingData.status_history || [];

            // Status badge colors
            const statusColors = {
                pending: '#fbbf24',
                confirmed: '#3b82f6',
                preparing: '#f97316',
                ready: '#10b981',
                picked_up: '#8b5cf6',
                delivering: '#06b6d4',
                delivered: '#22c55e',
                completed: '#22c55e',
                cancelled: '#ef4444',
                rejected: '#ef4444'
            };

            const statusBgColor = statusColors[order.status] || '#6b7280';

            return `
                <div style="display:flex;flex-direction:column;gap:12px;">
                    <!-- Order Status Header -->
                    <div style="padding:20px;background:linear-gradient(135deg, ${statusBgColor}15 0%, ${statusBgColor}25 100%);border-radius:16px;border:2px solid ${statusBgColor}40;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <div style="width:48px;height:48px;background:${statusBgColor};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;">
                                ${this.getStatusEmoji(order.status)}
                            </div>
                            <div style="flex:1;">
                                <div style="font-weight:700;font-size:14px;color:#6b7280;">${this.t('orderNumber')}</div>
                                <div style="font-weight:800;font-size:18px;color:#1f2937;">${this.state.orderNumber}</div>
                            </div>
                        </div>
                        <div style="margin-top:12px;padding:12px;background:white;border-radius:12px;">
                            <div style="font-size:12px;color:#6b7280;text-transform:uppercase;">${this.t('status')}</div>
                            <div style="font-weight:700;font-size:16px;color:${statusBgColor};">${this.getStatusText(order.status)}</div>
                            ${eta != null ? `<div style="margin-top:4px;font-size:14px;color:#374151;">⏱️ ${this.t('eta')}: ~${eta} ${this.t('minutes')}</div>` : ''}
                        </div>
                    </div>

                    <!-- Rider Info Section -->
                    <div style="padding:16px;background:white;border:2px solid ${rider ? '#10b981' : '#e5e7eb'};border-radius:16px;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                            <span style="font-size:20px;">${rider ? '🛵' : '⏳'}</span>
                            <span style="font-weight:700;font-size:16px;">${this.t('riderInfo')}</span>
                            ${rider ? `<span style="background:#10b981;color:white;font-size:10px;padding:2px 8px;border-radius:10px;font-weight:600;">${this.t('assigned')}</span>` : ''}
                        </div>
                        ${rider ? `
                            <!-- Google Map (Phase 2) -->
                            ${rider.current_latitude && rider.current_longitude ? `
                                <div id="binaapp-rider-map" style="width:100%;height:250px;border-radius:12px;margin-bottom:12px;background:#f3f4f6;position:relative;overflow:hidden;">
                                    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;">
                                        <div class="binaapp-spinner" style="margin:0 auto 8px;"></div>
                                        <div style="color:#6b7280;font-size:12px;">Loading map...</div>
                                    </div>
                                </div>
                            ` : ''}

                            <div style="display:flex;align-items:center;gap:12px;">
                                <div style="width:56px;height:56px;background:#f3f4f6;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;">
                                    ${rider.photo_url ? `<img src="${rider.photo_url}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` : '🧑'}
                                </div>
                                <div style="flex:1;">
                                    <div style="font-weight:700;font-size:16px;color:#1f2937;">${rider.name || '-'}</div>
                                    <div style="color:#6b7280;font-size:14px;margin-top:2px;">
                                        ${rider.vehicle_type ? this.getVehicleEmoji(rider.vehicle_type) + ' ' : ''}
                                        ${rider.vehicle_type || ''}
                                        ${rider.vehicle_plate ? ` • ${rider.vehicle_plate}` : ''}
                                    </div>
                                    ${rider.rating ? `<div style="color:#fbbf24;font-size:14px;margin-top:2px;">⭐ ${rider.rating}</div>` : ''}
                                    ${rider.current_latitude && rider.current_longitude ? `
                                        <div style="color:#10b981;font-size:12px;margin-top:4px;">
                                            📍 ${this.t('liveTracking')}
                                        </div>
                                    ` : `
                                        <div style="color:#9ca3af;font-size:12px;margin-top:4px;">
                                            📍 ${this.t('gpsNotAvailable')}
                                        </div>
                                    `}
                                </div>
                            </div>
                            <div style="margin-top:12px;display:flex;gap:8px;">
                                <a href="tel:${rider.phone}" style="flex:1;display:flex;align-items:center;justify-content:center;gap:6px;padding:12px;background:#10b981;color:white;border-radius:12px;text-decoration:none;font-weight:600;">
                                    📞 ${this.t('callRider')}
                                </a>
                                <a href="https://wa.me/${(rider.phone || '').replace(/[^0-9]/g, '')}" target="_blank" style="flex:1;display:flex;align-items:center;justify-content:center;gap:6px;padding:12px;background:#25d366;color:white;border-radius:12px;text-decoration:none;font-weight:600;">
                                    💬 WhatsApp
                                </a>
                            </div>
                        ` : `
                            <div style="text-align:center;padding:16px;background:#f9fafb;border-radius:12px;">
                                <div style="font-size:32px;margin-bottom:8px;">🔍</div>
                                <div style="color:#6b7280;font-size:14px;">${this.t('riderNotAssigned')}</div>
                                <div style="color:#9ca3af;font-size:12px;margin-top:4px;">${this.t('riderWillBeAssigned')}</div>
                            </div>
                        `}
                    </div>

                    <!-- Status Timeline -->
                    ${statusHistory.length > 0 ? `
                    <div style="padding:16px;background:#f9fafb;border-radius:16px;">
                        <div style="font-weight:700;margin-bottom:12px;">📋 ${this.t('statusHistory')}</div>
                        <div style="display:flex;flex-direction:column;gap:8px;">
                            ${statusHistory.slice(-5).reverse().map((h, idx) => `
                                <div style="display:flex;align-items:center;gap:12px;${idx === 0 ? 'font-weight:600;' : 'opacity:0.7;'}">
                                    <div style="width:8px;height:8px;background:${idx === 0 ? statusBgColor : '#9ca3af'};border-radius:50%;"></div>
                                    <div style="flex:1;">
                                        <span>${this.getStatusText(h.status)}</span>
                                        ${h.notes ? `<span style="color:#6b7280;font-size:12px;"> - ${h.notes}</span>` : ''}
                                    </div>
                                    <div style="font-size:12px;color:#9ca3af;">${this.formatTime(h.created_at)}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}

                    <!-- GPS Tracking Status (Phase 2) -->
                    ${rider && rider.current_latitude && rider.current_longitude ? `
                        <div style="padding:12px;background:#d1fae5;border-radius:12px;text-align:center;">
                            <div style="font-size:12px;color:#065f46;font-weight:600;">
                                📡 ${this.t('liveTrackingActive')}
                            </div>
                            <div style="font-size:11px;color:#047857;margin-top:2px;">
                                ${this.t('updatesEvery15Seconds')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Chat with Seller Button -->
                    ${this.state.conversationId ? `
                    <button class="binaapp-checkout-btn" onclick="BinaAppDelivery.openChat()" style="background:linear-gradient(to right, #3b82f6, #2563eb);">
                        💬 ${this.t('chatWithSeller')}
                    </button>
                    ` : ''}

                    <!-- Refresh Button -->
                    <button class="binaapp-checkout-btn" onclick="BinaAppDelivery.loadTracking()" style="background:linear-gradient(to right, ${this.config.primaryColor}, ${this.adjustColor(this.config.primaryColor, -20)});">
                        🔄 ${this.t('refresh')}
                    </button>

                    <!-- Auto-refresh notice -->
                    <div style="text-align:center;font-size:12px;color:#9ca3af;">
                        ${this.t('autoRefreshNote')}
                    </div>
                </div>
            `;
        },

        // Get status emoji
        getStatusEmoji: function(status) {
            const emojis = {
                pending: '⏳',
                confirmed: '✅',
                preparing: '👨‍🍳',
                ready: '📦',
                picked_up: '🛵',
                delivering: '🚀',
                delivered: '🎉',
                completed: '✨',
                cancelled: '❌',
                rejected: '🚫'
            };
            return emojis[status] || '📋';
        },

        // Get status text in current language
        getStatusText: function(status) {
            const lang = this.config.language;
            const texts = {
                ms: {
                    pending: 'Menunggu Pengesahan',
                    confirmed: 'Disahkan',
                    preparing: 'Sedang Disediakan',
                    ready: 'Siap untuk Diambil',
                    picked_up: 'Rider Sudah Ambil',
                    delivering: 'Dalam Perjalanan',
                    delivered: 'Telah Dihantar',
                    completed: 'Selesai',
                    cancelled: 'Dibatalkan',
                    rejected: 'Ditolak'
                },
                en: {
                    pending: 'Pending Confirmation',
                    confirmed: 'Confirmed',
                    preparing: 'Being Prepared',
                    ready: 'Ready for Pickup',
                    picked_up: 'Picked Up by Rider',
                    delivering: 'On the Way',
                    delivered: 'Delivered',
                    completed: 'Completed',
                    cancelled: 'Cancelled',
                    rejected: 'Rejected'
                }
            };
            return (texts[lang] || texts.en)[status] || status;
        },

        // Get vehicle emoji
        getVehicleEmoji: function(type) {
            const emojis = {
                motorcycle: '🏍️',
                bicycle: '🚲',
                car: '🚗'
            };
            return emojis[type] || '🛵';
        },

        // Format timestamp
        formatTime: function(timestamp) {
            if (!timestamp) return '';
            try {
                const date = new Date(timestamp);
                return date.toLocaleTimeString(this.config.language === 'ms' ? 'ms-MY' : 'en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                return '';
            }
        },

        // ============================================
        // PHASE 3: LEAFLET.JS GPS TRACKING FUNCTIONS
        // ============================================

        // Load Leaflet CSS
        loadLeafletCSS: function() {
            if (document.getElementById('binaapp-leaflet-css')) return;

            const link = document.createElement('link');
            link.id = 'binaapp-leaflet-css';
            link.rel = 'stylesheet';
            link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            link.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
            link.crossOrigin = '';
            document.head.appendChild(link);
            console.log('[BinaApp] Leaflet CSS loaded');
        },

        // Load Leaflet JavaScript
        loadLeafletJS: function() {
            return new Promise((resolve, reject) => {
                if (window.L) {
                    resolve(window.L);
                    return;
                }

                const script = document.createElement('script');
                script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
                script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
                script.crossOrigin = '';
                script.onload = () => {
                    console.log('[BinaApp] Leaflet JS loaded');
                    resolve(window.L);
                };
                script.onerror = reject;
                document.body.appendChild(script);
            });
        },

        // Initialize rider tracking map
        initRiderTrackingMap: async function(riderLat, riderLng, customerLat, customerLng, riderName) {
            try {
                this.loadLeafletCSS();
                const L = await this.loadLeafletJS();

                // Wait for container to be in DOM
                await new Promise(resolve => setTimeout(resolve, 100));

                const container = document.getElementById('binaapp-rider-map');
                if (!container) {
                    console.error('[BinaApp Map] Container not found');
                    return;
                }

                // Clear existing map
                if (this.state.riderMap) {
                    this.state.riderMap.remove();
                    this.state.riderMap = null;
                }

                // Create map centered on rider
                this.state.riderMap = L.map('binaapp-rider-map', {
                    zoomControl: true,
                    attributionControl: true
                }).setView([riderLat, riderLng], 14);

                // Add OpenStreetMap tiles (FREE!)
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                    maxZoom: 19,
                    minZoom: 10
                }).addTo(this.state.riderMap);

                // Custom rider icon (motorcycle)
                const riderIcon = L.divIcon({
                    html: `
                        <div style="
                            width: 50px;
                            height: 50px;
                            background: linear-gradient(135deg, #ea580c 0%, #fb923c 100%);
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            box-shadow: 0 4px 12px rgba(234, 88, 12, 0.5);
                            border: 4px solid white;
                            font-size: 26px;
                        ">
                            🛵
                        </div>
                    `,
                    className: '',
                    iconSize: [50, 50],
                    iconAnchor: [25, 25],
                    popupAnchor: [0, -25]
                });

                // Custom customer icon (location pin)
                const customerIcon = L.divIcon({
                    html: `
                        <div style="
                            width: 40px;
                            height: 40px;
                            background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
                            border-radius: 50% 50% 50% 0;
                            transform: rotate(-45deg);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.5);
                            border: 3px solid white;
                        ">
                            <span style="transform: rotate(45deg); font-size: 20px;">📍</span>
                        </div>
                    `,
                    className: '',
                    iconSize: [40, 40],
                    iconAnchor: [20, 40],
                    popupAnchor: [0, -40]
                });

                // Add rider marker
                this.state.riderMarker = L.marker([riderLat, riderLng], { icon: riderIcon })
                    .addTo(this.state.riderMap)
                    .bindPopup(`
                        <div style="text-align: center; font-family: system-ui; padding: 8px;">
                            <strong style="font-size: 16px; display: block; margin-bottom: 4px;">
                                🛵 ${riderName}
                            </strong>
                            <span style="font-size: 13px; color: #666;">
                                ${this.t('riderOnTheWay')}
                            </span>
                        </div>
                    `);

                // Add customer marker
                this.state.customerMarker = L.marker([customerLat, customerLng], { icon: customerIcon })
                    .addTo(this.state.riderMap)
                    .bindPopup(`
                        <div style="text-align: center; font-family: system-ui; padding: 8px;">
                            <strong style="font-size: 16px; display: block; margin-bottom: 4px;">
                                📍 ${this.t('yourDestination')}
                            </strong>
                            <span style="font-size: 13px; color: #666;">
                                ${this.t('deliveryLocation')}
                            </span>
                        </div>
                    `);

                // Draw route line
                this.state.routeLine = L.polyline(
                    [[riderLat, riderLng], [customerLat, customerLng]],
                    {
                        color: '#ea580c',
                        weight: 4,
                        opacity: 0.7,
                        dashArray: '10, 10',
                        lineCap: 'round'
                    }
                ).addTo(this.state.riderMap);

                // Calculate distance (Haversine formula)
                const R = 6371; // Earth's radius in km
                const dLat = (customerLat - riderLat) * Math.PI / 180;
                const dLng = (customerLng - riderLng) * Math.PI / 180;
                const a =
                    Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(riderLat * Math.PI / 180) * Math.cos(customerLat * Math.PI / 180) *
                    Math.sin(dLng/2) * Math.sin(dLng/2);
                const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                const distance = R * c;

                // Estimate ETA (30 km/h average city speed)
                const etaMinutes = Math.ceil((distance / 30) * 60);

                // Fit map to show both markers
                const bounds = L.latLngBounds([
                    [riderLat, riderLng],
                    [customerLat, customerLng]
                ]);
                this.state.riderMap.fitBounds(bounds, { padding: [80, 80] });

                // Store distance and ETA in state
                this.state.mapDistance = distance;
                this.state.mapETA = etaMinutes;

                console.log('[BinaApp Map] Initialized successfully - Distance:', distance.toFixed(1), 'km, ETA:', etaMinutes, 'min');

            } catch (error) {
                console.error('[BinaApp Map] Failed to initialize:', error);
            }
        },

        // Update rider position on map
        updateRiderPosition: function(newLat, newLng) {
            if (!this.state.riderMarker || !this.state.riderMap) {
                console.warn('[BinaApp Map] Map not initialized, cannot update position');
                return;
            }

            const newLatLng = [newLat, newLng];

            // Smooth animation
            this.state.riderMarker.setLatLng(newLatLng);

            // Update route line
            if (this.state.routeLine && this.state.customerMarker) {
                const customerLatLng = this.state.customerMarker.getLatLng();
                this.state.routeLine.setLatLngs([newLatLng, [customerLatLng.lat, customerLatLng.lng]]);
            }

            console.log('[BinaApp Map] Rider position updated:', newLat.toFixed(6), newLng.toFixed(6));
        },

        // Attach event listeners for views
        attachViewEventListeners: function(view) {
            if (view === 'checkout') {
                const form = document.getElementById('binaapp-checkout-form');
                if (form) {
                    form.addEventListener('submit', (e) => {
                        e.preventDefault();
                        this.submitOrder(new FormData(form));
                    });
                }
            }
        },

        // Add item to cart
        addToCart: function(itemId) {
            const item = this.state.menu.items.find(i => i.id === itemId);
            if (!item) return;

            const cartItem = {
                id: item.id,
                name: item.name,
                price: parseFloat(item.price),
                quantity: 1,
                size: this.state.selectedSize,
                color: this.state.selectedColor
            };

            const existingIndex = this.state.cart.findIndex(c =>
                c.id === itemId && c.size === cartItem.size && c.color === cartItem.color
            );

            if (existingIndex >= 0) {
                this.state.cart[existingIndex].quantity++;
            } else {
                this.state.cart.push(cartItem);
            }

            // Reset selections
            this.state.selectedSize = null;
            this.state.selectedColor = null;

            this.updateCartBadge();
            this.showNotification(this.t('addedToCart'));
        },

        // Update item quantity
        updateQuantity: function(index, newQuantity) {
            if (newQuantity <= 0) {
                this.state.cart.splice(index, 1);
            } else {
                this.state.cart[index].quantity = newQuantity;
            }

            this.updateCartBadge();
            this.showView('cart');
        },

        // Update cart badge
        updateCartBadge: function() {
            const badge = document.getElementById('binaapp-cart-count');
            const count = this.state.cart.reduce((sum, item) => sum + item.quantity, 0);

            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        },

        // Submit order via API (backend-first, WhatsApp as notification)
        submitOrder: async function(formData) {
            try {
                const config = this.getConfig();
                const payment = this.paymentConfig;
                const fulfillment = this.fulfillmentConfig;
                
                // Validate selections
                if ((fulfillment.delivery || fulfillment.pickup) && !this.state.selectedFulfillment) {
                    alert(this.t('selectFulfillmentError'));
                    return;
                }
                
                if ((payment.cod || payment.qr) && !this.state.selectedPayment) {
                    alert(this.t('selectPaymentError'));
                    return;
                }
                
                // Check minimum order for delivery
                const subtotal = this.state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
                if (this.state.selectedFulfillment === 'delivery' && subtotal < fulfillment.minOrder) {
                    alert(`Minimum order untuk delivery adalah RM${fulfillment.minOrder.toFixed(2)}`);
                    return;
                }

                // Require delivery zone when zones exist (needed for correct fee/minimum + backend validation)
                if (this.state.selectedFulfillment === 'delivery' && (this.state.zones || []).length > 0 && !this.state.selectedZone) {
                    alert(this.t('selectZoneError'));
                    return;
                }
                
                // Get form data - ensure all values are strings (never null/undefined)
                const customerName = (formData.get('customer_name') || '').toString().trim();
                const customerPhone = (formData.get('customer_phone') || '').toString().trim();
                const deliveryAddress = (document.getElementById('delivery-address')?.value || formData.get('delivery_address') || '').toString().trim();
                const deliveryNotes = (formData.get('delivery_notes') || '').toString().trim();
                const timeSlot = (formData.get('time_slot') || '').toString().trim();
                const appointmentDate = (formData.get('appointment_date') || '').toString().trim();
                const cakeMessage = (formData.get('cake_message') || '').toString().trim();

                // Validate required fields
                if (!customerName) {
                    alert('Sila masukkan nama anda');
                    return;
                }
                if (!customerPhone) {
                    alert('Sila masukkan nombor telefon anda');
                    return;
                }
                // Only require delivery address when delivery is selected (not for pickup)
                if (this.state.selectedFulfillment === 'delivery' && !deliveryAddress) {
                    alert('Sila masukkan alamat penghantaran');
                    return;
                }

                // Calculate totals
                const deliveryFee = this.state.selectedFulfillment === 'delivery' ? fulfillment.deliveryFee : 0;
                const total = subtotal + deliveryFee;

                // Show loading state
                const submitBtn = document.querySelector('#binaapp-checkout-form button[type="submit"]');
                const originalBtnText = submitBtn ? submitBtn.innerHTML : '';
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '⏳ ' + this.t('creatingOrder') + '...';
                }

                // ============================================
                // STEP 1: CREATE ORDER IN BACKEND (REQUIRED)
                // ============================================
                let createdOrder = null;
                let orderError = null;

                try {
                    // Build order payload - all string fields are guaranteed non-null from validation above
                    const orderPayload = {
                        website_id: this.config.websiteId,
                        customer_name: customerName,  // Already validated as non-empty string
                        customer_phone: customerPhone,  // Already validated as non-empty string
                        customer_email: "",
                        delivery_address: this.state.selectedFulfillment === 'delivery'
                            ? deliveryAddress  // Already validated as non-empty string for delivery
                            : (fulfillment.pickupAddress || 'Self Pickup'),
                        delivery_notes: deliveryNotes,  // Already converted to string (may be empty)
                        delivery_zone_id: this.state.selectedFulfillment === 'delivery'
                            ? (this.state.selectedZone ? String(this.state.selectedZone.id) : null)
                            : null,
                        items: this.state.cart.map(item => ({
                            menu_item_id: item.id,
                            quantity: item.quantity,
                            options: {
                                size: (item.size || '').toString(),
                                color: (item.color || '').toString()
                            },
                            notes: ""
                        })),
                        payment_method: this.state.selectedPayment === 'qr' ? 'online' : 'cod'
                    };

                    console.log('[BinaApp] Creating order in backend...', orderPayload);

                    const createRes = await fetch(`${this.config.apiUrl}/delivery/orders`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(orderPayload)
                    });

                    if (createRes.ok) {
                        createdOrder = await createRes.json();
                        this.state.orderNumber = createdOrder.order_number || null;
                        this.state.conversationId = createdOrder.conversation_id || null;
                        this.state.customerId = createdOrder.customer_id || null;
                        // Store for future orders
                        if (this.state.customerId) {
                            localStorage.setItem('binaapp_customer_id', this.state.customerId);
                            localStorage.setItem('binaapp_customer_phone', customerPhone);
                            localStorage.setItem('binaapp_customer_name', customerName);
                        }
                        console.log('[BinaApp] ✅ Order created:', this.state.orderNumber, 'conversation:', this.state.conversationId);
                    } else {
                        const errorText = await createRes.text();
                        let errorMessage = 'Failed to create order';
                        try {
                            const errorJson = JSON.parse(errorText);
                            if (errorJson.detail) {
                                // Handle array of error objects (validation errors)
                                if (Array.isArray(errorJson.detail)) {
                                    errorMessage = errorJson.detail.map(err => {
                                        if (typeof err === 'object' && err.msg) {
                                            return err.msg;
                                        } else if (typeof err === 'string') {
                                            return err;
                                        } else {
                                            return JSON.stringify(err);
                                        }
                                    }).join(', ');
                                } else if (typeof errorJson.detail === 'string') {
                                    errorMessage = errorJson.detail;
                                } else {
                                    // For other object types, stringify them
                                    errorMessage = JSON.stringify(errorJson.detail);
                                }
                            }
                        } catch (e) {
                            errorMessage = errorText || errorMessage;
                        }
                        orderError = errorMessage;
                        console.error('[BinaApp] ❌ Order creation failed:', errorMessage);
                    }
                } catch (createErr) {
                    orderError = createErr.message || 'Network error';
                    console.error('[BinaApp] ❌ Order creation error:', createErr);
                }

                // Restore button state
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }

                // If backend order failed, show error and stop
                if (!createdOrder || !this.state.orderNumber) {
                    alert(this.t('orderCreationFailed') + (orderError ? ': ' + orderError : ''));
                    return;
                }

                // ============================================
                // ORDER CREATED SUCCESSFULLY - Now build notification
                // ============================================
                // WhatsApp is now just a notification, not the core flow
                
                // Build WhatsApp message
                let msg = `${config.emoji} *${config.orderTitle} - ${this.config.businessName}*\n\n`;
                
                // Order items
                msg += `📝 *Pesanan:*\n`;
                this.state.cart.forEach(item => {
                    msg += `• ${item.name}`;
                    if (item.size) msg += ` (${item.size})`;
                    if (item.color) msg += ` - ${item.color}`;
                    msg += ` x${item.quantity} - RM${(item.price * item.quantity).toFixed(2)}\n`;
                });
                
                msg += `\n━━━━━━━━━━━━━━━━\n`;
                
                // Customer info
                msg += `👤 *Pelanggan:*\n`;
                msg += `Nama: ${customerName}\n`;
                msg += `Tel: ${customerPhone}\n`;
                
                msg += `\n━━━━━━━━━━━━━━━━\n`;
                
                // Fulfillment details
                if (this.state.selectedFulfillment === 'delivery') {
                    msg += `🛵 *Penghantaran:* Delivery\n`;
                    msg += `📍 *Alamat:* ${deliveryAddress || '(Sila nyatakan alamat)'}\n`;
                    msg += `💰 *Caj Delivery:* RM${deliveryFee.toFixed(2)}\n`;
                } else {
                    msg += `🏪 *Penghantaran:* Self Pickup\n`;
                    msg += `📍 *Lokasi:* ${fulfillment.pickupAddress || 'Di kedai'}\n`;
                }
                
                // Time slot if selected
                if (timeSlot) {
                    msg += `⏰ *Masa:* ${timeSlot}\n`;
                }
                
                // Appointment date if selected
                if (appointmentDate) {
                    msg += `📅 *Tarikh:* ${appointmentDate}\n`;
                }
                
                // Cake message if any
                if (cakeMessage) {
                    msg += `🎂 *Mesej Kek:* ${cakeMessage}\n`;
                }
                
                // Special instructions
                if (deliveryNotes) {
                    msg += `📝 *Nota:* ${deliveryNotes}\n`;
                }
                
                msg += `\n━━━━━━━━━━━━━━━━\n`;
                
                // Payment method
                msg += `💳 *Cara Bayar:* ${this.state.selectedPayment === 'cod' ? 'Bayar Tunai (COD)' : 'QR Payment'}\n`;
                
                if (this.state.selectedPayment === 'qr') {
                    msg += `✅ *Status:* Sudah bayar (bukti di bawah)\n`;
                }
                
                // Totals
                msg += `\n━━━━━━━━━━━━━━━━\n`;
                msg += `Subtotal: RM${subtotal.toFixed(2)}\n`;
                if (deliveryFee > 0) {
                    msg += `Delivery: RM${deliveryFee.toFixed(2)}\n`;
                }
                msg += `\n*JUMLAH: RM${total.toFixed(2)}*\n\n`;
                msg += `Terima kasih! 🙏`;
                
                // ============================================
                // STEP 2: SEND WHATSAPP NOTIFICATION TO MERCHANT
                // ============================================
                // Order is already saved in backend - WhatsApp is just a notification
                
                // Include order number in WhatsApp message (always present now)
                msg = `*🆕 PESANAN BARU*\n*No. Pesanan:* ${this.state.orderNumber}\n\n` + msg;
                msg += `\n\n📱 *Lihat & urus pesanan di Dashboard BinaApp*`;

                // Get WhatsApp number
                let whatsappNumber = this.config.whatsappNumber;
                
                if (whatsappNumber) {
                    // Clean the number
                    whatsappNumber = whatsappNumber.replace(/[^0-9]/g, '');
                    
                    // Open WhatsApp (merchant notification)
                    const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(msg)}`;
                    window.open(whatsappUrl, '_blank');
                    
                    console.log('[BinaApp] ✅ WhatsApp notification sent to merchant');
                } else {
                    // No WhatsApp number configured - just log it
                    console.log('[BinaApp] ℹ️ No WhatsApp number configured, skipping notification');
                }
                
                // ============================================
                // STEP 3: SHOW SUCCESS & TRACKING VIEW
                // ============================================
                
                // Clear cart and reset selections
                this.state.cart = [];
                this.state.selectedFulfillment = null;
                this.state.selectedPayment = null;
                this.updateCartBadge();
                
                // Show success notification
                this.showNotification(this.t('orderCreatedSuccess'));
                
                // Show tracking view (order is in backend, can be tracked)
                this.showView('tracking');

            } catch (error) {
                console.error('[BinaApp] Order error:', error);
                alert(this.t('orderError') + ': ' + error.message);
            }
        },

        // Open chat with seller
        openChat: function() {
            if (!this.state.conversationId || !this.state.customerId) {
                this.showNotification('Chat tidak tersedia');
                return;
            }

            const chatUrl = `${window.location.origin}/chat/${this.state.conversationId}?customer=${this.state.customerId}&name=${encodeURIComponent(localStorage.getItem('binaapp_customer_name') || 'Pelanggan')}`;

            // For now, open in a new tab - later can be a modal
            window.open(chatUrl, '_blank');

            console.log('[BinaApp] Opening chat:', this.state.conversationId);
        },

        // Show notification
        showNotification: function(message) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #10b981;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                z-index: 100001;
                animation: slideIn 0.3s ease-out;
            `;
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.remove();
            }, 2000);
        },

        // Translation helper
        t: function(key) {
            const translations = {
                ms: {
                    orderNow: 'Pesan Sekarang',
                    orderFood: 'Pesan Makanan',
                    loading: 'Memuatkan...',
                    noMenuAvailable: 'Tiada menu tersedia',
                    addToCart: 'Tambah ke Bakul',
                    viewCart: 'Lihat Bakul',
                    items: 'item',
                    yourCart: 'Bakul Anda',
                    cartEmpty: 'Bakul anda kosong',
                    startOrdering: 'Mula Pesan',
                    subtotal: 'Jumlah Kecil',
                    proceedToCheckout: 'Teruskan ke Pembayaran',
                    checkout: 'Pembayaran',
                    deliveryZone: 'Kawasan Penghantaran',
                    selectZone: 'Pilih Kawasan',
                    name: 'Nama',
                    phone: 'No. Telefon',
                    email: 'Email',
                    optional: 'pilihan',
                    address: 'Alamat',
                    notes: 'Nota',
                    placeOrder: 'Hantar Pesanan',
                    addedToCart: 'Ditambah ke bakul',
                    orderPlacedSuccess: 'Pesanan berjaya dihantar!',
                    orderNumber: 'No. Pesanan',
                    orderError: 'Ralat pesanan',
                    trackOrder: 'Jejak Pesanan',
                    noActiveOrder: 'Tiada pesanan aktif',
                    loadingOrderStatus: 'Memuatkan status pesanan...',
                    trackingLoadFailed: 'Gagal memuatkan maklumat pesanan. Cuba lagi.',
                    retry: 'Cuba Lagi',
                    refresh: 'Muat Semula',
                    status: 'Status',
                    riderInfo: 'Info Rider',
                    riderNotAssigned: 'Rider belum ditetapkan',
                    riderWillBeAssigned: 'Rider akan ditetapkan sebentar lagi',
                    noGpsPhase1: 'Lokasi GPS rider akan dipaparkan dalam versi akan datang',
                    liveTracking: 'Pengesanan Langsung',
                    riderOnTheWay: 'Rider sedang dalam perjalanan',
                    yourDestination: 'Destinasi Anda',
                    deliveryLocation: 'Lokasi penghantaran',
                    liveTrackingActive: 'Pengesanan GPS Aktif',
                    gpsNotAvailable: 'GPS tidak tersedia lagi',
                    updatesEvery15Seconds: 'Dikemas kini setiap 15 saat',
                    zoneAffectsFees: 'Caj dan minimum order ikut kawasan yang dipilih.',
                    selectZoneError: 'Sila pilih kawasan penghantaran terlebih dahulu.',
                    selectSize: 'Pilih Saiz',
                    selectColor: 'Pilih Warna',
                    selectDate: 'Pilih Tarikh',
                    selectTime: 'Pilih Masa',
                    selectStaff: 'Pilih Staff',
                    selectLocation: 'Pilih Lokasi',
                    shippingMethod: 'Cara Penghantaran',
                    cakeMessage: 'Mesej Atas Kek',
                    // New payment & fulfillment translations
                    selectFulfillment: 'Pilih Cara Terima',
                    selectPayment: 'Cara Bayaran',
                    deliveryAddress: 'Alamat Penghantaran',
                    selectFulfillmentError: 'Sila pilih cara terima (Delivery/Pickup)',
                    selectPaymentError: 'Sila pilih cara bayaran',
                    orderSent: 'Pesanan dihantar ke WhatsApp!',
                    delivery: 'Delivery',
                    pickup: 'Self Pickup',
                    cod: 'Bayar Tunai (COD)',
                    qrPayment: 'QR Payment',
                    // Enhanced tracking translations
                    assigned: 'Ditetapkan',
                    callRider: 'Hubungi Rider',
                    statusHistory: 'Sejarah Status',
                    eta: 'Anggaran Tiba',
                    minutes: 'minit',
                    autoRefreshNote: 'Tekan butang untuk muat semula status terkini',
                    // Order creation
                    creatingOrder: 'Membuat pesanan',
                    orderCreationFailed: 'Gagal membuat pesanan',
                    orderCreatedSuccess: 'Pesanan berjaya dibuat!',
                    // Chat
                    chatWithSeller: 'Chat dengan Penjual'
                },
                en: {
                    orderNow: 'Order Now',
                    orderFood: 'Order Food',
                    loading: 'Loading...',
                    noMenuAvailable: 'No menu available',
                    addToCart: 'Add to Cart',
                    viewCart: 'View Cart',
                    items: 'items',
                    yourCart: 'Your Cart',
                    cartEmpty: 'Your cart is empty',
                    startOrdering: 'Start Ordering',
                    subtotal: 'Subtotal',
                    proceedToCheckout: 'Proceed to Checkout',
                    checkout: 'Checkout',
                    deliveryZone: 'Delivery Zone',
                    selectZone: 'Select Zone',
                    name: 'Name',
                    phone: 'Phone Number',
                    email: 'Email',
                    optional: 'optional',
                    address: 'Address',
                    notes: 'Notes',
                    placeOrder: 'Place Order',
                    addedToCart: 'Added to cart',
                    orderPlacedSuccess: 'Order placed successfully!',
                    orderNumber: 'Order Number',
                    orderError: 'Order error',
                    trackOrder: 'Track Order',
                    noActiveOrder: 'No active order',
                    loadingOrderStatus: 'Loading order status...',
                    trackingLoadFailed: 'Failed to load order details. Please try again.',
                    retry: 'Retry',
                    refresh: 'Refresh',
                    status: 'Status',
                    riderInfo: 'Rider Info',
                    riderNotAssigned: 'Rider not assigned yet',
                    riderWillBeAssigned: 'Rider will be assigned shortly',
                    noGpsPhase1: 'Rider GPS location will be available in future updates',
                    liveTracking: 'Live Tracking',
                    riderOnTheWay: 'Rider is on the way',
                    yourDestination: 'Your Destination',
                    deliveryLocation: 'Delivery location',
                    liveTrackingActive: 'GPS Tracking Active',
                    gpsNotAvailable: 'GPS not available yet',
                    updatesEvery15Seconds: 'Updates every 15 seconds',
                    zoneAffectsFees: 'Fees and minimum order depend on selected zone.',
                    selectZoneError: 'Please select a delivery zone first.',
                    selectSize: 'Select Size',
                    selectColor: 'Select Color',
                    selectDate: 'Select Date',
                    selectTime: 'Select Time',
                    selectStaff: 'Select Staff',
                    selectLocation: 'Select Location',
                    shippingMethod: 'Shipping Method',
                    cakeMessage: 'Cake Message',
                    // New payment & fulfillment translations
                    selectFulfillment: 'Select Delivery Method',
                    selectPayment: 'Payment Method',
                    deliveryAddress: 'Delivery Address',
                    selectFulfillmentError: 'Please select delivery method (Delivery/Pickup)',
                    selectPaymentError: 'Please select payment method',
                    orderSent: 'Order sent to WhatsApp!',
                    delivery: 'Delivery',
                    pickup: 'Self Pickup',
                    cod: 'Cash on Delivery (COD)',
                    qrPayment: 'QR Payment',
                    // Enhanced tracking translations
                    assigned: 'Assigned',
                    callRider: 'Call Rider',
                    statusHistory: 'Status History',
                    eta: 'Est. Arrival',
                    minutes: 'mins',
                    autoRefreshNote: 'Tap refresh button to get latest status',
                    // Order creation
                    creatingOrder: 'Creating order',
                    orderCreationFailed: 'Failed to create order',
                    orderCreatedSuccess: 'Order created successfully!',
                    // Chat
                    chatWithSeller: 'Chat with Seller'
                }
            };

            const lang = this.config.language;
            return translations[lang]?.[key] || translations.en[key] || key;
        }
    };
    // Auto-initialize from data attributes if present
    (function autoInit() {
        const currentScript = document.currentScript || document.querySelector('script[data-website-id]');

        if (currentScript) {
            const websiteId = currentScript.getAttribute('data-website-id');
            const apiUrl = currentScript.getAttribute('data-api-url');
            const primaryColor = currentScript.getAttribute('data-primary-color');
            const language = currentScript.getAttribute('data-language');
            const businessType = currentScript.getAttribute('data-business-type');

            if (websiteId) {
                console.log('[BinaApp] Auto-initializing from data attributes');
                console.log('[BinaApp] Website ID:', websiteId);

                // Auto-initialize widget
                const config = {
                    websiteId: websiteId
                };

                if (apiUrl) config.apiUrl = apiUrl;
                if (primaryColor) config.primaryColor = primaryColor;
                if (language) config.language = language;
                if (businessType) config.businessType = businessType;

                // Initialize with a small delay to ensure DOM is ready
                setTimeout(() => {
                    window.BinaAppDelivery.init(config);
                }, 100);
            } else {
                console.warn('[BinaApp] No website ID found in script tag data attributes');
                console.log('[BinaApp] Will try to fetch by domain or wait for manual init()');

                // Try to fetch website_id from backend using current domain as fallback
                const hostname = window.location.hostname;
                if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1') {
                    console.log('[BinaApp] Attempting to fetch website_id for domain:', hostname);

                    const apiBaseUrl = apiUrl || 'https://binaapp-backend.onrender.com';
                    fetch(`${apiBaseUrl}/api/v1/websites/by-domain/${hostname}`)
                        .then(response => {
                            if (!response.ok) throw new Error(`HTTP ${response.status}`);
                            return response.json();
                        })
                        .then(website => {
                            console.log('[BinaApp] ✅ Found website by domain:', website.id);

                            const config = {
                                websiteId: website.id,
                                apiUrl: apiBaseUrl
                            };

                            if (primaryColor) config.primaryColor = primaryColor;
                            if (language) config.language = language;
                            if (businessType) config.businessType = businessType;

                            setTimeout(() => {
                                window.BinaAppDelivery.init(config);
                            }, 100);
                        })
                        .catch(error => {
                            console.error('[BinaApp] ❌ Failed to fetch website by domain:', error);
                            console.log('[BinaApp] Widget initialization deferred - call BinaAppDelivery.init() manually');
                        });
                }
            }
        }
    })();

})();
