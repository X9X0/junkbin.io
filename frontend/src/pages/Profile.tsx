import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { auth, messaging, reports } from '../api/endpoints';
import api from '../api/client';
import type { UserPreferences } from '../types';
import { BadgeGrid } from '../components/BadgeDisplay';
import EditProfileModal from '../components/EditProfileModal';
import ChangePasswordModal from '../components/ChangePasswordModal';
import ChangeUsernameModal from '../components/ChangeUsernameModal';
import DeleteAccountModal from '../components/DeleteAccountModal';
import PushNotificationToggle from '../components/PushNotificationToggle';
import MessageForwardingSetting from '../components/MessageForwardingSetting';
import {
  User,
  Shield,
  Star,
  Package,
  Cpu,
  Calendar,
  Award,
  AlertCircle,
  ChevronRight,
  Bell,
  Loader2,
  Ban,
  Pencil,
  Lock,
  FileText,
  Forward,
} from 'lucide-react';

export default function Profile() {
  const { t } = useTranslation();
  const { user, isAuthenticated } = useAuth();
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showChangeUsername, setShowChangeUsername] = useState(false);
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);

  const queryClient = useQueryClient();

  // Fetch user's contributions
  const { data: contributions, isLoading: contributionsLoading } = useQuery({
    queryKey: ['user-contributions', user?.id],
    queryFn: async () => {
      const response = await api.get(`/users/${user?.id}/contributions/`);
      return response.data;
    },
    enabled: !!user?.id,
  });

  // Fetch and manage notification preferences
  const { data: preferences, isLoading: prefsLoading } = useQuery({
    queryKey: ['preferences'],
    queryFn: auth.getPreferences,
    enabled: isAuthenticated,
  });

  const prefsMutation = useMutation({
    mutationFn: (data: Partial<UserPreferences>) => auth.updatePreferences(data),
    onMutate: async (newPrefs) => {
      await queryClient.cancelQueries({ queryKey: ['preferences'] });
      const previous = queryClient.getQueryData<UserPreferences>(['preferences']);
      queryClient.setQueryData<UserPreferences>(['preferences'], (old) =>
        old ? { ...old, ...newPrefs } : old
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['preferences'], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['preferences'] });
    },
  });

  const togglePref = (key: keyof UserPreferences) => {
    if (!preferences) return;
    prefsMutation.mutate({ [key]: !preferences[key] });
  };

  // Blocked users
  const { data: blockedData, isLoading: blockedLoading } = useQuery({
    queryKey: ['blocked-users'],
    queryFn: messaging.blocks,
    enabled: isAuthenticated,
  });

  const unblockMutation = useMutation({
    mutationFn: (blockId: string) => messaging.unblockUser(blockId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocked-users'] });
    },
  });

  // My reports
  const { data: myReports, isLoading: reportsLoading } = useQuery({
    queryKey: ['my-reports'],
    queryFn: () => reports.myReports(),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <AlertCircle className="h-16 w-16 text-cyber-pink mb-4" />
        <h2 className="font-display text-2xl text-white mb-2">{t('profile.not_logged_in')}</h2>
        <p className="text-gray-400 mb-6 text-center">
          {t('profile.please_log_in')}
        </p>
        <Link to="/login" className="btn-cyber">
          {t('auth.login.submit')}
        </Link>
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-4xl px-4">
        {/* Profile Header */}
        <div className="card-cyber p-6 mb-8">
          <div className="flex flex-col md:flex-row gap-6 items-center md:items-start">
            {/* Avatar */}
            <div className="w-24 h-24 bg-cyber-dark border-2 border-cyber-cyan flex items-center justify-center">
              {user.avatar ? (
                <img
                  src={user.avatar}
                  alt={user.username}
                  className="w-full h-full object-cover"
                />
              ) : (
                <User className="h-12 w-12 text-cyber-cyan" />
              )}
            </div>

            {/* Info */}
            <div className="flex-1 text-center md:text-left">
              <div className="flex flex-col md:flex-row md:items-center gap-2 mb-2">
                <h1 className="font-display text-2xl font-bold text-white">
                  {user.username}
                </h1>
                <div className="flex items-center justify-center md:justify-start gap-2">
                  {user.is_trusted && (
                    <span className="badge-cyber text-cyber-green border-cyber-green flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      {t('profile.trusted')}
                    </span>
                  )}
                  {user.is_moderator && (
                    <span className="badge-cyber text-cyber-yellow border-cyber-yellow flex items-center gap-1">
                      <Star className="h-3 w-3" />
                      {t('profile.moderator')}
                    </span>
                  )}
                </div>
              </div>

              <p className="text-gray-400 text-sm font-mono mb-4">{user.email}</p>

              {user.bio && (
                <p className="text-gray-300 text-sm mb-4">{user.bio}</p>
              )}

              <div className="flex items-center justify-center md:justify-start gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  Joined {new Date(user.created_at).toLocaleDateString()}
                </span>
              </div>

              <button
                onClick={() => setShowEditProfile(true)}
                className="mt-3 inline-flex items-center gap-1.5 text-xs font-mono text-gray-400 hover:text-cyber-cyan border border-cyber-light/30 hover:border-cyber-cyan/50 px-3 py-1.5 transition-colors"
              >
                <Pencil className="h-3 w-3" />
                {t('profile.edit_profile')}
              </button>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-cyan mb-1">
              {user.reputation_score || 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Award className="h-3.5 w-3.5" />
              {t('profile.reputation')}
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-pink mb-1">
              {user.contribution_count || 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Package className="h-3.5 w-3.5" />
              {t('profile.contributions')}
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-green mb-1">
              {contributions?.products?.length || 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Cpu className="h-3.5 w-3.5" />
              {t('profile.products')}
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-yellow mb-1">
              {contributions?.components?.length || 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Package className="h-3.5 w-3.5" />
              {t('profile.components')}
            </div>
          </div>
        </div>

        {/* Notification Settings */}
        <div className="card-cyber p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="h-5 w-5 text-cyber-cyan" />
            <h2 className="font-display text-lg font-bold text-white">
              {t('profile.notification_settings')}
            </h2>
          </div>

          {prefsLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-cyber-cyan" />
            </div>
          ) : preferences ? (
            <div className="space-y-3">
              {/* Master toggle */}
              <div className="flex items-center justify-between py-2">
                <div>
                  <div className="text-sm text-white font-mono">{t('profile.email_notifications')}</div>
                  <div className="text-xs text-gray-500">
                    {t('profile.email_notifications_desc')}
                  </div>
                </div>
                <button
                  onClick={() => togglePref('email_notifications')}
                  className={`relative w-11 h-6 rounded-full transition-colors ${
                    preferences.email_notifications
                      ? 'bg-cyber-cyan/30 border border-cyber-cyan'
                      : 'bg-cyber-dark border border-cyber-light/30'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
                      preferences.email_notifications
                        ? 'translate-x-5 bg-cyber-cyan'
                        : 'translate-x-0 bg-gray-500'
                    }`}
                  />
                </button>
              </div>

              <PushNotificationToggle />

              <div className="border-t border-cyber-light/20" />

              {/* Sub-toggles */}
              {[
                { key: 'notify_messages' as const, label: t('profile.notif_messages'), desc: t('profile.notif_messages_desc') },
                { key: 'notify_submissions' as const, label: t('profile.notif_submissions'), desc: t('profile.notif_submissions_desc') },
                { key: 'notify_reports' as const, label: t('profile.notif_reports'), desc: t('profile.notif_reports_desc') },
                { key: 'notify_account' as const, label: t('profile.notif_account'), desc: t('profile.notif_account_desc') },
                { key: 'notify_junkbin' as const, label: t('profile.notif_junkbin'), desc: t('profile.notif_junkbin_desc') },
              ].map(({ key, label, desc }) => (
                <div
                  key={key}
                  className={`flex items-center justify-between py-2 pl-4 ${
                    !preferences.email_notifications ? 'opacity-40' : ''
                  }`}
                >
                  <div>
                    <div className="text-sm text-gray-300 font-mono">{label}</div>
                    <div className="text-xs text-gray-600">{desc}</div>
                  </div>
                  <button
                    onClick={() => togglePref(key)}
                    disabled={!preferences.email_notifications}
                    className={`relative w-11 h-6 rounded-full transition-colors disabled:cursor-not-allowed ${
                      preferences[key]
                        ? 'bg-cyber-cyan/30 border border-cyber-cyan'
                        : 'bg-cyber-dark border border-cyber-light/30'
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-transform ${
                        preferences[key]
                          ? 'translate-x-5 bg-cyber-cyan'
                          : 'translate-x-0 bg-gray-500'
                      }`}
                    />
                  </button>
                </div>
              ))}

              <div className="text-xs text-gray-600 pt-2 font-mono">
                {t('profile.security_email_note')}
              </div>
            </div>
          ) : null}
        </div>

        {/* Message Forwarding */}
        <div className="card-cyber p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Forward className="h-5 w-5 text-cyber-cyan" />
            <h2 className="font-display text-lg font-bold text-white">
              {t('profile.message_forwarding', 'Message Forwarding')}
            </h2>
          </div>
          <MessageForwardingSetting />
        </div>

        {/* Blocked Users */}
        <div className="card-cyber p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Ban className="h-5 w-5 text-cyber-pink" />
            <h2 className="font-display text-lg font-bold text-white">
              {t('profile.blocked_users')}
            </h2>
          </div>

          {blockedLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-cyber-pink" />
            </div>
          ) : blockedData && blockedData.results.length > 0 ? (
            <div className="space-y-2">
              {blockedData.results.map((block) => (
                <div
                  key={block.id}
                  className="flex items-center justify-between p-3 border border-cyber-light/20 bg-cyber-dark"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-cyber-dark border border-cyber-light/30 flex items-center justify-center">
                      {block.blocked_user.avatar ? (
                        <img
                          src={block.blocked_user.avatar}
                          alt={block.blocked_user.username}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <User className="h-4 w-4 text-gray-500" />
                      )}
                    </div>
                    <div>
                      <div className="text-sm text-white font-mono">
                        {block.blocked_user.username}
                      </div>
                      <div className="text-xs text-gray-600">
                        {t('profile.blocked_on', { date: new Date(block.created_at).toLocaleDateString() })}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => unblockMutation.mutate(block.id)}
                    disabled={unblockMutation.isPending}
                    className="text-xs font-mono text-cyber-pink hover:text-white border border-cyber-pink/50 px-3 py-1 hover:bg-cyber-pink/10 transition-colors disabled:opacity-50"
                  >
                    {t('profile.unblock')}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 py-2">
              {t('profile.no_blocked')}
            </p>
          )}
        </div>

        {/* Security */}
        <div className="card-cyber p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Lock className="h-5 w-5 text-cyber-green" />
            <h2 className="font-display text-lg font-bold text-white">
              {t('profile.security_settings')}
            </h2>
          </div>

          <div className="flex items-center justify-between py-2 border-b border-cyber-light/10">
            <div>
              <div className="text-sm text-white font-mono">{t('profile.username_label')}</div>
              <div className="text-xs text-gray-500">
                {t('profile.change_username')}
              </div>
            </div>
            <button
              onClick={() => setShowChangeUsername(true)}
              className="text-xs font-mono text-cyber-green hover:text-white border border-cyber-green/50 px-3 py-1.5 hover:bg-cyber-green/10 transition-colors"
            >
              {t('profile.change_username_btn')}
            </button>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <div className="text-sm text-white font-mono">{t('profile.password_label')}</div>
              <div className="text-xs text-gray-500">
                {t('profile.change_password')}
              </div>
            </div>
            <button
              onClick={() => setShowChangePassword(true)}
              className="text-xs font-mono text-cyber-green hover:text-white border border-cyber-green/50 px-3 py-1.5 hover:bg-cyber-green/10 transition-colors"
            >
              {t('profile.change_password_btn')}
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="card-cyber p-6 mb-8 border-cyber-pink/30">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="h-5 w-5 text-cyber-pink" />
            <h2 className="font-display text-lg font-bold text-white">
              {t('profile.danger_zone')}
            </h2>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <div className="text-sm text-white font-mono">{t('profile.delete_account_label')}</div>
              <div className="text-xs text-gray-500">
                {t('profile.delete_account_desc')}
              </div>
            </div>
            <button
              onClick={() => setShowDeleteAccount(true)}
              className="text-xs font-mono text-cyber-pink hover:text-white border border-cyber-pink/50 px-3 py-1.5 hover:bg-cyber-pink/10 transition-colors"
            >
              {t('profile.delete_account_btn')}
            </button>
          </div>
        </div>

        {/* My Reports */}
        <div className="card-cyber p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="h-5 w-5 text-cyber-yellow" />
            <h2 className="font-display text-lg font-bold text-white">
              {t('profile.my_reports')}
            </h2>
          </div>

          {reportsLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-cyber-yellow" />
            </div>
          ) : myReports && myReports.results.length > 0 ? (
            <div className="space-y-2">
              {myReports.results.map((report) => (
                <div
                  key={report.id}
                  className="flex items-center justify-between p-3 border border-cyber-light/20 bg-cyber-dark"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`badge-cyber text-[10px] ${
                          report.status === 'pending'
                            ? 'text-cyber-yellow border-cyber-yellow'
                            : report.status === 'resolved_valid'
                              ? 'text-cyber-green border-cyber-green'
                              : 'text-gray-400 border-gray-500'
                        }`}
                      >
                        {report.status_display || report.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">
                        {report.reason_display || report.reason}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400 truncate">
                      {report.reported_item_data?.display || `${report.content_type_name} #${report.object_id}`}
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      {new Date(report.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 py-2">
              {t('profile.no_reports')}
            </p>
          )}
        </div>

        {/* Recent Contributions */}
        <div className="space-y-6">
          {/* Products */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg font-bold text-white">
                {t('profile.your_products')}
              </h2>
              <Link
                to="/my-submissions?type=products"
                className="text-xs text-cyber-cyan hover:text-white transition-colors flex items-center gap-1"
              >
                {t('profile.view_all')} <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {contributionsLoading ? (
              <div className="card-cyber p-8 text-center">
                <div className="text-cyber-cyan font-mono animate-pulse">
                  {t('profile.loading')}
                </div>
              </div>
            ) : contributions?.products?.length > 0 ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {contributions.products.slice(0, 6).map((product: any) => (
                  <Link
                    key={product.id}
                    to={`/products/${product.id}`}
                    className="card-cyber p-4 hover:border-cyber-cyan/50 transition-all group"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-cyber-cyan">
                        {product.manufacturer}
                      </span>
                      {!product.is_approved && (
                        <span className="badge-cyber text-cyber-yellow border-cyber-yellow text-[10px]">
                          {t('profile.pending')}
                        </span>
                      )}
                    </div>
                    <h3 className="font-semibold text-white group-hover:text-cyber-cyan transition-colors truncate">
                      {product.model_number}
                    </h3>
                    <div className="text-xs text-gray-500 mt-1">
                      {product.category_display || product.category}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="card-cyber p-8 text-center">
                <Cpu className="h-10 w-10 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 text-sm mb-4">
                  {t('profile.no_products')}
                </p>
                <Link to="/submit" className="btn-cyber text-sm">
                  {t('profile.add_first_product')}
                </Link>
              </div>
            )}
          </div>

          {/* Components */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg font-bold text-white">
                {t('profile.your_components')}
              </h2>
              <Link
                to="/my-submissions?type=components"
                className="text-xs text-cyber-pink hover:text-white transition-colors flex items-center gap-1"
              >
                {t('profile.view_all')} <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {contributionsLoading ? (
              <div className="card-cyber p-8 text-center">
                <div className="text-cyber-pink font-mono animate-pulse">
                  {t('profile.loading')}
                </div>
              </div>
            ) : contributions?.components?.length > 0 ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {contributions.components.slice(0, 6).map((component: any) => (
                  <Link
                    key={component.id}
                    to={`/components/${component.id}/products`}
                    className="card-cyber p-4 hover:border-cyber-pink/50 transition-all group"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-cyber-pink">
                        {component.manufacturer}
                      </span>
                    </div>
                    <h3 className="font-mono font-semibold text-white group-hover:text-cyber-pink transition-colors truncate">
                      {component.part_number}
                    </h3>
                    <div className="text-xs text-gray-500 mt-1">
                      {component.component_type_display || component.component_type}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="card-cyber p-8 text-center">
                <Package className="h-10 w-10 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 text-sm mb-4">
                  {t('profile.no_components')}
                </p>
                <Link to="/submit" className="btn-cyber text-sm">
                  {t('profile.add_first_component')}
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Badges/Achievements */}
        <div className="mt-8 p-4 border border-cyber-light/20 bg-cyber-dark/50">
          <h3 className="font-mono text-sm text-gray-500 mb-3">{t('profile.achievements')}</h3>
          <BadgeGrid
            badges={user.badges || []}
            size="md"
            emptyMessage={t('profile.no_achievements')}
          />
        </div>
      </div>

      {/* Modals */}
      <EditProfileModal
        isOpen={showEditProfile}
        onClose={() => setShowEditProfile(false)}
      />
      <ChangePasswordModal
        isOpen={showChangePassword}
        onClose={() => setShowChangePassword(false)}
      />
      <ChangeUsernameModal
        isOpen={showChangeUsername}
        onClose={() => setShowChangeUsername(false)}
      />
      <DeleteAccountModal
        isOpen={showDeleteAccount}
        onClose={() => setShowDeleteAccount(false)}
      />
    </div>
  );
}
