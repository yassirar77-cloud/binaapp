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
 *     apiUrl: 'https://api.binaapp.my/v1',
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
            apiUrl: 'https://api.binaapp.my/v1',
            businessType: 'food',
            primaryColor: '#ea580c',
            language: 'ms'
        },

        businessConfig: null,

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
            orderNumber: null
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

            this.injectStyles();
            this.createWidget();
            this.loadData();
            this.initEventListeners();

            console.log('[BinaApp] Universal order widget initialized for:', this.config.businessType);
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

                console.log('[BinaApp] Data loaded:', this.state);
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
                    break;
            }

            this.attachViewEventListeners(view);
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

            let html = '<form id="binaapp-checkout-form">';

            // Appointment date (salon, services, bakery)
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
                        <select class="binaapp-form-select" name="time_slot" required>
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

            // Location choice (services)
            if (features.locationChoice && config.locationOptions) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">📍 ${this.t('selectLocation')}</label>
                        ${config.locationOptions.map((opt, i) => `
                            <div class="binaapp-shipping-option ${i === 0 ? 'selected' : ''}"
                                 onclick="BinaAppDelivery.selectLocation('${opt.id}', ${opt.extraFee}, this)">
                                <input type="radio" name="location" value="${opt.id}" ${i === 0 ? 'checked' : ''}>
                                <div style="flex:1;">
                                    <p style="font-weight:600;margin:0;">${opt.icon} ${opt.name}</p>
                                </div>
                                <span style="font-weight:bold;color:${opt.extraFee === 0 ? '#10b981' : '#ea580c'};">
                                    ${opt.extraFee === 0 ? 'FREE' : '+RM' + opt.extraFee}
                                </span>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            // Zone selection (food)
            if (features.deliveryZones && this.state.zones.length > 0) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">${this.t('deliveryZone')}</label>
                        <select class="binaapp-form-select" name="zone" required>
                            <option value="">${this.t('selectZone')}</option>
                `;

                this.state.zones.forEach(zone => {
                    html += `<option value="${zone.id}" data-fee="${zone.delivery_fee}">
                        ${zone.zone_name} - RM ${parseFloat(zone.delivery_fee).toFixed(2)}
                    </option>`;
                });

                html += `
                        </select>
                    </div>
                `;
            }

            // Shipping options (clothing, general)
            if (features.shippingOptions && config.shippingOptions) {
                html += `
                    <div class="binaapp-form-group">
                        <label class="binaapp-form-label">📦 ${this.t('shippingMethod')}</label>
                        ${config.shippingOptions.map((opt, i) => `
                            <div class="binaapp-shipping-option ${i === 0 ? 'selected' : ''}"
                                 onclick="BinaAppDelivery.selectShipping('${opt.id}', ${opt.price}, this)">
                                <input type="radio" name="shipping" value="${opt.id}" ${i === 0 ? 'checked' : ''}>
                                <div style="flex:1;">
                                    <p style="font-weight:600;margin:0;">${opt.name}</p>
                                    <p style="font-size:12px;color:#6b7280;margin:0;">${opt.desc}</p>
                                </div>
                                <span style="font-weight:bold;color:${opt.price === 0 ? '#10b981' : '#ea580c'};">
                                    ${opt.price === 0 ? 'FREE' : 'RM' + opt.price}
                                </span>
                            </div>
                        `).join('')}
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

            // Customer info
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
                    <label class="binaapp-form-label">${this.t('email')} (${this.t('optional')})</label>
                    <input type="email" class="binaapp-form-input" name="customer_email">
                </div>

                <div class="binaapp-form-group">
                    <label class="binaapp-form-label">${this.t('address')}</label>
                    <textarea class="binaapp-form-textarea" name="delivery_address" rows="3" required></textarea>
                </div>

                <div class="binaapp-form-group">
                    <label class="binaapp-form-label">${this.t('notes')} (${this.t('optional')})</label>
                    <textarea class="binaapp-form-textarea" name="delivery_notes" rows="2"></textarea>
                </div>

                <button type="submit" class="binaapp-checkout-btn">
                    ${this.t('placeOrder')}
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

        // Render tracking view
        renderTracking: function() {
            if (!this.state.orderNumber) {
                return '<div class="binaapp-cart-empty">' + this.t('noActiveOrder') + '</div>';
            }

            return `
                <div class="binaapp-tracking-status">
                    <div class="binaapp-spinner"></div>
                    <p>${this.t('loadingOrderStatus')}</p>
                    <p><strong>${this.t('orderNumber')}: ${this.state.orderNumber}</strong></p>
                </div>
            `;
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

        // Submit order
        submitOrder: async function(formData) {
            try {
                const config = this.getConfig();
                const orderData = {
                    website_id: this.config.websiteId,
                    business_type: this.config.businessType,
                    customer_name: formData.get('customer_name'),
                    customer_phone: formData.get('customer_phone'),
                    customer_email: formData.get('customer_email'),
                    delivery_address: formData.get('delivery_address'),
                    delivery_notes: formData.get('delivery_notes'),
                    delivery_zone_id: formData.get('zone'),
                    payment_method: 'cod',
                    items: this.state.cart.map(item => ({
                        menu_item_id: item.id,
                        quantity: item.quantity,
                        size: item.size,
                        color: item.color
                    })),
                    // Business-specific fields
                    appointment_date: formData.get('appointment_date'),
                    time_slot: formData.get('time_slot'),
                    staff: formData.get('staff'),
                    shipping_method: formData.get('shipping'),
                    location: formData.get('location'),
                    cake_message: formData.get('cake_message')
                };

                const response = await fetch(`${this.config.apiUrl}/delivery/orders`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(orderData)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to place order');
                }

                const result = await response.json();
                this.state.orderNumber = result.order_number;
                this.state.cart = [];
                this.updateCartBadge();

                alert(this.t('orderPlacedSuccess') + '\n' + this.t('orderNumber') + ': ' + result.order_number);
                this.closeModal();

            } catch (error) {
                console.error('[BinaApp] Order error:', error);
                alert(this.t('orderError') + ': ' + error.message);
            }
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
                    selectSize: 'Pilih Saiz',
                    selectColor: 'Pilih Warna',
                    selectDate: 'Pilih Tarikh',
                    selectTime: 'Pilih Masa',
                    selectStaff: 'Pilih Staff',
                    selectLocation: 'Pilih Lokasi',
                    shippingMethod: 'Cara Penghantaran',
                    cakeMessage: 'Mesej Atas Kek'
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
                    selectSize: 'Select Size',
                    selectColor: 'Select Color',
                    selectDate: 'Select Date',
                    selectTime: 'Select Time',
                    selectStaff: 'Select Staff',
                    selectLocation: 'Select Location',
                    shippingMethod: 'Shipping Method',
                    cakeMessage: 'Cake Message'
                }
            };

            const lang = this.config.language;
            return translations[lang]?.[key] || translations.en[key] || key;
        }
    };
})();
