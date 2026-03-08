import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'

// eslint-disable-next-line no-console
console.log('%c psst: try the old code 👾', 'color:#22c55e;font-family:monospace;font-size:13px;');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
