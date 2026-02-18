import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { auth } from '../api/endpoints';
import { X, Loader2, CheckCircle } from 'lucide-react';
import { parseApiError } from '../utils/formErrors';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ChangePasswordModal({ isOpen, onClose }: ChangePasswordModalProps) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string; new_password_confirm: string }) =>
      auth.changePassword(data),
    onSuccess: () => {
      setSuccess(true);
      setTimeout(() => {
        resetAndClose();
      }, 1500);
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to change password.'));
    },
  });

  const resetAndClose = () => {
    setCurrentPassword('');
    setNewPassword('');
    setNewPasswordConfirm('');
    setError('');
    setSuccess(false);
    onClose();
  };

  if (!isOpen) return null;

  const validationError = () => {
    if (newPassword && newPassword.length < 8) return 'New password must be at least 8 characters.';
    if (newPasswordConfirm && newPassword !== newPasswordConfirm) return 'Passwords do not match.';
    return '';
  };

  const clientError = validationError();
  const canSubmit = currentPassword && newPassword.length >= 8 && newPassword === newPasswordConfirm && !mutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-cyber-darker border border-cyber-light/30 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg font-bold text-white">CHANGE PASSWORD</h2>
          <button onClick={resetAndClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {success ? (
          <div className="p-8 text-center">
            <CheckCircle className="h-12 w-12 text-cyber-green mx-auto mb-3" />
            <p className="text-cyber-green font-mono">PASSWORD CHANGED SUCCESSFULLY</p>
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
                Current Password *
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

            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                New Password *
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="input-cyber"
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
                Confirm New Password *
              </label>
              <input
                type="password"
                value={newPasswordConfirm}
                onChange={(e) => setNewPasswordConfirm(e.target.value)}
                className="input-cyber"
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>

            {clientError && (
              <div className="text-xs text-cyber-yellow font-mono">{clientError}</div>
            )}

            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full btn-cyber py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  CHANGING...
                </>
              ) : (
                'CHANGE PASSWORD'
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
