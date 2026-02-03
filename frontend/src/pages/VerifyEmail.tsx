import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CheckCircle, AlertCircle, Mail } from 'lucide-react';
import api from '../api/client';

export default function VerifyEmail() {
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      try {
        const response = await api.post('/auth/verify-email/', { uid, token });
        setMessage(response.data.message || 'Email verified successfully!');
        setStatus('success');
      } catch (err: any) {
        setMessage(err.response?.data?.error || 'Verification failed. The link may have expired.');
        setStatus('error');
      }
    };

    if (uid && token) {
      verifyEmail();
    } else {
      setStatus('error');
      setMessage('Invalid verification link.');
    }
  }, [uid, token]);

  if (status === 'loading') {
    return (
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="card-cyber p-8 text-center">
            <Mail className="h-16 w-16 text-cyber-cyan mx-auto mb-4 animate-pulse" />
            <h1 className="font-display text-2xl font-bold text-white mb-4">
              VERIFYING <span className="text-cyber-cyan">EMAIL</span>
            </h1>
            <p className="text-gray-400">
              Please wait while we verify your email address...
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
              EMAIL <span className="text-cyber-green">VERIFIED</span>
            </h1>
            <p className="text-gray-400 mb-6">{message}</p>
            <Link to="/" className="btn-cyber inline-block">
              CONTINUE TO SITE
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
            VERIFICATION <span className="text-cyber-pink">FAILED</span>
          </h1>
          <p className="text-gray-400 mb-6">{message}</p>
          <Link to="/login" className="btn-cyber inline-block">
            GO TO LOGIN
          </Link>
        </div>
      </div>
    </div>
  );
}
