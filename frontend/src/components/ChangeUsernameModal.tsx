import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { auth } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { X, Loader2, CheckCircle } from 'lucide-react';
import { parseApiError } from '../utils/formErrors';
import { useTranslation } from 'react-i18next';

interface ChangeUsernameModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ChangeUsernameModal({ isOpen, onClose }: ChangeUsernameModalProps) {
  const { t } = useTranslation();
  const { user, refreshUser } = useAuth();
  const requiresPassword = !user?.oauth_provider;
  const [currentPassword, setCurrentPassword] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: (data: { current_password: string; new_username: string }) =>
      auth.changeUsername(data),
    onSuccess: async () => {
      await refreshUser();
      setSuccess(true);
      setTimeout(() => {
        resetAndClose();
      }, 1500);
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to change username.'));
    },
  });

  const resetAndClose = () => {
    setCurrentPassword('');
    setNewUsername('');
    setError('');
    setSuccess(false);
    onClose();
  };

  if (!isOpen) return null;

  const canSubmit = newUsername.trim().length > 0 && (!requiresPassword || currentPassword) && !mutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate({
      current_password: currentPassword,
      new_username: newUsername.trim(),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-cyber-darker border border-cyber-light/30 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg font-bold text-white">{t('modals.change_username_title')}</h2>
          <button onClick={resetAndClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {success ? (
          <div className="p-8 text-center">
            <CheckCircle className="h-12 w-12 text-cyber-green mx-auto mb-3" />
            <p className="text-cyber-green font-mono">{t('modals.username_changed')}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            {error && (
              <div className="p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                {t('modals.new_username')} *
              </label>
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                className="input-cyber"
                required
                maxLength={150}
                autoComplete="username"
                placeholder={user?.username}
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
              className="w-full btn-cyber py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('modals.changing')}
                </>
              ) : (
                t('modals.change_username_title')
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
