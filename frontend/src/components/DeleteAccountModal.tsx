import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { auth } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import { parseApiError } from '../utils/formErrors';
import { useTranslation } from 'react-i18next';

interface DeleteAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DeleteAccountModal({ isOpen, onClose }: DeleteAccountModalProps) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const requiresPassword = !user?.oauth_provider;
  const [currentPassword, setCurrentPassword] = useState('');
  const [confirmUsername, setConfirmUsername] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (data: { current_password: string }) => auth.deleteAccount(data),
    onSuccess: async () => {
      await logout();
      navigate('/');
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to delete account.'));
    },
  });

  const resetAndClose = () => {
    setCurrentPassword('');
    setConfirmUsername('');
    setError('');
    onClose();
  };

  if (!isOpen) return null;

  const usernameMatches = confirmUsername === user?.username;
  const canSubmit = usernameMatches && (!requiresPassword || currentPassword) && !mutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate({ current_password: currentPassword });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-cyber-darker border border-cyber-pink/50 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-pink/30">
          <h2 className="font-display text-lg font-bold text-cyber-pink flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            {t('modals.delete_account_title')}
          </h2>
          <button onClick={resetAndClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm">
            {t('modals.delete_account_warning')}
          </div>

          {error && (
            <div className="p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              {t('modals.delete_account_confirm_label', { username: user?.username })}
            </label>
            <input
              type="text"
              value={confirmUsername}
              onChange={(e) => setConfirmUsername(e.target.value)}
              className="input-cyber"
              required
              autoComplete="off"
            />
          </div>

          {requiresPassword ? (
            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                {t('modals.current_password')} *
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="input-cyber"
                required
                autoComplete="current-password"
              />
            </div>
          ) : (
            <p className="text-xs text-gray-500 font-mono">{t('modals.oauth_no_password_needed')}</p>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full btn-cyber btn-cyber-pink py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('modals.deleting')}
              </>
            ) : (
              t('modals.delete_account_title')
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
