let cart = [];
let currentPaymentMethod = 'cash';
let mpesaConfirmed = false;

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
});

// Fetch product via API
async function fetchProduct(barcode) {
    setStatus("SEARCHING PRODUCT...", "text-indigo-400");
    try {
        const res = await fetch(`${CONFIG.productsUrl}?barcode=${barcode}&branch=${CONFIG.branchId}`);
        if (!res.ok) throw new Error("API Network error");
        
        const data = await res.json();
        const results = data.results || data;
        
        if (results.length > 0) {
            addToCart(results[0]);
            setStatus("PRODUCT ADDED.", "text-emerald-400");
        } else {
            setStatus("PRODUCT NOT FOUND.", "text-rose-400");
        }
    } catch (err) {
        // Offline handling
        setStatus("OFFLINE: PRODUCT CACHE REQUIRED.", "text-amber-400");
        // In real app we would check IndexedDB or cache here
    }
}

// Set status message
function setStatus(msg, colorClass = "text-slate-500") {
    const el = document.getElementById('status-message');
    el.textContent = msg;
    el.className = `text-[10px] font-mono ${colorClass}`;
    setTimeout(() => {
        el.textContent = "AWAITING INPUT...";
        el.className = "text-[10px] text-slate-500 font-mono";
    }, 3000);
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
            <td class="p-2 text-right">${item.quantity}</td>
            <td class="p-2 text-right text-slate-400">${formatMoney(item.unit_price)}</td>
            <td class="p-2 text-right pr-4 text-white">${formatMoney(lineTotal)}</td>
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
    } else {
        // Card simple active
        btn.disabled = false;
    }
}

// M-Pesa Stk push fake
function sendStkPush() {
    const phone = document.getElementById('mpesa-phone').value;
    if (!phone) return;
    
    const btn = document.getElementById('btn-stk-push');
    const container = document.getElementById('mpesa-status-container');
    const statusText = document.getElementById('mpesa-status-text');
    
    btn.classList.add('hidden');
    container.classList.remove('hidden');
    statusText.textContent = "WAITING FOR CUSTOMER (SIMULATED)...";
    
    // Simulate webhook arrival after 3s
    setTimeout(() => {
        statusText.textContent = "M-PESA CONFIRMED ✓";
        statusText.classList.remove('text-slate-400');
        statusText.classList.add('text-emerald-400');
        container.classList.replace('bg-slate-900', 'bg-emerald-900/20');
        container.classList.replace('border-slate-700', 'border-emerald-500/50');
        
        mpesaConfirmed = true;
        updateTotals();
    }, 3000);
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
    
    const payload = {
        session_id: CONFIG.sessionId,
        client_created_at: new Date().toISOString(),
        offline_uuid: uuidv4(),
        cart: cart.map(i => ({
            product_id: i.product.id,
            quantity: i.quantity,
            unit_price: i.unit_price,
            discount_amount: i.discount_amount
        })),
        payments: [{
            method: currentPaymentMethod,
            amount: total,
            mpesa_phone: currentPaymentMethod === 'mpesa' ? document.getElementById('mpesa-phone').value : null,
            card_reference: currentPaymentMethod === 'card' ? document.getElementById('card-reference').value : null
        }]
    };

    if (navigator.onLine) {
        try {
            setStatus("SUBMITTING...", "text-indigo-400");
            const res = await fetch(CONFIG.apiUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    // "Authorization": Bearer added if needed
                },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error("Sync failed");
            setStatus("SALE COMPLETED", "text-emerald-400");
            postCompleteReset();
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
