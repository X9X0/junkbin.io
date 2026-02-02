import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../api/client';

export default function PasswordReset() {
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
      setError(err.response?.data?.error || 'Failed to send reset email');
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
              CHECK YOUR <span className="text-cyber-cyan">EMAIL</span>
            </h1>
            <p className="text-gray-400 mb-6">
              If an account with that email exists, we've sent password reset instructions.
            </p>
            <Link to="/login" className="btn-cyber inline-block">
              BACK TO LOGIN
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
            RESET <span className="text-cyber-cyan">PASSWORD</span>
          </h1>
          <p className="text-gray-500 font-mono text-sm">
            Enter your email to receive reset instructions
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
                EMAIL ADDRESS
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-cyber"
                placeholder="Enter your email"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-cyber flex items-center justify-center gap-2 py-3"
            >
              {isLoading ? (
                <span className="animate-pulse">SENDING...</span>
              ) : (
                <>
                  <Mail className="h-4 w-4" />
                  SEND RESET LINK
                </>
              )}
            </button>
          </form>

          <div className="divider-circuit" />

          <p className="text-center text-sm text-gray-500">
            Remember your password?{' '}
            <Link to="/login" className="text-cyber-cyan hover:underline">
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
