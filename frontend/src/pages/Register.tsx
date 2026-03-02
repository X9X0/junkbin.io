import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import GoogleLoginButton from '../components/GoogleLoginButton';
import { UserPlus, AlertCircle, Check } from 'lucide-react';
import { parseApiError } from '../utils/formErrors';

export default function Register() {
  const { t } = useTranslation();
  const { register, googleLogin } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.password_confirm) {
      setError(t('auth.register.passwords_mismatch'));
      return;
    }

    setIsLoading(true);

    try {
      await register(formData);
      navigate('/');
    } catch (err: any) {
      setError(parseApiError(err, t('auth.register.registration_failed')));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            {t('auth.register.title')}
          </h1>
          <p className="text-gray-500 font-mono text-sm">
            {t('auth.register.subtitle')}
          </p>
        </div>

        <div className="card-cyber p-8">
          {/* Quick signup via Google */}
          <GoogleLoginButton
            text="signup_with"
            onSuccess={async (credential) => {
              setError('');
              setIsLoading(true);
              try {
                await googleLogin(credential);
                navigate('/');
              } catch (err: any) {
                setError(err.response?.data?.error || t('auth.register.google_failed'));
              } finally {
                setIsLoading(false);
              }
            }}
            onError={(msg) => setError(msg)}
          />

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-700" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-cyber-dark px-4 text-sm font-mono text-gray-500">{t('auth.register.or')}</span>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-4 mb-6 bg-cyber-pink/10 border border-cyber-pink/30 text-cyber-pink">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                {t('auth.register.username')}
              </label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="input-cyber"
                placeholder={t('auth.register.username_placeholder')}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                {t('auth.register.email')}
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="input-cyber"
                placeholder={t('auth.register.email_placeholder')}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                {t('auth.register.password')}
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="input-cyber"
                placeholder={t('auth.register.password_placeholder')}
                required
                minLength={8}
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                {t('auth.register.confirm_password')}
              </label>
              <input
                type="password"
                name="password_confirm"
                value={formData.password_confirm}
                onChange={handleChange}
                className="input-cyber"
                placeholder={t('auth.register.confirm_placeholder')}
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-cyber flex items-center justify-center gap-2 py-3"
            >
              {isLoading ? (
                <span className="animate-pulse">{t('auth.register.submitting')}</span>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  {t('auth.register.submit')}
                </>
              )}
            </button>
          </form>

          {/* Benefits */}
          <div className="mt-6 p-4 bg-cyber-cyan/5 border border-cyber-cyan/20">
            <p className="text-xs font-mono text-gray-400 mb-3">
              {t('auth.register.benefits_title')}
            </p>
            <ul className="space-y-2 text-sm text-gray-300">
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-cyber-green" />
                {t('auth.register.benefit_submit')}
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-cyber-green" />
                {t('auth.register.benefit_upload')}
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-cyber-green" />
                {t('auth.register.benefit_reputation')}
              </li>
            </ul>
          </div>

          <div className="divider-circuit" />

          <p className="text-center text-sm text-gray-500">
            {t('auth.register.have_account')}{' '}
            <Link to="/login" className="text-cyber-cyan hover:underline">
              {t('auth.register.login_link')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
