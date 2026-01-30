import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
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
} from 'lucide-react';

export default function Profile() {
  const { user, isAuthenticated } = useAuth();

  // Fetch user's contributions
  const { data: contributions, isLoading: contributionsLoading } = useQuery({
    queryKey: ['user-contributions', user?.id],
    queryFn: async () => {
      const response = await api.get(`/users/${user?.id}/contributions/`);
      return response.data;
    },
    enabled: !!user?.id,
  });

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <AlertCircle className="h-16 w-16 text-cyber-pink mb-4" />
        <h2 className="font-display text-2xl text-white mb-2">NOT LOGGED IN</h2>
        <p className="text-gray-400 mb-6 text-center">
          Please log in to view your profile.
        </p>
        <Link to="/login" className="btn-cyber">
          LOGIN
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
                      TRUSTED
                    </span>
                  )}
                  {user.is_moderator && (
                    <span className="badge-cyber text-cyber-yellow border-cyber-yellow flex items-center gap-1">
                      <Star className="h-3 w-3" />
                      MODERATOR
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
              REPUTATION
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-pink mb-1">
              {user.contribution_count || 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Package className="h-3.5 w-3.5" />
              CONTRIBUTIONS
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-green mb-1">
              {contributions?.products?.length || 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Cpu className="h-3.5 w-3.5" />
              PRODUCTS
            </div>
          </div>

          <div className="card-cyber p-4 text-center">
            <div className="text-3xl font-display font-bold text-cyber-yellow mb-1">
              {contributions?.components?.length || 0}
            </div>
            <div className="text-xs font-mono text-gray-500 flex items-center justify-center gap-1">
              <Package className="h-3.5 w-3.5" />
              COMPONENTS
            </div>
          </div>
        </div>

        {/* Recent Contributions */}
        <div className="space-y-6">
          {/* Products */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg font-bold text-white">
                YOUR <span className="text-cyber-cyan">PRODUCTS</span>
              </h2>
              <Link
                to="/my-submissions?type=products"
                className="text-xs text-cyber-cyan hover:text-white transition-colors flex items-center gap-1"
              >
                VIEW ALL <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {contributionsLoading ? (
              <div className="card-cyber p-8 text-center">
                <div className="text-cyber-cyan font-mono animate-pulse">
                  LOADING...
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
                          PENDING
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
                  You haven't documented any products yet.
                </p>
                <Link to="/submit" className="btn-cyber text-sm">
                  ADD YOUR FIRST PRODUCT
                </Link>
              </div>
            )}
          </div>

          {/* Components */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg font-bold text-white">
                YOUR <span className="text-cyber-pink">COMPONENTS</span>
              </h2>
              <Link
                to="/my-submissions?type=components"
                className="text-xs text-cyber-pink hover:text-white transition-colors flex items-center gap-1"
              >
                VIEW ALL <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {contributionsLoading ? (
              <div className="card-cyber p-8 text-center">
                <div className="text-cyber-pink font-mono animate-pulse">
                  LOADING...
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
                  You haven't added any components yet.
                </p>
                <Link to="/submit" className="btn-cyber text-sm">
                  ADD YOUR FIRST COMPONENT
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Badges/Achievements placeholder */}
        <div className="mt-8 p-4 border border-cyber-light/20 bg-cyber-dark/50">
          <h3 className="font-mono text-sm text-gray-500 mb-2">ACHIEVEMENTS</h3>
          <div className="flex flex-wrap gap-2">
            {user.contribution_count >= 1 && (
              <span className="px-3 py-1 text-xs font-mono bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30">
                FIRST CONTRIBUTION
              </span>
            )}
            {user.contribution_count >= 10 && (
              <span className="px-3 py-1 text-xs font-mono bg-cyber-pink/10 text-cyber-pink border border-cyber-pink/30">
                10 CONTRIBUTIONS
              </span>
            )}
            {user.is_trusted && (
              <span className="px-3 py-1 text-xs font-mono bg-cyber-green/10 text-cyber-green border border-cyber-green/30">
                TRUSTED CONTRIBUTOR
              </span>
            )}
            {user.contribution_count < 1 && (
              <span className="text-xs text-gray-600">
                Start contributing to earn achievements!
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
