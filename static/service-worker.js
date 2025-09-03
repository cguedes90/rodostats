const CACHE_NAME = 'rodostats-v2.0';
const STATIC_CACHE = 'rodostats-static-v2.0';
const DYNAMIC_CACHE = 'rodostats-dynamic-v2.0';
const API_CACHE = 'rodostats-api-v2.0';

// URLs essenciais para cache estático
const STATIC_URLS = [
  '/',
  '/app', 
  '/vehicles',
  '/analytics',
  '/oil_list',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// Padrões de URL para diferentes estratégias de cache
const API_PATTERNS = [
  new RegExp('/api/'),
  new RegExp('/dashboard'),
  new RegExp('/vehicles')
];

const CACHE_STRATEGIES = {
  CACHE_FIRST: 'cache-first',
  NETWORK_FIRST: 'network-first', 
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate'
};

// Instalação - cache estático
self.addEventListener('install', event => {
  console.log('🚀 RodoStats Service Worker instalando...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('📦 Cachando recursos estáticos');
        return cache.addAll(STATIC_URLS);
      })
      .then(() => {
        console.log('✅ Service Worker instalado com sucesso');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('❌ Erro na instalação:', err);
      })
  );
});

// Interceptação de requisições com estratégias inteligentes
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Estratégia baseada no tipo de recurso
  if (event.request.method !== 'GET') {
    // Requisições POST/PUT - sempre tentar network first
    event.respondWith(networkFirst(event.request));
  } else if (STATIC_URLS.some(staticUrl => event.request.url.includes(staticUrl))) {
    // Recursos estáticos - cache first
    event.respondWith(cacheFirst(event.request));
  } else if (API_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    // APIs - stale while revalidate
    event.respondWith(staleWhileRevalidate(event.request));
  } else if (url.pathname.match(/\.(png|jpg|jpeg|svg|gif|css|js)$/)) {
    // Assets - cache first
    event.respondWith(cacheFirst(event.request));
  } else {
    // Páginas HTML - network first com fallback
    event.respondWith(networkFirst(event.request));
  }
});

// Estratégia Cache First
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('Cache first failed:', error);
    return new Response('Recurso indisponível offline', { status: 503 });
  }
}

// Estratégia Network First
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('Network failed, trying cache:', error);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Página offline fallback
    if (request.destination === 'document') {
      return new Response(`
        <html>
          <head>
            <title>RodoStats - Offline</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
              body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; 
                     background: #1a1a2e; color: #fff; text-align: center; padding: 50px; }
              .offline-icon { font-size: 4rem; margin: 20px 0; }
              .btn { background: #4A90E2; color: white; padding: 10px 20px; 
                     text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }
            </style>
          </head>
          <body>
            <div class="offline-icon">🚗📱</div>
            <h1>RodoStats</h1>
            <h2>Você está offline</h2>
            <p>Conecte-se à internet para acessar todas as funcionalidades</p>
            <a href="/" class="btn" onclick="window.location.reload()">Tentar novamente</a>
          </body>
        </html>
      `, { 
        headers: { 'Content-Type': 'text/html' },
        status: 503
      });
    }
    
    return new Response('Conteúdo indisponível offline', { status: 503 });
  }
}

