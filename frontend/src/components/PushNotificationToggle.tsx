import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Bell, BellOff, Loader2 } from 'lucide-react';
import { notifications } from '../api/endpoints';

function urlBase64ToUint8Array(base64Url: string): Uint8Array {
  const padding = '='.repeat((4 - (base64Url.length % 4)) % 4);
  const base64 = (base64Url + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

const SUPPORTED = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;

/** Push notification opt-in, next to the email notification toggles in Profile. */
export default function PushNotificationToggle() {
  const { t } = useTranslation();
  const [subscribed, setSubscribed] = useState(false);
  const [loading, setLoading] = useState(SUPPORTED);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!SUPPORTED) return;
    (async () => {
      const registration = await navigator.serviceWorker.ready;
      const existing = await registration.pushManager.getSubscription();
      setSubscribed(!!existing);
      setLoading(false);
    })();
  }, []);

  if (!SUPPORTED) return null;

  const enable = async () => {
    setBusy(true);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') return;

      const { key } = await notifications.vapidPublicKey();
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(key) as BufferSource,
      });
      await notifications.pushSubscribe(subscription.toJSON() as PushSubscriptionJSON);
      setSubscribed(true);
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    setBusy(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await notifications.pushUnsubscribe(subscription.endpoint);
        await subscription.unsubscribe();
      }
      setSubscribed(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <div className="text-sm text-white font-mono">
          {t('profile.push_notifications', 'Push notifications')}
        </div>
        <div className="text-xs text-gray-500">
          {t('profile.push_notifications_desc', 'Get notified in your browser, even when this tab is closed.')}
        </div>
      </div>
      {loading ? (
        <Loader2 className="h-5 w-5 animate-spin text-cyber-cyan" />
      ) : (
        <button
          onClick={subscribed ? disable : enable}
          disabled={busy}
          className={`flex items-center gap-2 px-3 py-1.5 border font-mono text-xs disabled:opacity-50 ${
            subscribed
              ? 'border-cyber-cyan text-cyber-cyan hover:bg-cyber-cyan/10'
              : 'border-cyber-light/30 text-gray-400 hover:border-cyber-cyan hover:text-cyber-cyan'
          }`}
        >
          {subscribed ? <Bell className="h-3.5 w-3.5" /> : <BellOff className="h-3.5 w-3.5" />}
          {subscribed
            ? t('profile.push_enabled', 'Enabled')
            : t('profile.push_enable', 'Enable')}
        </button>
      )}
    </div>
  );
}
