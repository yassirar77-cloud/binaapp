/**
 * BinaApp Delivery Widget
 *
 * Embed this widget on any website to enable food delivery ordering
 *
 * Usage:
 * <script src="https://binaapp.my/widgets/delivery-widget.js"></script>
 * <script>
 *   BinaAppDelivery.init({
 *     websiteId: 'your-website-id',
 *     apiUrl: 'https://api.binaapp.my/v1',
 *     primaryColor: '#ea580c',
 *     language: 'ms'  // 'ms' or 'en'
 *   });
 * </script>
 */

(function() {
    'use strict';

    // Widget namespace
    window.BinaAppDelivery = {
        config: {
            websiteId: null,
            apiUrl: 'https://api.binaapp.my/v1',
            primaryColor: '#ea580c',
            language: 'ms'
        },

        state: {
            zones: [],
            menu: { categories: [], items: [] },
            cart: [],
            selectedZone: null,
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

            this.injectStyles();
            this.createWidget();
            this.loadData();
            this.initEventListeners();

            console.log('[BinaApp] Delivery widget initialized');
        },

        // Inject widget styles
        injectStyles: function() {
            const styles = `
                /* BinaApp Delivery Widget Styles */
                #binaapp-widget {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 99999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                #binaapp-order-btn {
                    background: linear-gradient(135deg, ${this.config.primaryColor} 0%, #c2410c 100%);
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
                    background: linear-gradient(135deg, ${this.config.primaryColor} 0%, #c2410c 100%);
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
                    color: ${this.config.primaryColor};
                }

                .binaapp-add-to-cart-btn {
                    background: ${this.config.primaryColor};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    width: 100%;
                    margin-top: 8px;
                    cursor: pointer;
                    font-weight: 600;
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
                    border-top-color: ${this.config.primaryColor};
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

        // Create widget DOM
        createWidget: function() {
            // Create floating button
            const widgetContainer = document.createElement('div');
            widgetContainer.id = 'binaapp-widget';
            widgetContainer.innerHTML = `
                <button id="binaapp-order-btn">
                    <span>🛵</span>
                    <span>${this.t('orderNow')}</span>
                    <span class="binaapp-cart-badge" id="binaapp-cart-count" style="display:none;">0</span>
                </button>
            `;

            // Create modal
            const modal = document.createElement('div');
            modal.id = 'binaapp-modal';
            modal.innerHTML = `
                <div class="binaapp-modal-content">
                    <div class="binaapp-modal-header">
                        <h2 id="binaapp-modal-title">${this.t('orderFood')}</h2>
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
                // Load zones
                const zonesRes = await fetch(`${this.config.apiUrl}/delivery/zones/${this.config.websiteId}`);
                const zonesData = await zonesRes.json();
                this.state.zones = zonesData.zones;

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

            switch(view) {
                case 'menu':
                    title.textContent = this.t('orderFood');
                    body.innerHTML = this.renderMenu();
                    break;
                case 'cart':
                    title.textContent = this.t('yourCart');
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

        // Render menu view
        renderMenu: function() {
            const items = this.state.menu.items;

            if (!items || items.length === 0) {
                return `<div class="binaapp-cart-empty">${this.t('noMenuAvailable')}</div>`;
            }

            let html = '<div class="binaapp-menu-grid">';

            items.forEach(item => {
                html += `
                    <div class="binaapp-menu-item" data-item-id="${item.id}">
                        <img src="${item.image_url || 'https://via.placeholder.com/300x180?text=No+Image'}" alt="${item.name}">
                        <div class="binaapp-menu-item-content">
                            <div class="binaapp-menu-item-name">${item.name}</div>
                            <div class="binaapp-menu-item-desc">${item.description || ''}</div>
                            <div class="binaapp-menu-item-price">RM ${parseFloat(item.price).toFixed(2)}</div>
                            <button class="binaapp-add-to-cart-btn" onclick="BinaAppDelivery.addToCart('${item.id}')">
                                ${this.t('addToCart')}
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

        // Render cart view
        renderCart: function() {
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

                html += `
                    <div class="binaapp-cart-item">
                        <div>
                            <strong>${cartItem.name}</strong><br>
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
            const zones = this.state.zones;

            let html = '<form id="binaapp-checkout-form">';

            // Zone selection
            html += `
                <div class="binaapp-form-group">
                    <label class="binaapp-form-label">${this.t('deliveryZone')}</label>
                    <select class="binaapp-form-select" name="zone" required>
                        <option value="">${this.t('selectZone')}</option>
            `;

            zones.forEach(zone => {
                html += `<option value="${zone.id}" data-fee="${zone.delivery_fee}">
                    ${zone.zone_name} - RM ${parseFloat(zone.delivery_fee).toFixed(2)}
                </option>`;
            });

            html += `
                    </select>
                </div>

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

            const existingIndex = this.state.cart.findIndex(c => c.id === itemId);

            if (existingIndex >= 0) {
                this.state.cart[existingIndex].quantity++;
            } else {
                this.state.cart.push({
                    id: item.id,
                    name: item.name,
                    price: parseFloat(item.price),
                    quantity: 1
                });
            }

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
                const orderData = {
                    website_id: this.config.websiteId,
                    customer_name: formData.get('customer_name'),
                    customer_phone: formData.get('customer_phone'),
                    customer_email: formData.get('customer_email'),
                    delivery_address: formData.get('delivery_address'),
                    delivery_notes: formData.get('delivery_notes'),
                    delivery_zone_id: formData.get('zone'),
                    payment_method: 'cod',
                    items: this.state.cart.map(item => ({
                        menu_item_id: item.id,
                        quantity: item.quantity
                    }))
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
            // Simple alert for MVP, can be enhanced with toast notifications
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
                    loadingOrderStatus: 'Memuatkan status pesanan...'
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
                    loadingOrderStatus: 'Loading order status...'
                }
            };

            const lang = this.config.language;
            return translations[lang]?.[key] || translations.en[key] || key;
        }
    };
})();