// Estratégia Stale While Revalidate  
async function staleWhileRevalidate(request) {
  const cache = await caches.open(API_CACHE);
  const cachedResponse = await cache.match(request);
  
  const networkResponse = fetch(request).then(response => {
    if (response && response.status === 200) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);
  
  return cachedResponse || networkResponse;
}

// Ativação - limpar caches antigos
self.addEventListener('activate', event => {
  console.log('🔄 RodoStats Service Worker ativando...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      const validCaches = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE];
      return Promise.all(
        cacheNames.map(cacheName => {
          if (!validCaches.includes(cacheName)) {
            console.log('🗑️ Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('✅ Service Worker ativado e assumiu controle');
      return self.clients.claim();
    })
  );
});

// Background sync para dados offline
self.addEventListener('sync', event => {
  console.log('🔄 Background sync triggered:', event.tag);
  
  if (event.tag === 'fuel-records-sync') {
    event.waitUntil(syncOfflineRecords());
  } else if (event.tag === 'oil-changes-sync') {
    event.waitUntil(syncOfflineOilChanges());
  }
});

// Sincronizar registros de combustível offline
async function syncOfflineRecords() {
  try {
    const offlineData = await getOfflineData('pending-fuel-records');
    for (const record of offlineData) {
      try {
        await fetch('/add_fuel_record', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(record)
        });
        await removeOfflineData('pending-fuel-records', record.id);
        console.log('✅ Registro sincronizado:', record.id);
      } catch (error) {
        console.error('❌ Erro na sincronização:', error);
      }
    }
  } catch (error) {
    console.error('❌ Erro no background sync:', error);
  }
}

// Sincronizar trocas de óleo offline
async function syncOfflineOilChanges() {
  try {
    const offlineData = await getOfflineData('pending-oil-changes');
    for (const oilChange of offlineData) {
      try {
        await fetch('/oil_change_global', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(oilChange)
        });
        await removeOfflineData('pending-oil-changes', oilChange.id);
        console.log('✅ Troca de óleo sincronizada:', oilChange.id);
      } catch (error) {
        console.error('❌ Erro na sincronização:', error);
      }
    }
  } catch (error) {
    console.error('❌ Erro no background sync:', error);
  }
}

// Push notifications inteligentes
self.addEventListener('push', event => {
  let notificationData = {
    title: 'RodoStats',
    body: 'Você tem uma nova notificação!',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png'
  };

  if (event.data) {
    try {
      notificationData = { ...notificationData, ...event.data.json() };
    } catch (error) {
      notificationData.body = event.data.text();
    }
  }

  const options = {
    body: notificationData.body,
    icon: notificationData.icon,
    badge: notificationData.badge,
    vibrate: [200, 100, 200],
    requireInteraction: true,
    data: {
      dateOfArrival: Date.now(),
      url: notificationData.url || '/app',
      ...notificationData.data
    },
    actions: [
      {
        action: 'view',
        title: '👀 Ver',
        icon: '/static/icons/icon-192.png'
      },
      {
        action: 'dismiss',
        title: '❌ Dispensar'
      }
    ],
    tag: notificationData.tag || 'default'
  };

  event.waitUntil(
    self.registration.showNotification(notificationData.title, options)
  );
});

// Clique em notificações
self.addEventListener('notificationclick', event => {
  console.log('🔔 Notificação clicada:', event.action);
  event.notification.close();

  const targetUrl = event.notification.data.url || '/app';

  if (event.action === 'view' || !event.action) {
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then(clientList => {
          // Tentar focar uma janela existente
          for (const client of clientList) {
            if (client.url.includes(self.location.origin) && 'focus' in client) {
              client.navigate(targetUrl);
              return client.focus();
            }
          }
          // Abrir nova janela se não houver uma existente
          if (clients.openWindow) {
            return clients.openWindow(targetUrl);
          }
        })
    );
  }
  // Action 'dismiss' não faz nada (apenas fecha a notificação)
});

// Utilidades para IndexedDB offline
function getOfflineData(storeName) {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in self)) {
      resolve([]);
      return;
    }
    
    const request = indexedDB.open('rodostats-offline', 1);
    request.onerror = () => resolve([]);
    request.onsuccess = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(storeName)) {
        resolve([]);
        return;
      }
      
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const getAllRequest = store.getAll();
      
      getAllRequest.onsuccess = () => resolve(getAllRequest.result || []);
      getAllRequest.onerror = () => resolve([]);
    };
  });
}

function removeOfflineData(storeName, id) {
  return new Promise((resolve) => {
    if (!('indexedDB' in self)) {
      resolve();
      return;
    }
    
    const request = indexedDB.open('rodostats-offline', 1);
    request.onsuccess = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(storeName)) {
        resolve();
        return;
      }
      
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      store.delete(id);
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => resolve();
    };
    request.onerror = () => resolve();
  });
}
