let cart = [];
let currentPaymentMethod = 'cash';
let mpesaConfirmed = false;
let customersList = [];
let selectedCustomer = null;

// Format currency
const formatMoney = (val) => Number(val).toFixed(2);

// Focus barcode
document.addEventListener('DOMContentLoaded', () => {
    const barcodeInput = document.getElementById('barcode-input');
    if (barcodeInput) barcodeInput.focus();
    
    barcodeInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            const code = barcodeInput.value.trim();
            if (code) {
                await fetchProduct(code);
                barcodeInput.value = '';
            }
        }
    });

    document.getElementById('cash-tendered').addEventListener('input', updateTotals);

    const digitalReceiptToggle = document.getElementById('send-digital-receipt');
    const receiptPhoneInput = document.getElementById('receipt-phone');
    if (digitalReceiptToggle) {
        digitalReceiptToggle.addEventListener('change', (e) => {
            if (e.target.checked) {
                receiptPhoneInput.classList.remove('hidden');
                receiptPhoneInput.focus();
            } else {
                receiptPhoneInput.classList.add('hidden');
            }
        });
    }

    // Load customers list
    fetchCustomers();

    // Customer select change listener
    const customerSelect = document.getElementById('customer-select');
    if (customerSelect) {
        customerSelect.addEventListener('change', (e) => {
            onCustomerSelectChanged(e.target.value);
        });
    }

    // Load parked sales on start
    updateParkedSalesUI();
});

// Fetch product via API
async function fetchProduct(barcode) {
    setStatus("SEARCHING PRODUCT...", "text-indigo-400");
    try {
        const res = await fetch(`${CONFIG.productsUrl}by_barcode/?barcode=${encodeURIComponent(barcode)}`);
        const data = await res.json();
        
        if (data.length > 0) {
            const product = data[0];
            if (product.current_stock > 0) {
                addToCart(product);
                setStatus("PRODUCT ADDED.", "text-emerald-400");
            } else {
                setStatus(`OUT OF STOCK. <button onclick="checkGlobalStock(${product.id})" class="underline text-indigo-400 ml-2 font-bold">CHECK BRANCHES</button>`, "text-rose-400", 6000);
            }
        } else {
            setStatus("PRODUCT NOT FOUND.", "text-rose-400");
        }
    } catch (err) {
        setStatus("OFFLINE — PRODUCT CACHE NEEDED.", "text-amber-400");
        console.error("Fetch product error:", err);
    }
}

async function checkGlobalStock(productId) {
    try {
        setStatus("LOOKING UP GLOBAL STOCK...", "text-indigo-400");
        const res = await fetch(`${CONFIG.productsUrl}${productId}/global-stock/`);
        const data = await res.json();
        
        document.getElementById('stock-modal-product').textContent = `${data.product_name} (${data.sku})`;
        const body = document.getElementById('stock-modal-body');
        body.innerHTML = '';
        
        if (data.branches.length === 0) {
            body.innerHTML = '<div class="text-xs text-slate-500 italic">No stock found in any other branch.</div>';
        } else {
            data.branches.forEach(b => {
                body.innerHTML += `
                    <div class="flex justify-between items-center bg-slate-900/50 p-2 rounded border border-slate-800">
                        <span class="text-xs text-slate-300 font-bold">${b.branch__name}</span>
                        <span class="text-xs text-emerald-400 font-mono font-bold">${b.total_stock} IN STOCK</span>
                    </div>
                `;
            });
        }
        
        document.getElementById('stock-modal').classList.remove('hidden');
    } catch (err) {
        console.error("Global stock fetch failed:", err);
        setStatus("FAILED TO FETCH GLOBAL STOCK.", "text-rose-400");
    }
}

function closeStockModal() {
    document.getElementById('stock-modal').classList.add('hidden');
}


// Set status message
function setStatus(msg, colorClass = "text-slate-500", timeout = 3000) {
    const el = document.getElementById('status-message');
    el.innerHTML = msg;
    el.className = `text-[10px] font-mono ${colorClass}`;
    setTimeout(() => {
        if (el.innerHTML === msg) {
            el.textContent = "AWAITING INPUT...";
            el.className = "text-[10px] text-slate-500 font-mono";
        }
    }, timeout);
}

// Add to cart
function addToCart(product) {
    const existing = cart.find(i => i.product.id === product.id);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            product: product,
            quantity: 1,
            unit_price: Number(product.selling_price),
            discount_amount: 0
        });
    }
    renderCart();
}

