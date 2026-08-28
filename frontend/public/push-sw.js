// Web Push handling, loaded into the vite-plugin-pwa-generated service
// worker via workbox.importScripts (see vite.config.ts). Kept separate from
// the generated sw.js so the generateSW strategy/precache config doesn't
// need to change.

self.addEventListener('push', (event) => {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch {
    payload = { title: 'Junkbin.io', body: event.data.text() };
  }

  const { title, body, url, unreadCount } = payload;

  event.waitUntil(
    (async () => {
      await self.registration.showNotification(title || 'Junkbin.io', {
        body: body || '',
        icon: '/icons/icon-192.png',
        // Must be a monochrome silhouette - Android reads only the alpha
        // channel and paints it solid white in the status bar. Reusing the
        // full-color app icon here rendered as a plain white square.
        badge: '/icons/badge-96.png',
        data: { url: url || '/' },
      });

      // Best-effort app-icon badge update. Not all browsers expose the
      // Badging API in service-worker scope, so this is a supplement to --
      // not a replacement for -- the foreground tab's own
      // navigator.setAppBadge() call in useNotificationCount.ts.
      if (typeof unreadCount === 'number') {
        if ('setAppBadge' in self.registration) {
          try {
            await self.registration.setAppBadge(unreadCount);
          } catch {
            // ignore -- unsupported in this browser's SW scope
          }
        }
        const clients = await self.clients.matchAll({ type: 'window' });
        clients.forEach((client) => client.postMessage({ type: 'set-badge', count: unreadCount }));
      }
    })()
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';

  event.waitUntil(
    (async () => {
      const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      const existing = clients.find((c) => new URL(c.url).origin === self.location.origin);
      if (existing) {
        existing.navigate(url);
        return existing.focus();
      }
      return self.clients.openWindow(url);
    })()
  );
});
