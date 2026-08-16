import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import './sentry'
import './index.css'
import './i18n'
import App from './App.tsx'

// eslint-disable-next-line no-console
console.log('%c psst: try the old code 👾', 'color:#22c55e;font-family:monospace;font-size:13px;');

registerSW({
  immediate: true,
  onRegisterError(error) {
    // Environments like crawler bots often can't/won't register a service
    // worker; that's not a real failure, so keep it out of Sentry.
    // eslint-disable-next-line no-console
    console.warn('Service worker registration failed:', error);
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
