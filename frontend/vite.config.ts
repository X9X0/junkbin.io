import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { readFileSync } from 'fs'

const { version } = JSON.parse(readFileSync('./package.json', 'utf-8'))
const buildTime = new Date().toISOString()

// https://vite.dev/config/
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version),
    __BUILD_TIME__: JSON.stringify(buildTime),
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react':  ['react', 'react-dom'],
          'vendor-router': ['react-router-dom'],
          'vendor-query':  ['@tanstack/react-query'],
          'vendor-i18n':   ['i18next', 'react-i18next', 'i18next-browser-languagedetector', 'i18next-http-backend'],
          'vendor-icons':  ['lucide-react'],
          'vendor-utils':  ['axios', 'clsx'],
          'vendor-sentry': ['@sentry/react'],
        },
      },
    },
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: false,
      includeAssets: ['vite.svg', 'icons/*.png'],
      manifest: {
        name: 'Junkbin.io - Right to Repair Database',
        short_name: 'Junkbin',
        description: 'Community-driven database for electronic components and repair documentation',
        theme_color: '#05d9e8',
        background_color: '#0a0a0f',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        skipWaiting: true,
        clientsClaim: true,
        // Web Push (push/notificationclick) handlers, kept in a separate
        // file rather than switching to the injectManifest strategy.
        importScripts: ['/push-sw.js'],
        navigateFallbackDenylist: [/^\/media\//, /^\/static\//, /^\/api\//, /^\/admin\//],
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        runtimeCaching: [
          {
            // thumbnails are named by a hash of their source and settings, so a cached copy
            // never goes stale: phones (the PWA) don't fetch the same grid of images again
            urlPattern: ({ url, sameOrigin }) => sameOrigin && url.pathname.startsWith('/media/cache/'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'media-thumbnails',
              expiration: { maxEntries: 600, maxAgeSeconds: 60 * 60 * 24 * 30, purgeOnQuotaError: true },
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            urlPattern: /^https?:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
          {
            urlPattern: /^https?:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'gstatic-fonts-cache',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    }),
  ],
})
