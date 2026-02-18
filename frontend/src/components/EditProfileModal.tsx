import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { auth } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { X, Loader2 } from 'lucide-react';
import { parseApiError } from '../utils/formErrors';

interface EditProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function EditProfileModal({ isOpen, onClose }: EditProfileModalProps) {
  const { user, refreshUser } = useAuth();
  const [error, setError] = useState('');

  const [bio, setBio] = useState('');
  const [location, setLocation] = useState('');
  const [website, setWebsite] = useState('');
  const [avatar, setAvatar] = useState<File | null>(null);

  useEffect(() => {
    if (isOpen && user) {
      setBio(user.bio || '');
      setLocation(user.location || '');
      setWebsite(user.website || '');
      setAvatar(null);
      setError('');
    }
  }, [isOpen, user]);

  const mutation = useMutation({
    mutationFn: (data: FormData) => auth.updateProfile(data),
    onSuccess: async () => {
      await refreshUser();
      onClose();
    },
    onError: (err: any) => {
      setError(parseApiError(err, 'Failed to update profile.'));
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('bio', bio);
    formData.append('location', location);
    formData.append('website', website);
    if (avatar) formData.append('avatar', avatar);
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-cyber-darker border border-cyber-light/30 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-cyber-light/30">
          <h2 className="font-display text-lg font-bold text-white">EDIT PROFILE</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 border border-cyber-pink/50 bg-cyber-pink/10 text-cyber-pink text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Bio
            </label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              maxLength={500}
              placeholder="Tell us about yourself..."
              className="input-cyber resize-none"
            />
            <div className="text-xs text-gray-600 mt-1 text-right">{bio.length}/500</div>
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Location
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. San Francisco, CA"
              maxLength={100}
              className="input-cyber"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Website
            </label>
            <input
              type="url"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://..."
              className="input-cyber"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-gray-500 uppercase mb-1">
              Avatar <span className="text-gray-600">(optional)</span>
            </label>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              onChange={(e) => setAvatar(e.target.files?.[0] || null)}
              className="input-cyber text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full btn-cyber py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                SAVING...
              </>
            ) : (
              'SAVE CHANGES'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
