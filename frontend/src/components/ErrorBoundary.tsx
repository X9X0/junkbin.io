import { Component } from 'react';
import type { ReactNode } from 'react';
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
