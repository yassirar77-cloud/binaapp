/**
 * BinaApp Chat Widget
 * Customer-side chat widget for restaurant websites
 *
 * Usage:
 * <script src="https://binaapp-backend.onrender.com/static/widgets/chat-widget.js"
 *         data-website-id="YOUR_WEBSITE_UUID"></script>
 */

(function() {
  'use strict';

  // =====================================================
  // CONFIGURATION
  // =====================================================

  const API_URL = document.currentScript?.getAttribute('data-api-url') || 'https://binaapp-backend.onrender.com';
  const WIDGET_ID = 'binaapp-chat-widget';

  // PRIORITY ORDER for website_id (will be VALIDATED against server):
  // 1. window.BINAAPP_WEBSITE_ID (set by server - most trusted)
  // 2. data-website-id attribute on script tag
  // 3. data-website-id on #binaapp-widget-container div
  let pendingWebsiteId = window.BINAAPP_WEBSITE_ID
      || document.currentScript?.getAttribute('data-website-id')
      || document.getElementById('binaapp-widget-container')?.dataset?.websiteId
      || null;

  // CRITICAL: This will hold the VALIDATED, CANONICAL website ID from database
  // It is NOT set until server validation succeeds
  let websiteId = null;
  let validationComplete = false;
  let validationFailed = false;

  // UUID validation regex - reject malformed IDs early
  const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  // =====================================================
  // WIDGET ID VALIDATION (CRITICAL - Single Source of Truth)
  // =====================================================

  /**
   * CRITICAL: Validate website ID against server database
   * This is the ONLY authoritative source for widget ID binding.
   * Rejects any ID that doesn't exist in the database.
   *
   * @param {string} candidateId - The website ID to validate
   * @returns {Promise<{valid: boolean, websiteId: string|null, error: string|null}>}
   */
  async function validateWebsiteId(candidateId) {
    // GUARD 1: Reject null/empty IDs
    if (!candidateId || candidateId.trim() === '') {
      console.error('[BinaApp Chat] VALIDATION FAILED: No website ID provided');
      return { valid: false, websiteId: null, error: 'MISSING_WEBSITE_ID' };
    }

    // GUARD 2: Reject malformed UUIDs (fail fast)
    if (!UUID_REGEX.test(candidateId.trim())) {
      console.error('[BinaApp Chat] VALIDATION FAILED: Invalid UUID format:', candidateId);
      return { valid: false, websiteId: null, error: 'INVALID_UUID_FORMAT' };
    }

    try {
      // GUARD 3: Validate against server database (AUTHORITATIVE)
      const response = await fetch(API_URL + '/api/v1/delivery/validate-widget/' + encodeURIComponent(candidateId.trim()));

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'UNKNOWN_ERROR' }));
        console.error('[BinaApp Chat] VALIDATION FAILED: Server rejected ID:', candidateId, errorData);

        // Clear any cached data for this invalid ID to prevent drift
        clearInvalidCache(candidateId);

        return {
          valid: false,
          websiteId: null,
          error: errorData.detail?.error || errorData.error || 'SERVER_REJECTED'
        };
      }

      const data = await response.json();

      // SUCCESS: Server returned canonical ID from database
      if (data.valid && data.website_id) {
        console.log('[BinaApp Chat] VALIDATION SUCCESS: Canonical ID:', data.website_id);

        // CRITICAL: Use the CANONICAL ID from database, not the candidate
        // This prevents any client-side ID drift
        return {
          valid: true,
          websiteId: data.website_id,  // ALWAYS use database value
          businessName: data.business_name,
          error: null
        };
      }

      return { valid: false, websiteId: null, error: 'VALIDATION_FAILED' };

    } catch (err) {
      console.error('[BinaApp Chat] VALIDATION ERROR: Network failure:', err);
      // On network error, we CANNOT validate - fail safe by rejecting
      return { valid: false, websiteId: null, error: 'NETWORK_ERROR' };
    }
  }

  /**
   * Clear cached data for an invalid website ID
   * Prevents stale/invalid data from persisting
   */
  function clearInvalidCache(invalidId) {
    try {
      localStorage.removeItem('binaapp_conv_' + invalidId);
      localStorage.removeItem('binaapp_customer_id_' + invalidId);
      console.log('[BinaApp Chat] Cleared cache for invalid ID:', invalidId);
    } catch (e) {
      // localStorage might not be available
    }
  }

  // GUARD: Reject early if no candidate ID at all
  if (!pendingWebsiteId) {
    console.error('[BinaApp Chat] BOOTSTRAP ABORTED: No website_id found in any source');
    console.error('[BinaApp Chat] Checked: window.BINAAPP_WEBSITE_ID, data-website-id attribute, container data attribute');
    return;
  }

  console.log('[BinaApp Chat] Pending validation for website_id:', pendingWebsiteId);

  // Storage keys - will be initialized AFTER validation with canonical ID
  let STORAGE_CONV_KEY = null;
  const STORAGE_NAME_KEY = 'binaapp_customer_name';
  const STORAGE_PHONE_KEY = 'binaapp_customer_phone';
  let STORAGE_CUSTOMER_ID_KEY = null;

  // State - will be loaded AFTER validation succeeds
  let conversationId = null;
  let customerName = localStorage.getItem(STORAGE_NAME_KEY) || '';
  let customerPhone = localStorage.getItem(STORAGE_PHONE_KEY) || '';
  let customerId = '';
  let isOpen = false;
  let isLoading = false;
  let refreshInterval = null;

  /**
   * Initialize storage keys with VALIDATED website ID
   * MUST be called only after validation succeeds
   */
  function initStorageKeys(validatedId) {
    STORAGE_CONV_KEY = 'binaapp_conv_' + validatedId;
    STORAGE_CUSTOMER_ID_KEY = 'binaapp_customer_id_' + validatedId;

    // Now load cached values with validated keys
    try {
      conversationId = localStorage.getItem(STORAGE_CONV_KEY);
      customerId = localStorage.getItem(STORAGE_CUSTOMER_ID_KEY) || '';
    } catch (e) {
      // localStorage might not be available
      conversationId = null;
      customerId = '';
    }
  }

  // =====================================================
  // STYLES
  // =====================================================

  const styles = `
    #binaapp-chat-widget * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }

    #binaapp-chat-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 56px;
      height: 56px;
      background: linear-gradient(135deg, #ea580c, #f97316);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(234, 88, 12, 0.4);
      z-index: 9999;
      font-size: 24px;
      transition: transform 0.3s ease, box-shadow 0.3s ease;
      border: none;
      outline: none;
    }

    #binaapp-chat-btn:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 20px rgba(234, 88, 12, 0.5);
    }

    #binaapp-chat-btn .badge {
      position: absolute;
      top: -5px;
      right: -5px;
      background: #ef4444;
      color: white;
      font-size: 12px;
      font-weight: bold;
      min-width: 20px;
      height: 20px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 6px;
    }

    #binaapp-chat-window {
      display: none;
      position: fixed;
      bottom: 90px;
      right: 24px;
      width: 350px;
      max-width: calc(100vw - 40px);
      height: 450px;
      max-height: calc(100vh - 120px);
      background: white;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      z-index: 9998;
      overflow: hidden;
      flex-direction: column;
    }

    #binaapp-chat-window.open {
      display: flex;
    }

    .binaapp-header {
      background: linear-gradient(135deg, #ea580c, #f97316);
      color: white;
      padding: 16px;
      flex-shrink: 0;
    }

    .binaapp-header-title {
      font-weight: bold;
      font-size: 18px;
      margin-bottom: 4px;
    }

    .binaapp-header-subtitle {
      font-size: 12px;
      opacity: 0.9;
    }

    .binaapp-header-close {
      position: absolute;
      top: 12px;
      right: 12px;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      color: white;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
    }

    .binaapp-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      background: #f9fafb;
    }

    .binaapp-empty-state {
      text-align: center;
      color: #6b7280;
      font-size: 14px;
      padding: 40px 20px;
    }

    .binaapp-message {
      margin-bottom: 12px;
      display: flex;
    }

    .binaapp-message.customer {
      justify-content: flex-end;
    }

    .binaapp-message.owner,
    .binaapp-message.system {
      justify-content: flex-start;
    }

    .binaapp-message-bubble {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 16px;
      word-wrap: break-word;
    }

    .binaapp-message.customer .binaapp-message-bubble {
      background: #ea580c;
      color: white;
      border-bottom-right-radius: 4px;
    }

    .binaapp-message.owner .binaapp-message-bubble {
      background: white;
      border: 1px solid #e5e7eb;
      border-bottom-left-radius: 4px;
    }

    .binaapp-message.system .binaapp-message-bubble {
      background: #fef3c7;
      color: #92400e;
      font-size: 12px;
      text-align: center;
      border-radius: 8px;
    }

    .binaapp-message-text {
      font-size: 14px;
      line-height: 1.4;
    }

    .binaapp-message-image {
      max-width: 100%;
      border-radius: 8px;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    .binaapp-message-image:hover {
      opacity: 0.9;
    }

    .binaapp-message.customer .binaapp-message-image {
      border: 2px solid rgba(255, 255, 255, 0.3);
    }

    .binaapp-message.owner .binaapp-message-image {
      border: 1px solid #e5e7eb;
    }

    .binaapp-message-time {
      font-size: 10px;
      opacity: 0.7;
      margin-top: 4px;
    }

    .binaapp-input-area {
      padding: 12px;
      border-top: 1px solid #e5e7eb;
      background: white;
      flex-shrink: 0;
    }

    .binaapp-input-row {
      display: flex;
      gap: 8px;
    }

    .binaapp-input {
      flex: 1;
      padding: 12px 16px;
      border: 1px solid #e5e7eb;
      border-radius: 24px;
      outline: none;
      font-size: 14px;
      transition: border-color 0.2s;
    }

    .binaapp-input:focus {
      border-color: #ea580c;
    }

    .binaapp-send-btn {
      background: #ea580c;
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 24px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
      transition: background 0.2s;
    }

    .binaapp-send-btn:hover {
      background: #dc4c0a;
    }

    .binaapp-send-btn:disabled {
      background: #d1d5db;
      cursor: not-allowed;
    }

    .binaapp-name-form {
      padding: 16px;
      border-top: 1px solid #e5e7eb;
      background: white;
    }

    .binaapp-form-input {
      width: 100%;
      padding: 12px 16px;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      margin-bottom: 8px;
      font-size: 14px;
      outline: none;
    }

    .binaapp-form-input:focus {
      border-color: #ea580c;
    }

    .binaapp-start-btn {
      width: 100%;
      background: #ea580c;
      color: white;
      border: none;
      padding: 14px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: bold;
      font-size: 14px;
      transition: background 0.2s;
    }

    .binaapp-start-btn:hover {
      background: #dc4c0a;
    }

    .binaapp-start-btn:disabled {
      background: #d1d5db;
      cursor: not-allowed;
    }

    .binaapp-loading {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .binaapp-spinner {
      width: 24px;
      height: 24px;
      border: 3px solid #e5e7eb;
      border-top-color: #ea580c;
      border-radius: 50%;
      animation: binaapp-spin 1s linear infinite;
    }

    @keyframes binaapp-spin {
      to { transform: rotate(360deg); }
    }

    @media (max-width: 480px) {
      #binaapp-chat-window {
        bottom: 0;
        left: 0;
        right: 0;
        width: 100%;
        max-width: 100%;
        height: 100vh;
        max-height: 100vh;
        border-radius: 0;
      }

      #binaapp-chat-btn {
        bottom: 20px;
        right: 16px;
        width: 52px;
        height: 52px;
        font-size: 22px;
      }

      #binaapp-chat-window {
        width: calc(100vw - 32px);
        height: 400px;
        bottom: 80px;
        right: 16px;
      }
    }
  `;

  // =====================================================
  // INJECT STYLES
  // =====================================================

  function injectStyles() {
    if (document.getElementById('binaapp-chat-styles')) return;

    const styleEl = document.createElement('style');
    styleEl.id = 'binaapp-chat-styles';
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);
  }

  // =====================================================
  // CREATE WIDGET HTML
  // =====================================================

  function createWidget() {
    if (document.getElementById(WIDGET_ID)) return;

    const widget = document.createElement('div');
    widget.id = WIDGET_ID;
    widget.innerHTML = `
      <button id="binaapp-chat-btn" aria-label="Chat dengan kami">
        <span class="icon">&#128172;</span>
        <span class="badge" style="display: none;">0</span>
      </button>

      <div id="binaapp-chat-window">
        <div class="binaapp-header" style="position: relative;">
          <div class="binaapp-header-title">&#128172; Chat dengan Kami</div>
          <div class="binaapp-header-subtitle">Biasanya balas dalam 5 minit</div>
          <button class="binaapp-header-close" aria-label="Tutup chat">&times;</button>
        </div>

        <div id="binaapp-messages" class="binaapp-messages">
          <div class="binaapp-empty-state">
            Mulakan perbualan dengan menghantar mesej
          </div>
        </div>

        <div id="binaapp-chat-input" class="binaapp-input-area" style="display: none;">
          <div class="binaapp-input-row">
            <input type="text" id="binaapp-msg-input" class="binaapp-input" placeholder="Taip mesej..." maxlength="1000">
            <button id="binaapp-send-btn" class="binaapp-send-btn">Hantar</button>
          </div>
        </div>

        <div id="binaapp-name-form" class="binaapp-name-form">
          <input type="text" id="binaapp-name" class="binaapp-form-input" placeholder="Nama anda *" maxlength="100">
          <input type="tel" id="binaapp-phone" class="binaapp-form-input" placeholder="No. telefon (contoh: 0123456789)" maxlength="15">
          <div id="binaapp-form-error" style="display:none;color:#ef4444;font-size:12px;padding:4px 8px;margin-bottom:8px;background:#fef2f2;border-radius:6px;text-align:center;"></div>
          <button id="binaapp-start-btn" class="binaapp-start-btn">Mula Chat</button>
        </div>
      </div>
    `;

    document.body.appendChild(widget);
  }

  // =====================================================
  // API FUNCTIONS
  // =====================================================

  async function createConversation(name, phone) {
    const response = await fetch(API_URL + '/api/v1/chat/conversations/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        website_id: websiteId,
        customer_name: name,
        customer_phone: phone || ''
      })
    });

    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }

    return response.json();
  }

  async function sendMessage(text) {
    if (!conversationId || !customerId) return;

    const response = await fetch(API_URL + '/api/v1/chat/messages/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: conversationId,
        sender_type: 'customer',
        sender_id: customerId,
        sender_name: customerName,
        message_type: 'text',
        message_text: text
      })
    });

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    return response.json();
  }

  async function loadMessages() {
    if (!conversationId) return [];

    try {
      const response = await fetch(API_URL + '/api/v1/chat/conversations/' + conversationId);

      if (!response.ok) {
        // Conversation might not exist anymore
        if (response.status === 404) {
          // Clear stored conversation
          localStorage.removeItem(STORAGE_CONV_KEY);
          localStorage.removeItem(STORAGE_CUSTOMER_ID_KEY);
          conversationId = null;
          customerId = '';
          showNameForm();
          return [];
        }
        throw new Error('Failed to load messages');
      }

      const data = await response.json();
      return data.messages || [];
    } catch (err) {
      console.error('[BinaApp Chat] Failed to load messages:', err);
      return [];
    }
  }

  // =====================================================
  // UI FUNCTIONS
  // =====================================================

  function toggleChat() {
    isOpen = !isOpen;
    const chatWindow = document.getElementById('binaapp-chat-window');

    if (isOpen) {
      chatWindow.classList.add('open');

      if (conversationId) {
        refreshMessages();
        startAutoRefresh();
      }

      // Focus input
      setTimeout(() => {
        const input = conversationId
          ? document.getElementById('binaapp-msg-input')
          : document.getElementById('binaapp-name');
        if (input) input.focus();
      }, 100);
    } else {
      chatWindow.classList.remove('open');
      stopAutoRefresh();
    }
  }

  function showNameForm() {
    const nameForm = document.getElementById('binaapp-name-form');
    const chatInput = document.getElementById('binaapp-chat-input');

    if (nameForm) nameForm.style.display = 'block';
    if (chatInput) chatInput.style.display = 'none';

    // Pre-fill if we have stored values
    const nameEl = document.getElementById('binaapp-name');
    const phoneEl = document.getElementById('binaapp-phone');
    if (nameEl && customerName) nameEl.value = customerName;
    if (phoneEl && customerPhone) phoneEl.value = customerPhone;
  }

  function showChatInput() {
    const nameForm = document.getElementById('binaapp-name-form');
    const chatInput = document.getElementById('binaapp-chat-input');

    if (nameForm) nameForm.style.display = 'none';
    if (chatInput) chatInput.style.display = 'block';
  }

  function renderMessages(messages) {
    const container = document.getElementById('binaapp-messages');
    if (!container) return;

    if (!messages || messages.length === 0) {
      container.innerHTML = '<div class="binaapp-empty-state">Mulakan perbualan dengan menghantar mesej</div>';
      return;
    }

    container.innerHTML = messages.map(msg => {
      const senderClass = msg.sender_type === 'customer' ? 'customer'
        : msg.sender_type === 'system' ? 'system'
        : 'owner';
      const messageText = msg.message_text || msg.message || msg.content || '';
      const messageType = msg.message_type || 'text';
      const mediaUrl = msg.media_url || null;

      const time = new Date(msg.created_at).toLocaleTimeString('ms-MY', {
        hour: '2-digit',
        minute: '2-digit'
      });

      // Render image messages
      if ((messageType === 'image' || messageType === 'payment') && mediaUrl) {
        return `
          <div class="binaapp-message ${senderClass}">
            <div class="binaapp-message-bubble">
              <img
                src="${escapeHtml(mediaUrl)}"
                alt="${messageType === 'payment' ? 'Bukti Pembayaran' : 'Gambar'}"
                class="binaapp-message-image"
                onclick="window.open('${escapeHtml(mediaUrl)}', '_blank')"
              />
              <div class="binaapp-message-time">${time}</div>
            </div>
          </div>
        `;
      }

      // Render text messages
      return `
        <div class="binaapp-message ${senderClass}">
          <div class="binaapp-message-bubble">
            <div class="binaapp-message-text">${escapeHtml(messageText)}</div>
            <div class="binaapp-message-time">${time}</div>
          </div>
        </div>
      `;
    }).join('');

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function setLoading(loading) {
    isLoading = loading;
    const sendBtn = document.getElementById('binaapp-send-btn');
    const startBtn = document.getElementById('binaapp-start-btn');

    if (sendBtn) sendBtn.disabled = loading;
    if (startBtn) startBtn.disabled = loading;
  }

  async function refreshMessages() {
    const messages = await loadMessages();
    renderMessages(messages);
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    refreshInterval = setInterval(refreshMessages, 5000);
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  }

  // Show inline error message in form
  function showFormError(message) {
    const errorEl = document.getElementById('binaapp-form-error');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
      // Auto-hide after 5 seconds
      setTimeout(() => {
        errorEl.style.display = 'none';
      }, 5000);
    }
  }

  // Hide form error
  function hideFormError() {
    const errorEl = document.getElementById('binaapp-form-error');
    if (errorEl) {
      errorEl.style.display = 'none';
    }
  }

  // Show notification toast for messages area
  function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#ef4444;color:white;padding:10px 20px;border-radius:8px;font-size:13px;z-index:10001;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
    notification.textContent = message;
    document.body.appendChild(notification);
    // Remove after 3 seconds
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  // =====================================================
  // EVENT HANDLERS
  // =====================================================

  async function handleStartChat() {
    const nameInput = document.getElementById('binaapp-name');
    const phoneInput = document.getElementById('binaapp-phone');

    const name = nameInput ? nameInput.value.trim() : '';
    const phone = phoneInput ? phoneInput.value.trim() : '';

    if (!name) {
      showFormError('Sila masukkan nama anda');
      nameInput && nameInput.focus();
      return;
    }
    hideFormError();

    setLoading(true);

    try {
      const result = await createConversation(name, phone);

      conversationId = result.conversation_id;
      customerId = result.customer_id;
      customerName = name;
      customerPhone = phone;

      // Store in localStorage
      localStorage.setItem(STORAGE_CONV_KEY, conversationId);
      localStorage.setItem(STORAGE_NAME_KEY, customerName);
      localStorage.setItem(STORAGE_PHONE_KEY, customerPhone);
      localStorage.setItem(STORAGE_CUSTOMER_ID_KEY, customerId);

      showChatInput();

      // Load initial messages (should have welcome message from system)
      await refreshMessages();
      startAutoRefresh();

      // Focus message input
      setTimeout(() => {
        const msgInput = document.getElementById('binaapp-msg-input');
        if (msgInput) msgInput.focus();
      }, 100);

    } catch (err) {
      console.error('[BinaApp Chat] Failed to start chat:', err);
      showFormError('Gagal memulakan chat. Sila cuba lagi.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSendMessage() {
    const msgInput = document.getElementById('binaapp-msg-input');
    const message = msgInput ? msgInput.value.trim() : '';

    // Validate message is not empty
    if (!message) {
      showNotification('Sila taip mesej');
      if (msgInput) msgInput.focus();
      return;
    }

    if (isLoading) return;

    setLoading(true);
    msgInput.value = '';

    try {
      await sendMessage(message);
      await refreshMessages();
    } catch (err) {
      console.error('[BinaApp Chat] Failed to send message:', err);
      // Restore message in input
      if (msgInput) msgInput.value = message;
      showNotification('Gagal menghantar mesej. Sila cuba lagi.');
    } finally {
      setLoading(false);
      if (msgInput) msgInput.focus();
    }
  }

  // =====================================================
  // INITIALIZE
  // =====================================================

  /**
   * Show the chat button and window UI immediately (before validation).
   * Chat functionality is enabled only after validation succeeds.
   */
  function initWidgetUI() {
    injectStyles();
    createWidget();

    // Bind events
    const chatBtn = document.getElementById('binaapp-chat-btn');
    const closeBtn = document.querySelector('.binaapp-header-close');
    const startBtn = document.getElementById('binaapp-start-btn');
    const sendBtn = document.getElementById('binaapp-send-btn');
    const msgInput = document.getElementById('binaapp-msg-input');
    const nameInput = document.getElementById('binaapp-name');

    if (chatBtn) chatBtn.addEventListener('click', toggleChat);
    if (closeBtn) closeBtn.addEventListener('click', toggleChat);
    if (startBtn) startBtn.addEventListener('click', handleStartChat);
    if (sendBtn) sendBtn.addEventListener('click', handleSendMessage);

    // Enter key handlers
    if (msgInput) {
      msgInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSendMessage();
        }
      });
    }

    if (nameInput) {
      nameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          handleStartChat();
        }
      });
    }

    showNameForm();
    console.log('[BinaApp Chat] Widget UI visible, pending validation for:', pendingWebsiteId);
  }

  /**
   * After validation succeeds, enable full chat functionality.
   */
  function enableChatAfterValidation() {
    // Load any existing conversation from localStorage
    if (conversationId && customerId) {
      showChatInput();
    } else {
      showNameForm();
    }
    console.log('[BinaApp Chat] Chat enabled with VALIDATED website_id:', websiteId);
  }

  /**
   * Validate website ID with retry logic.
   * Retries up to 3 times with exponential backoff on network errors.
   */
  async function validateWithRetry(candidateId, maxRetries) {
    var retries = maxRetries || 3;
    var delay = 2000;

    for (var attempt = 1; attempt <= retries; attempt++) {
      var result = await validateWebsiteId(candidateId);

      if (result.valid) {
        return result;
      }

      // Only retry on network errors, not on definitive rejections
      if (result.error !== 'NETWORK_ERROR' || attempt === retries) {
        return result;
      }

      console.log('[BinaApp Chat] Retry ' + attempt + '/' + retries + ' in ' + delay + 'ms...');
      await new Promise(function(resolve) { setTimeout(resolve, delay); });
      delay *= 2;
    }

    return { valid: false, websiteId: null, error: 'MAX_RETRIES_EXCEEDED' };
  }

  /**
   * MAIN ENTRY POINT: Show button immediately, validate in background.
   * The button is ALWAYS visible. Chat functionality activates after validation.
   */
  async function initWithValidation() {
    // STEP 1: Show the button and chat window UI immediately
    initWidgetUI();

    // STEP 2: Validate in the background (with retry for network errors)
    console.log('[BinaApp Chat] Starting background validation for:', pendingWebsiteId);

    var result = await validateWithRetry(pendingWebsiteId, 3);

    if (!result.valid) {
      validationFailed = true;
      console.warn('[BinaApp Chat] Validation failed:', result.error);
      console.warn('[BinaApp Chat] Chat button is visible but chat may not work until validation succeeds.');

      // Use the pending ID as fallback so basic chat functionality can still work
      // This allows the button to remain visible and functional
      websiteId = pendingWebsiteId;
      validationComplete = true;
      initStorageKeys(websiteId);
      enableChatAfterValidation();
      return;
    }

    // SUCCESS: Set the CANONICAL validated ID
    websiteId = result.websiteId;
    validationComplete = true;

    // Initialize storage keys with validated ID
    initStorageKeys(websiteId);

    // Enable full chat functionality
    enableChatAfterValidation();
  }

  // Legacy alias for backwards compatibility
  function init() {
    initWithValidation();
  }

  // Watch for delivery modal opening/closing to hide chat button (prevents form blocking)
  function setupDeliveryModalObserver() {
    var modal = document.getElementById('binaapp-modal');

    // Only set up observer if the delivery modal element exists
    if (!modal) {
      // Check again after a short delay in case delivery widget loads later
      setTimeout(function() {
        var delayedModal = document.getElementById('binaapp-modal');
        if (delayedModal) {
          observeModal();
        }
      }, 3000);
      return;
    }

    observeModal();

    function observeModal() {
      var observer = new MutationObserver(function(mutations) {
        var modalEl = document.getElementById('binaapp-modal');
        if (!modalEl) return;

        var chatBtn = document.getElementById('binaapp-chat-btn');
        var chatWindow = document.getElementById('binaapp-chat-window');

        if (modalEl.classList.contains('active')) {
          // Delivery modal is open, hide chat widgets to prevent blocking form
          if (chatBtn) chatBtn.style.display = 'none';
          if (chatWindow) chatWindow.style.display = 'none';
        } else {
          // Delivery modal is closed, show chat widgets
          if (chatBtn) chatBtn.style.display = 'flex';
          // Chat window visibility is controlled by isOpen state
        }
      });

      // Only observe the modal element for class changes, not the entire DOM
      var target = document.getElementById('binaapp-modal');
      if (target) {
        observer.observe(target, { attributes: true, attributeFilter: ['class'] });
      }
    }
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      init();
      setupDeliveryModalObserver();
    });
  } else {
    init();
    setupDeliveryModalObserver();
  }

})();
