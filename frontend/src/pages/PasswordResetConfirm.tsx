import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Lock, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../api/client';

export default function PasswordResetConfirm() {
  const { t } = useTranslation();
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== passwordConfirm) {
      setError(t('auth.reset_confirm.passwords_mismatch'));
      return;
    }

    if (password.length < 8) {
      setError(t('auth.reset_confirm.password_too_short'));
      return;
    }

    setIsLoading(true);

    try {
      await api.post('/auth/password/reset/confirm/', {
        uid,
        token,
        new_password: password,
        new_password_confirm: passwordConfirm,
      });
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.error || t('auth.reset_confirm.failed'));
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
              {t('auth.reset_confirm.success_title')}
            </h1>
            <p className="text-gray-400 mb-6">
              {t('auth.reset_confirm.success_message')}
            </p>
            <button
              onClick={() => navigate('/login')}
              className="btn-cyber"
            >
              {t('auth.reset_confirm.go_to_login')}
            </button>
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
            {t('auth.reset_confirm.title')}
          </h1>
          <p className="text-gray-500 font-mono text-sm">
            {t('auth.reset_confirm.subtitle')}
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
                {t('auth.reset_confirm.new_password')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-cyber"
                placeholder={t('auth.reset_confirm.new_password_placeholder')}
                required
                minLength={8}
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                {t('auth.reset_confirm.confirm_password')}
              </label>
              <input
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                className="input-cyber"
                placeholder={t('auth.reset_confirm.confirm_placeholder')}
                required
                minLength={8}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-cyber flex items-center justify-center gap-2 py-3"
            >
              {isLoading ? (
                <span className="animate-pulse">{t('auth.reset_confirm.submitting')}</span>
              ) : (
                <>
                  <Lock className="h-4 w-4" />
                  {t('auth.reset_confirm.submit')}
                </>
              )}
            </button>
          </form>

          <div className="divider-circuit" />

          <p className="text-center text-sm text-gray-500">
            <Link to="/login" className="text-cyber-cyan hover:underline">
              {t('auth.reset_confirm.back_to_login')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
