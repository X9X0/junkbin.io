import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Home, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  const { t } = useTranslation();

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
      <div className="text-center">
        {/* Glitchy 404 */}
        <div className="relative mb-8">
          <h1 className="font-display text-[150px] md:text-[200px] font-bold text-cyber-dark leading-none">
            404
          </h1>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-display text-[150px] md:text-[200px] font-bold text-cyber-cyan opacity-50 animate-pulse">
              404
            </span>
          </div>
        </div>

        {/* Warning icon */}
        <div className="w-20 h-20 mx-auto mb-6 flex items-center justify-center bg-cyber-pink/10 border border-cyber-pink/30">
          <AlertTriangle className="h-10 w-10 text-cyber-pink" />
        </div>

        <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-4">
          {t('not_found.line1')}
          <span className="block text-cyber-pink">{t('not_found.line2')}</span>
        </h2>

        <p className="text-gray-400 max-w-md mx-auto mb-8 font-mono text-sm">
          {t('not_found.message')}
        </p>

        {/* Terminal-style error */}
        <div className="max-w-md mx-auto mb-8 text-left">
          <div className="terminal">
            <p className="text-cyber-pink">{t('not_found.error_label')}</p>
            <p className="text-gray-500 mt-1">
              &gt; {t('not_found.error_detail')}
            </p>
            <p className="text-gray-500">
              &gt; {t('not_found.check_url')}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/" className="btn-cyber flex items-center gap-2">
            <Home className="h-4 w-4" />
            {t('not_found.return_home')}
          </Link>
          <button
            onClick={() => window.history.back()}
            className="btn-cyber btn-cyber-pink flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            {t('not_found.go_back')}
          </button>
        </div>
      </div>
    </div>
  );
}
