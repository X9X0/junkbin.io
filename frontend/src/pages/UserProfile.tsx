import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { users } from '../api/endpoints';
import {
  User as UserIcon,
  Shield,
  Star,
  Package,
  Cpu,
  Calendar,
  Award,
  MapPin,
  ExternalLink,
  MessageSquare,
  Trophy,
  Loader2,
  AlertCircle,
} from 'lucide-react';

export default function UserProfile() {
  const { id } = useParams<{ id: string }>();
  const { user: currentUser, isAuthenticated } = useAuth();

  const { data: profileUser, isLoading, error } = useQuery({
    queryKey: ['user-profile', id],
    queryFn: () => users.get(id!),
    enabled: !!id,
  });

  const { data: stats } = useQuery({
    queryKey: ['user-stats', id],
    queryFn: () => users.stats(id!),
    enabled: !!id,
  });

  const { data: contributions } = useQuery({
    queryKey: ['user-contributions', id],
    queryFn: () => users.contributions(id!),
    enabled: !!id,
  });

  const isSelf = isAuthenticated && currentUser?.id === id;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-cyber-cyan" />
      </div>
    );
  }

  if (error || !profileUser) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <AlertCircle className="h-16 w-16 text-cyber-pink mb-4" />
        <h2 className="font-display text-2xl text-white mb-2">USER NOT FOUND</h2>
        <p className="text-gray-400 mb-6 text-center">
          This user doesn't exist or their account has been deactivated.
        </p>
        <Link to="/leaderboard" className="btn-cyber">
          BROWSE USERS
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
            <div className="w-24 h-24 bg-cyber-dark border-2 border-cyber-cyan flex items-center justify-center flex-shrink-0">
              {profileUser.avatar ? (
                <img
                  src={profileUser.avatar}
                  alt={profileUser.username}
                  className="w-full h-full object-cover"
                />
              ) : (
                <UserIcon className="h-12 w-12 text-cyber-cyan" />
              )}
            </div>

            {/* Info */}
            <div className="flex-1 text-center md:text-left">
              <div className="flex flex-col md:flex-row md:items-center gap-2 mb-2">
                <h1 className="font-display text-2xl font-bold text-white">
                  {profileUser.display_name || profileUser.username}
                </h1>
                <div className="flex items-center justify-center md:justify-start gap-2">
                  {profileUser.is_trusted && (
                    <span className="badge-cyber text-cyber-green border-cyber-green flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      TRUSTED
                    </span>
                  )}
                </div>
              </div>

              {profileUser.display_name && profileUser.display_name !== profileUser.username && (
                <p className="text-gray-500 text-sm font-mono mb-2">@{profileUser.username}</p>
              )}

              {profileUser.bio && (
                <p className="text-gray-300 text-sm mb-3">{profileUser.bio}</p>
              )}

              <div className="flex items-center justify-center md:justify-start gap-4 text-xs text-gray-500 flex-wrap">
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  Joined {new Date(profileUser.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </span>
                {profileUser.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {profileUser.location}
                  </span>
                )}
                {profileUser.website && (
                  <a
                    href={profileUser.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-cyber-cyan hover:underline"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Website
                  </a>
                )}
              </div>
            </div>

            {/* Send Message button */}
            {isAuthenticated && !isSelf && (
              <Link
                to={`/messages/new?to=${profileUser.id}`}
                className="btn-cyber flex items-center gap-2 text-sm flex-shrink-0"
              >
                <MessageSquare className="h-4 w-4" />
                SEND MESSAGE
              </Link>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-cyan mb-1">
              {profileUser.reputation_score}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Award className="h-3.5 w-3.5" />
              REPUTATION
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-pink mb-1">
              {profileUser.contribution_count}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Package className="h-3.5 w-3.5" />
              CONTRIBUTIONS
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-green mb-1">
              {stats?.approved_products ?? 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Cpu className="h-3.5 w-3.5" />
              PRODUCTS
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-yellow mb-1">
              {stats?.approved_components ?? 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Package className="h-3.5 w-3.5" />
              COMPONENTS
            </div>
          </div>
        </div>

        {/* Rank */}
        {stats?.reputation_rank && (
          <div className="card-cyber p-3 mb-8 flex items-center justify-center gap-2 text-sm">
            <Trophy className="h-4 w-4 text-cyber-yellow" />
            <span className="text-gray-400 font-mono">
              Ranked <span className="text-cyber-yellow font-bold">#{stats.reputation_rank}</span> by reputation
            </span>
          </div>
        )}

        {/* Contributions */}
        <div className="space-y-8">
          {/* Products */}
          <div>
            <h2 className="font-display text-lg font-bold text-white mb-4">
              RECENT <span className="text-cyber-cyan">PRODUCTS</span>
            </h2>
            {contributions?.products && contributions.products.length > 0 ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {contributions.products.slice(0, 6).map((product) => (
                  <Link
                    key={product.id}
                    to={`/products/${product.id}`}
                    className="card-cyber p-4 hover:border-cyber-cyan/50 transition-all group"
                  >
                    <span className="text-xs font-mono text-cyber-cyan">
                      {product.manufacturer}
                    </span>
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
                <p className="text-gray-500 text-sm font-mono">No products yet</p>
              </div>
            )}
          </div>

          {/* Components */}
          <div>
            <h2 className="font-display text-lg font-bold text-white mb-4">
              RECENT <span className="text-cyber-pink">COMPONENTS</span>
            </h2>
            {contributions?.components && contributions.components.length > 0 ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {contributions.components.slice(0, 6).map((component) => (
                  <Link
                    key={component.id}
                    to={`/components/${component.id}/products`}
                    className="card-cyber p-4 hover:border-cyber-pink/50 transition-all group"
                  >
                    <span className="text-xs font-mono text-cyber-pink">
                      {component.manufacturer}
                    </span>
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
                <p className="text-gray-500 text-sm font-mono">No components yet</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
