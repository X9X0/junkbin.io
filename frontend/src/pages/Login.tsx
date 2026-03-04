import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import GoogleLoginButton from '../components/GoogleLoginButton';
import GitHubLoginButton from '../components/GitHubLoginButton';
import { LogIn, AlertCircle } from 'lucide-react';

export default function Login() {
  const { t } = useTranslation();
  const { login, googleLogin, githubLogin } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login({ username, password });
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || t('auth.login.invalid_credentials'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            {t('auth.login.title')}
          </h1>
          <p className="text-gray-500 font-mono text-sm">
            {t('auth.login.subtitle')}
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
                {t('auth.login.username')}
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-cyber"
                placeholder={t('auth.login.username_placeholder')}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                {t('auth.login.password')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-cyber"
                placeholder={t('auth.login.password_placeholder')}
                required
              />
              <div className="mt-2 text-right">
                <Link to="/reset-password" className="text-sm text-cyber-cyan hover:underline">
                  {t('auth.login.forgot')}
                </Link>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-cyber flex items-center justify-center gap-2 py-3"
            >
              {isLoading ? (
                <span className="animate-pulse">{t('auth.login.submitting')}</span>
              ) : (
                <>
                  <LogIn className="h-4 w-4" />
                  {t('auth.login.submit')}
                </>
              )}
            </button>
          </form>

          {/* OR divider + Google login */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-700" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-cyber-dark px-4 text-sm font-mono text-gray-500">{t('auth.login.or')}</span>
            </div>
          </div>

          <div className="space-y-3">
            <GoogleLoginButton
              text="signin_with"
              onSuccess={async (credential) => {
                setError('');
                setIsLoading(true);
                try {
                  await googleLogin(credential);
                  navigate('/');
                } catch (err: any) {
                  setError(err.response?.data?.error || t('auth.login.google_failed'));
                } finally {
                  setIsLoading(false);
                }
              }}
              onError={(msg) => setError(msg)}
            />
            <GitHubLoginButton
              text="signin_with"
              onSuccess={async (code) => {
                setError('');
                setIsLoading(true);
                try {
                  await githubLogin(code);
                  navigate('/');
                } catch (err: any) {
                  setError(err.response?.data?.error || 'GitHub sign-in failed');
                } finally {
                  setIsLoading(false);
                }
              }}
              onError={(msg) => setError(msg)}
            />
          </div>

          <div className="divider-circuit" />

          <p className="text-center text-sm text-gray-500">
            {t('auth.login.no_account')}{' '}
            <Link to="/register" className="text-cyber-cyan hover:underline">
              {t('auth.login.register_link')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