// Render cart
function renderCart() {
    const tbody = document.getElementById('cart-body');
    tbody.innerHTML = '';
    
    let subtotal = 0;
    let tax = 0;
    
    cart.forEach((item, index) => {
        const lineTotal = item.quantity * item.unit_price;
        subtotal += lineTotal;
        // Simple 16% inclusive for demo rendering
        if (item.product.tax_type === 'V') {
            tax += lineTotal - (lineTotal / 1.16);
        }

        const tr = document.createElement('tr');
        tr.className = index % 2 === 0 ? "" : "bg-slate-800/20";
        tr.innerHTML = `
            <td class="p-2 pl-4 text-indigo-400 truncate max-w-[200px]" title="${item.product.name}">${item.product.name}</td>
            <td class="p-2 text-center">
                <input type="number" min="1" value="${item.quantity}" onchange="updateItemQty(${index}, this.value)" class="w-12 bg-slate-900 border border-slate-700 text-white text-center rounded p-1 text-[11px] focus:outline-none focus:border-indigo-500 font-mono">
            </td>
            <td class="p-2 text-right text-slate-400">${formatMoney(item.unit_price)}</td>
            <td class="p-2 text-right pr-4 text-white">${formatMoney(lineTotal)}</td>
            <td class="p-2 text-center">
                <button onclick="removeFromCart(${index})" class="text-rose-500 hover:text-rose-400 font-bold px-1 py-0.5 cursor-pointer text-xs transition-colors">&times;</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('cart-subtotal').textContent = formatMoney(subtotal);
    document.getElementById('cart-tax').textContent = formatMoney(tax);
    document.getElementById('cart-discount').textContent = formatMoney(0);
    document.getElementById('cart-total').textContent = formatMoney(subtotal);
    
    updateTotals();
}

// Clear cart
function clearCart() {
    cart = [];
    renderCart();
    setStatus("CART CLEARED.", "text-amber-400");
}

// Payment UI Switch
function switchPayment(method) {
    currentPaymentMethod = method;
    document.querySelectorAll('.payment-tab').forEach(el => {
        el.classList.remove('border-indigo-500', 'text-indigo-400');
        el.classList.add('border-transparent', 'text-slate-500');
    });
    
    const activeTab = Array.from(document.querySelectorAll('.payment-tab'))
        .find(el => el.textContent.toLowerCase() === method.replace('-', ''));
    if (activeTab) {
        activeTab.classList.remove('border-transparent', 'text-slate-500');
        activeTab.classList.add('border-indigo-500', 'text-indigo-400');
    }

    document.querySelectorAll('.payment-view').forEach(el => el.classList.add('hidden'));
    document.getElementById(`payment-${method}`).classList.remove('hidden');
    
    updateTotals();
}

// Update Totals
function updateTotals() {
    const total = Number(document.getElementById('cart-total').textContent);
    const btn = document.getElementById('btn-complete-sale');
    
    if (cart.length === 0) {
        btn.disabled = true;
        return;
    }

    if (currentPaymentMethod === 'cash') {
        const tendered = Number(document.getElementById('cash-tendered').value || 0);
        const change = tendered - total;
        
        const changeEl = document.getElementById('cash-change');
        changeEl.textContent = formatMoney(Math.max(0, change));
        
        // Active Complete button if exact or more change
        if (tendered >= total) {
            btn.disabled = false;
            changeEl.classList.remove('text-rose-400');
            changeEl.classList.add('text-amber-400');
        } else {
            btn.disabled = true;
            changeEl.classList.remove('text-amber-400');
            changeEl.classList.add('text-rose-400');
        }
    } else if (currentPaymentMethod === 'mpesa') {
        btn.disabled = !mpesaConfirmed;
    } else if (currentPaymentMethod === 'store_credit') {
        if (!selectedCustomer) {
            btn.disabled = true;
            setStatus("SELECT A CUSTOMER FOR CREDIT PURCHASE", "text-rose-400");
        } else if (!selectedCustomer.allow_credit_sales) {
            btn.disabled = true;
            setStatus("CUSTOMER DOES NOT ALLOW CREDIT SALES", "text-rose-400");
        } else {
            const availableCredit = Number(selectedCustomer.credit_limit) - Number(selectedCustomer.current_credit_balance);
            if (total > availableCredit) {
                btn.disabled = true;
                setStatus(`LIMIT EXCEEDED. AVAIL: KES ${formatMoney(availableCredit)}`, "text-rose-400");
            } else {
                btn.disabled = false;
            }
        }
    } else if (currentPaymentMethod === 'points') {
        if (!selectedCustomer) {
            btn.disabled = true;
            setStatus("SELECT A CUSTOMER TO REDEEM POINTS", "text-rose-400");
        } else if (selectedCustomer.loyalty_points < total) {
            btn.disabled = true;
            setStatus(`INSUFFICIENT POINTS. HAVE ${selectedCustomer.loyalty_points} PTS`, "text-rose-400");
        } else {
            btn.disabled = false;
        }
    } else {
        // Card simple active
        btn.disabled = false;
    }
}

// M-Pesa Stk push integration
async function sendStkPush() {
    const phone = document.getElementById('mpesa-phone').value;
    if (!phone) {
        setStatus("ENTER PHONE NUMBER", "text-rose-400");
        return;
    }
    
    const total = Number(document.getElementById('cart-total').textContent);
    if (total <= 0) {
        setStatus("CART IS EMPTY", "text-rose-400");
        return;
    }

    const ref = cart.length > 0 ? cart[0].product.barcode : "POSPay";
    
    const btn = document.getElementById('btn-stk-push');
    const container = document.getElementById('mpesa-status-container');
    const statusText = document.getElementById('mpesa-status-text');
    
    btn.disabled = true;
    btn.textContent = "SENDING...";
    setStatus("INITIATING STK PUSH...", "text-indigo-400");

    try {
        const res = await fetch(CONFIG.mpesaInitiateUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": CONFIG.csrfToken
            },
            body: JSON.stringify({
                phone: phone,
                amount: total,
                reference: ref
            })
        });
        
        const data = await res.json();
        
        if (data.ResponseCode === "0") {
            btn.classList.add('hidden');
            container.classList.remove('hidden');
            statusText.innerHTML = `
                <div class="mb-2">STK PUSH SENT TO ${phone}</div>
                <div class="text-[10px] text-slate-500 mb-3">Waiting for PIN entry…</div>
                <div class="flex items-center justify-center gap-2">
                    <div class="w-3 h-3 rounded-full bg-indigo-500 animate-pulse"></div>
                    <span class="text-[10px] text-slate-400" id="mpesa-poll-status">Checking payment status…</span>
                </div>
            `;
            setStatus("STK PUSH SENT. AWAITING PIN ENTRY.", "text-emerald-400", 10000);
            
            // Auto-poll Safaricom to detect payment
            pollMpesaStatus(data.CheckoutRequestID);
        } else {
            btn.disabled = false;
            btn.textContent = "SEND STK PUSH";
            setStatus(data.CustomerMessage || "STK PUSH FAILED.", "text-rose-400", 5000);
        }
    } catch (err) {
        console.error("STK push error:", err);
        btn.disabled = false;
        btn.textContent = "SEND STK PUSH";
        setStatus("NETWORK ERROR. TRY AGAIN.", "text-rose-400");
    }
}

let mpesaPollTimer = null;

async function pollMpesaStatus(checkoutRequestId) {
    let attempts = 0;
    const maxAttempts = 10; // ~2 minutes (12s interval, Safaricom allows max 5 req/min)
    
    const poll = async () => {
        attempts++;
        const pollStatus = document.getElementById('mpesa-poll-status');
        
        try {
            const res = await fetch('/api/v1/mpesa/query/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CONFIG.csrfToken
                },
                body: JSON.stringify({ checkout_request_id: checkoutRequestId })
            });
            const data = await res.json();
            
            if (data.paid) {
                // Payment confirmed by Safaricom!
                markMpesaConfirmed();
                setStatus("M-PESA PAYMENT CONFIRMED BY SAFARICOM ✓", "text-emerald-400");
                return; // stop polling
            }
            
            if (data.cancelled) {
                // User cancelled on their phone
                const statusText = document.getElementById('mpesa-status-text');
                statusText.innerHTML = `
                    <div class="text-rose-400 mb-2">PAYMENT CANCELLED BY CUSTOMER</div>
                    <button onclick="resetMpesaUI()" class="px-2 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[10px] font-bold font-sans cursor-pointer">TRY AGAIN</button>
                `;
                setStatus("CUSTOMER CANCELLED M-PESA PAYMENT.", "text-rose-400");
                return;
            }
            
            if (pollStatus) pollStatus.textContent = `Checking… (${attempts}/${maxAttempts})`;
            
        } catch (err) {
            console.warn("Poll error:", err);
        }
        
        if (attempts < maxAttempts) {
            mpesaPollTimer = setTimeout(poll, 12000);
        } else {
            // Timeout — show manual confirm fallback
            const statusText = document.getElementById('mpesa-status-text');
            statusText.innerHTML = `
                <div class="text-amber-400 mb-2">COULD NOT AUTO-DETECT PAYMENT</div>
                <div class="text-[10px] text-slate-500 mb-2">If you received the M-Pesa confirmation SMS:</div>
                <button onclick="markMpesaConfirmed()" class="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold font-sans cursor-pointer">CONFIRM PAYMENT RECEIVED</button>
            `;
        }
    };
    
    // First check after 8 seconds (give user time to enter PIN)
    mpesaPollTimer = setTimeout(poll, 8000);
}

function markMpesaConfirmed() {
    if (mpesaPollTimer) clearTimeout(mpesaPollTimer);
    
    const statusText = document.getElementById('mpesa-status-text');
    const container = document.getElementById('mpesa-status-container');
    
    statusText.textContent = "M-PESA CONFIRMED ✓";
    statusText.classList.remove('text-slate-400');
    statusText.classList.add('text-emerald-400');
    container.classList.replace('bg-slate-900', 'bg-emerald-900/20');
    container.classList.replace('border-slate-700', 'border-emerald-500/50');
    
    mpesaConfirmed = true;
    updateTotals();
}

function resetMpesaUI() {
    if (mpesaPollTimer) clearTimeout(mpesaPollTimer);
    const btn = document.getElementById('btn-stk-push');
    const container = document.getElementById('mpesa-status-container');
    btn.classList.remove('hidden');
    btn.disabled = false;
    btn.textContent = "SEND STK PUSH";
    container.classList.add('hidden');
}

// Generates UUID4
const uuidv4 = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
};

// Complete Sale
async function completeSale() {
    const total = Number(document.getElementById('cart-total').textContent);
    
    // If M-Pesa was already confirmed locally (STK push succeeded + user verified),
    // send 'mpesa-confirmed' so the server records the sale immediately
    // instead of waiting for an unreachable callback.
    let paymentMethod = currentPaymentMethod;
    if (currentPaymentMethod === 'mpesa' && mpesaConfirmed) {
        paymentMethod = 'mpesa-confirmed';
    }

    const payload = {
        session_id: CONFIG.sessionId,
        customer_id: selectedCustomer ? selectedCustomer.id : null,
        client_created_at: new Date().toISOString(),
        offline_uuid: uuidv4(),
        cart: cart.map(i => ({
            product_id: i.product.id,
            quantity: i.quantity,
            unit_price: i.unit_price,
            discount_amount: i.discount_amount
        })),
        payments: [{
            method: paymentMethod,
            amount: total,
            mpesa_phone: currentPaymentMethod === 'mpesa' ? document.getElementById('mpesa-phone').value : null,
            card_reference: currentPaymentMethod === 'card' ? document.getElementById('card-reference').value : null
        }],
        send_digital_receipt: document.getElementById('send-digital-receipt').checked,
        receipt_phone: document.getElementById('receipt-phone').value
    };

    if (navigator.onLine) {
        try {
            setStatus("SUBMITTING...", "text-indigo-400");
            const res = await fetch(CONFIG.apiUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": CONFIG.csrfToken,
                },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("Sync failed");
            const saleData = await res.json();
            setStatus("SALE COMPLETED", "text-emerald-400");
            showReceipt(saleData.id);
        } catch (err) {
            console.error("Sale commit failed, queueing offline", err);
            await queueOfflineSale(payload);
            setStatus("OFFLINE SALE QUEUED.", "text-amber-400");
            postCompleteReset();
        }
    } else {
        await queueOfflineSale(payload);
        setStatus("OFFLINE SALE QUEUED.", "text-amber-400");
        postCompleteReset();
    }
}

function postCompleteReset() {
    cart = [];
    renderCart();
    
    // Reset M-Pesa
    mpesaConfirmed = false;
    document.getElementById('btn-stk-push').classList.remove('hidden');
    document.getElementById('mpesa-status-container').classList.add('hidden');
    document.getElementById('mpesa-status-text').textContent = "WAITING FOR CUSTOMER...";
    document.getElementById('mpesa-status-text').classList.replace('text-emerald-400', 'text-slate-400');
    
    const container = document.getElementById('mpesa-status-container');
    container.classList.replace('bg-emerald-900/20', 'bg-slate-900');
    container.classList.replace('border-emerald-500/50', 'border-slate-700');
    
    // Reset inputs
    document.getElementById('cash-tendered').value = '';
    document.getElementById('mpesa-phone').value = '';
    document.getElementById('card-reference').value = '';
    
    // Reset selected customer
    selectedCustomer = null;
    const customerSelect = document.getElementById('customer-select');
    if (customerSelect) {
        customerSelect.value = '';
    }
    const customerInfo = document.getElementById('customer-info');
    if (customerInfo) {
        customerInfo.classList.add('hidden');
    }
    fetchCustomers(); // Refresh loyalty points & credit balances
    
    updateTotals();
    
    setTimeout(() => {
        document.getElementById('barcode-input').focus();
    }, 100);
}

// Offline queueing placeholder (Real app uses IndexedDB)
async function queueOfflineSale(payload) {
    if (typeof window.saveToIndexedDB === 'function') {
        await window.saveToIndexedDB(payload);
    } else {
        console.warn("IndexedDB handler not found");
        // Fallback or localStorage
    }
}

// Receipt Modal Handlers
async function showReceipt(saleId) {
    try {
        const res = await fetch(`${CONFIG.apiUrl}${saleId}/receipt/`);
        if (!res.ok) throw new Error("Failed to load receipt");
        const data = await res.json();
        
        const receiptContent = document.getElementById('receipt-content');
        if (receiptContent) {
            receiptContent.textContent = data.text;
        }
        const modal = document.getElementById('receipt-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    } catch (err) {
        console.error("Receipt loading error:", err);
        setStatus("SALE COMPLETED (FAILED TO LOAD RECEIPT)", "text-amber-400", 5000);
        postCompleteReset();
    }
}

function closeReceiptModal() {
    const modal = document.getElementById('receipt-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    postCompleteReset();
}

function printReceipt() {
    window.print();
}

// Cart Helper Functions
function updateItemQty(index, val) {
    const qty = parseInt(val);
    if (isNaN(qty) || qty < 1) {
        cart[index].quantity = 1;
    } else {
        cart[index].quantity = qty;
    }
    renderCart();
}

function removeFromCart(index) {
    cart.splice(index, 1);
    renderCart();
    setStatus("ITEM REMOVED FROM CART.", "text-amber-400");
}

// Park/Hold Sale Functions
function holdCurrentSale() {
    if (cart.length === 0) {
        setStatus("CANNOT HOLD AN EMPTY CART", "text-rose-400");
        return;
    }
    
    const parkedSales = JSON.parse(localStorage.getItem('parked_sales') || '[]');
    const newParked = {
        id: uuidv4().substring(0, 8),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        cart: cart,
        total: document.getElementById('cart-total').textContent
    };
    
    parkedSales.push(newParked);
    localStorage.setItem('parked_sales', JSON.stringify(parkedSales));
    
    cart = [];
    renderCart();
    updateParkedSalesUI();
    setStatus("SALE PARKED (ON HOLD)", "text-indigo-400");
}

function updateParkedSalesUI() {
    const container = document.getElementById('parked-sales-container');
    const select = document.getElementById('parked-sales-select');
    if (!container || !select) return;
    
    const parkedSales = JSON.parse(localStorage.getItem('parked_sales') || '[]');
    
    if (parkedSales.length === 0) {
        container.classList.add('hidden');
        return;
    }
    
    container.classList.remove('hidden');
    select.innerHTML = '<option value="" disabled selected>SELECT TO RESUME</option>';
    
    parkedSales.forEach(sale => {
        select.innerHTML += `
            <option value="${sale.id}">#${sale.id} (${sale.timestamp}) - KES ${sale.total}</option>
        `;
    });
}

function resumeParkedSale(id) {
    if (!id) return;
    
    if (cart.length > 0) {
        setStatus("CLEAR OR HOLD CURRENT SALE FIRST", "text-rose-400");
        document.getElementById('parked-sales-select').value = '';
        return;
    }
    
    let parkedSales = JSON.parse(localStorage.getItem('parked_sales') || '[]');
    const found = parkedSales.find(sale => sale.id === id);
    
    if (found) {
        cart = found.cart;
        parkedSales = parkedSales.filter(sale => sale.id !== id);
        localStorage.setItem('parked_sales', JSON.stringify(parkedSales));
        
        renderCart();
        updateParkedSalesUI();
        setStatus("SALE RESUMED", "text-emerald-400");
    }
}

// ── CUSTOMER & CREDIT CONTROL FUNCTIONS ──────────────────────────────────────

async function fetchCustomers() {
    try {
        const res = await fetch('/api/v1/customers/');
        if (!res.ok) throw new Error("Failed to fetch customers");
        
        customersList = await res.json();
        
        const select = document.getElementById('customer-select');
        if (!select) return;
        
        // Save current selected value
        const currentVal = select.value;
        
        // Clear & populate
        select.innerHTML = '<option value="">Walk-in Customer</option>';
        customersList.forEach(c => {
            select.innerHTML += `
                <option value="${c.id}">${c.name} (${c.phone || 'No Phone'})</option>
            `;
        });
        
        // Restore selected value if still in list
        if (currentVal && customersList.some(c => c.id == currentVal)) {
            select.value = currentVal;
            onCustomerSelectChanged(currentVal);
        }
    } catch (err) {
        console.error("Customers list fetch failed:", err);
    }
}

function onCustomerSelectChanged(customerId) {
    const infoContainer = document.getElementById('customer-info');
    if (!customerId) {
        selectedCustomer = null;
        if (infoContainer) infoContainer.classList.add('hidden');
        updateTotals();
        return;
    }
    
    selectedCustomer = customersList.find(c => c.id == customerId);
    if (!selectedCustomer) {
        if (infoContainer) infoContainer.classList.add('hidden');
        updateTotals();
        return;
    }
    
    // Populate details
    document.getElementById('cust-phone-val').textContent = selectedCustomer.phone || 'N/A';
    document.getElementById('cust-points-val').textContent = `${selectedCustomer.loyalty_points || 0} Points`;
    
    const creditVal = document.getElementById('cust-credit-val');
    if (selectedCustomer.allow_credit_sales) {
        const creditLimit = Number(selectedCustomer.credit_limit || 0);
        const creditBalance = Number(selectedCustomer.current_credit_balance || 0);
        const availableCredit = creditLimit - creditBalance;
        creditVal.textContent = `KES ${formatMoney(availableCredit)} / KES ${formatMoney(creditLimit)}`;
        creditVal.className = 'text-emerald-400 font-bold';
    } else {
        creditVal.textContent = 'NOT ALLOWED';
        creditVal.className = 'text-rose-400 font-bold';
    }
    
    if (infoContainer) infoContainer.classList.remove('hidden');
    updateTotals();
}

function openCustomerModal() {
    document.getElementById('customer-modal').classList.remove('hidden');
}

function closeCustomerModal() {
    document.getElementById('customer-modal').classList.add('hidden');
    document.getElementById('new-customer-form').reset();
    document.getElementById('credit-limit-container').classList.add('hidden');
}

function toggleCreditLimitField(checked) {
    const container = document.getElementById('credit-limit-container');
    if (checked) {
        container.classList.remove('hidden');
    } else {
        container.classList.add('hidden');
    }
}

async function registerNewCustomer(event) {
    event.preventDefault();
    
    const name = document.getElementById('new-cust-name').value.trim();
    const phone = document.getElementById('new-cust-phone').value.trim();
    const email = document.getElementById('new-cust-email').value.trim();
    const allowCredit = document.getElementById('new-cust-allow-credit').checked;
    const creditLimit = document.getElementById('new-cust-credit-limit').value || "0.00";
    
    if (!name || !phone) {
        setStatus("NAME AND PHONE ARE REQUIRED", "text-rose-400");
        return;
    }
    
    setStatus("REGISTERING CUSTOMER...", "text-indigo-400");
    
    try {
        const res = await fetch('/api/v1/customers/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({
                name: name,
                phone: phone,
                email: email,
                allow_credit_sales: allowCredit,
                credit_limit: creditLimit
            })
        });
        
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.phone ? `Phone number: ${errData.phone[0]}` : "Failed to register customer");
        }
        
        const newCust = await res.json();
        
        // Refresh customer list
        await fetchCustomers();
        
        // Select the new customer
        const select = document.getElementById('customer-select');
        if (select) {
            select.value = newCust.id;
            onCustomerSelectChanged(newCust.id);
        }
        
        closeCustomerModal();
        setStatus(`CUSTOMER ${name} REGISTERED SUCCESSFULLY`, "text-emerald-400");
    } catch (err) {
        console.error("Customer registration failed:", err);
        setStatus(err.message, "text-rose-400");
    }
}
