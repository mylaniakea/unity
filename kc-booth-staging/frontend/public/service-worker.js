self.addEventListener('push', function(event) {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Homelab Intelligence Alert';
    const options = {
        body: data.body || 'New alert!',
        icon: '/vite.svg', // Placeholder icon
        badge: '/vite.svg', // Placeholder badge
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/',
            alertId: data.alertId, // Optional: for linking to specific alerts
        }
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    const clickedNotification = event.notification.data;
    const urlToOpen = new URL(clickedNotification.url, self.location.origin).href;

    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        })
        .then(function(clientList) {
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});
