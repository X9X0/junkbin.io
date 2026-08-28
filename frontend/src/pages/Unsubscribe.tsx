import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CheckCircle, AlertCircle, MailX } from 'lucide-react';
import { newsletter } from '../api/endpoints';

export default function Unsubscribe() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');

  useEffect(() => {
    const unsubscribe = async () => {
      try {
        const response = await newsletter.unsubscribe(token!);
        setEmail(response.email || '');
        setMessage(response.message || 'You have been unsubscribed.');
        setStatus('success');
      } catch (err: any) {
        setMessage(err.response?.data?.error || 'This unsubscribe link is invalid.');
        setStatus('error');
      }
    };

    if (token) {
      unsubscribe();
    } else {
      setStatus('error');
      setMessage('This unsubscribe link is invalid.');
    }
  }, [token]);

  if (status === 'loading') {
    return (
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="card-cyber p-8 text-center">
            <MailX className="h-16 w-16 text-cyber-cyan mx-auto mb-4 animate-pulse" />
            <h1 className="font-display text-2xl font-bold text-white mb-4">
              Unsubscribing...
            </h1>
            <p className="text-gray-400">
              One moment while we process your request.
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
              You're unsubscribed
            </h1>
            <p className="text-gray-400 mb-2">{message}</p>
            {email && (
              <p className="text-gray-500 text-sm mb-6 font-mono">{email}</p>
            )}
            <Link to="/" className="btn-cyber inline-block">
              Back to Junkbin.io
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
            Link didn't work
          </h1>
          <p className="text-gray-400 mb-6">{message}</p>
          <Link to="/" className="btn-cyber inline-block">
            Back to Junkbin.io
          </Link>
        </div>
      </div>
    </div>
  );
}
