import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, Mail } from 'lucide-react';
import api from '../api/client';

export default function VerifyEmail() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      try {
        const response = await api.post('/auth/verify-email/', { token });
        setMessage(response.data.message || t('verify_email.success_title'));
        setStatus('success');
      } catch (err: any) {
        setMessage(err.response?.data?.error || t('verify_email.invalid_link'));
        setStatus('error');
      }
    };

    if (token) {
      verifyEmail();
    } else {
      setStatus('error');
      setMessage(t('verify_email.invalid_link'));
    }
  }, [token]);

  if (status === 'loading') {
    return (
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="card-cyber p-8 text-center">
            <Mail className="h-16 w-16 text-cyber-cyan mx-auto mb-4 animate-pulse" />
            <h1 className="font-display text-2xl font-bold text-white mb-4">
              {t('verify_email.verifying_title')}
            </h1>
            <p className="text-gray-400">
              {t('verify_email.verifying_message')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="card-cyber p-8 text-center">
            <CheckCircle className="h-16 w-16 text-cyber-green mx-auto mb-4" />
            <h1 className="font-display text-2xl font-bold text-white mb-4">
              {t('verify_email.success_title')}
            </h1>
            <p className="text-gray-400 mb-6">{message}</p>
            <Link to="/" className="btn-cyber inline-block">
              {t('verify_email.continue_to_site')}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        <div className="card-cyber p-8 text-center">
          <AlertCircle className="h-16 w-16 text-cyber-pink mx-auto mb-4" />
          <h1 className="font-display text-2xl font-bold text-white mb-4">
            {t('verify_email.failed_title')}
          </h1>
          <p className="text-gray-400 mb-6">{message}</p>
          <Link to="/login" className="btn-cyber inline-block">
            {t('auth.reset_confirm.go_to_login')}
          </Link>
        </div>
      </div>
    </div>
  );
}
