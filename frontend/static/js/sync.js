const DB_NAME = 'posOfflineDB';
const STORE_NAME = 'pending_sales';

function initDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = e => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'offline_uuid' });
            }
        };
        req.onsuccess = e => resolve(e.target.result);
        req.onerror = e => reject(e.target.error);
    });
}

window.saveToIndexedDB = async function(payload) {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.put({
        ...payload,
        created_at: new Date().toISOString(),
        retry_count: 0
    });
    updateOfflineCount();
};

async function getOfflineSales() {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    return new Promise((resolve) => {
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result);
    });
}

async function removeOfflineSale(uuid) {
    const db = await initDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(uuid);
}

async function updateOfflineCount() {
    const sales = await getOfflineSales();
    const countEl = document.getElementById('pending-sales-count');
    if (countEl) countEl.textContent = sales.length;
}

window.syncSales = async function() {
    const sales = await getOfflineSales();
    if (sales.length === 0) return;

    try {
        const res = await fetch('/api/v1/sync/sales/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sales })
        });
        
        if (res.ok) {
            const data = await res.json();
            for (const result of data.results) {
                if (result.status === 'synced' || result.status === 'already_synced') {
                    await removeOfflineSale(result.offline_uuid);
                }
            }
        }
    } catch (err) {
        console.error('Sync failed', err);
    }
    updateOfflineCount();
};

// Initial count load
document.addEventListener('DOMContentLoaded', updateOfflineCount);
