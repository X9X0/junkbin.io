import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../api/client';

export default function PasswordReset() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.post('/auth/password/reset/', { email });
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.error || t('auth.reset.failed'));
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="card-cyber p-8 text-center">
            <CheckCircle className="h-16 w-16 text-cyber-cyan mx-auto mb-4" />
            <h1 className="font-display text-2xl font-bold text-white mb-4">
              {t('auth.reset.success_title')}
            </h1>
            <p className="text-gray-400 mb-6">
              {t('auth.reset.success_message')}
            </p>
            <Link to="/login" className="btn-cyber inline-block">
              {t('auth.reset.back_to_login')}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            {t('auth.reset.title')}
          </h1>
          <p className="text-gray-500 font-mono text-sm">
            {t('auth.reset.subtitle')}
          </p>
        </div>

        <div className="card-cyber p-8">
          {error && (
            <div className="flex items-center gap-2 p-4 mb-6 bg-cyber-pink/10 border border-cyber-pink/30 text-cyber-pink">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                {t('auth.reset.email')}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-cyber"
                placeholder={t('auth.reset.email_placeholder')}
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-cyber flex items-center justify-center gap-2 py-3"
            >
              {isLoading ? (
                <span className="animate-pulse">{t('auth.reset.submitting')}</span>
              ) : (
                <>
                  <Mail className="h-4 w-4" />
                  {t('auth.reset.submit')}
                </>
              )}
            </button>
          </form>

          <div className="divider-circuit" />

          <p className="text-center text-sm text-gray-500">
            {t('auth.reset.remember_password')}{' '}
            <Link to="/login" className="text-cyber-cyan hover:underline">
              {t('auth.reset.login_link')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
