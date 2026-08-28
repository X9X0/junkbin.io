import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import * as Sentry from '@sentry/react';
import { AlertTriangle } from 'lucide-react';
import { withTranslation } from 'react-i18next';
import type { WithTranslation } from 'react-i18next';

interface Props extends WithTranslation {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });

    // A deploy replaced the JS bundle while this tab had an old page open,
    // so a lazy route's chunk hash no longer exists on the server. The fix
    // is just to reload for the current bundle - guard with sessionStorage
    // so a genuinely broken chunk doesn't reload-loop forever.
    const isChunkLoadError = /dynamically imported module|importing a module script failed|loading chunk/i.test(
      error.message
    );
    if (isChunkLoadError && !sessionStorage.getItem('chunk-reload-attempted')) {
      sessionStorage.setItem('chunk-reload-attempted', '1');
      window.location.reload();
    }
  }

  render() {
    const { t } = this.props;

    if (this.state.hasError) {
      return (
        <div className="min-h-[60vh] flex flex-col items-center justify-center px-4 text-center">
          <AlertTriangle className="h-16 w-16 text-cyber-yellow mb-4" />
          <p className="font-mono text-cyber-yellow text-xs tracking-[0.5em] mb-2">⚠ WARNING ⚠</p>
          <h2 className="font-display text-xl text-white mb-1 tracking-widest">
            NO USER SERVICEABLE PARTS INSIDE
          </h2>
          <p className="text-gray-500 font-mono text-xs mb-4">
            ...just kidding. Tear it apart.
          </p>
          <p className="text-gray-400 text-sm mb-6 max-w-md font-mono">
            {this.state.error?.message || t('common.error')}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: undefined });
              window.location.reload();
            }}
            className="btn-cyber"
          >
            RELOAD PAGE
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default withTranslation()(ErrorBoundary);
