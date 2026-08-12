import * as Sentry from '@sentry/react';

const dsn = import.meta.env.VITE_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production',
    // Same GIT_SHA the backend tags its release with (see production.py),
    // so a single deploy's frontend and backend events correlate in Sentry.
    release: import.meta.env.VITE_GIT_SHA || undefined,
    integrations: [Sentry.browserTracingIntegration()],
    // Matches the backend's traces_sample_rate - well under the free plan's
    // 5M spans/month even combined. No replay/profiling integrations: replay
    // is capped at 50/month free and profiling isn't included on any plan,
    // it's metered pay-as-you-go.
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
  });
}
