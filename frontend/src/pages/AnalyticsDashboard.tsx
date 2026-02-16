import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, Search, Cpu, Users, TrendingUp, Activity, Database, Loader2 } from 'lucide-react';
import { analytics } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import type { AnalyticsDashboardData, DailyActiveUsers } from '../types';

function Sparkline({ data, width = 200, height = 40 }: { data: number[]; width?: number; height?: number }) {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const stepX = width / Math.max(data.length - 1, 1);

  const points = data
    .map((v, i) => `${i * stepX},${height - ((v - min) / range) * (height - 4) - 2}`)
    .join(' ');

  return (
    <svg width={width} height={height} className="inline-block">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        points={points}
      />
    </svg>
  );
}

const ACTIVITY_LABELS: Record<string, string> = {
  login: 'Logins',
  product_view: 'Product Views',
  component_view: 'Component Views',
  search: 'Searches',
  submission: 'Submissions',
  report: 'Reports',
};

export default function AnalyticsDashboard() {
  const { user, isAuthenticated } = useAuth();
  const [days, setDays] = useState(30);

  const isStaff = isAuthenticated && (user?.is_staff || user?.is_moderator);

  const { data, isLoading, error } = useQuery<AnalyticsDashboardData>({
    queryKey: ['analytics', days],
    queryFn: () => analytics.dashboard(days),
    enabled: !!isStaff,
    staleTime: 60000,
  });

  if (!isAuthenticated || !isStaff) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-cyber-cyan" />
          <div>
            <h1 className="font-display text-2xl font-bold text-white tracking-wider">
              ANALYTICS
            </h1>
            <p className="text-sm text-gray-500 font-mono">Site metrics & engagement</p>
          </div>
        </div>

        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 font-mono text-xs border transition-colors ${
                days === d
                  ? 'border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10'
                  : 'border-cyber-light/30 text-gray-500 hover:text-white hover:border-cyber-light/60'
              }`}
            >
              {d}D
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-cyber-cyan" />
        </div>
      )}

      {error && (
        <div className="card-cyber p-6 text-center">
          <p className="text-cyber-pink font-mono">Failed to load analytics data</p>
        </div>
      )}

      {data && (
        <>
          {/* Content Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              icon={<Database className="h-5 w-5" />}
              label="Products"
              value={data.content_stats.products}
              color="text-cyber-cyan"
            />
            <StatCard
              icon={<Cpu className="h-5 w-5" />}
              label="Components"
              value={data.content_stats.components}
              color="text-cyber-pink"
            />
            <StatCard
              icon={<Activity className="h-5 w-5" />}
              label="Schematics"
              value={data.content_stats.schematics}
              color="text-cyber-green"
            />
            <StatCard
              icon={<TrendingUp className="h-5 w-5" />}
              label="Recipes"
              value={data.content_stats.recipes}
              color="text-cyber-yellow"
            />
          </div>

          {/* DAU + Search Analytics Row */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            {/* Daily Active Users */}
            <div className="card-cyber p-6">
              <div className="flex items-center gap-2 mb-4">
                <Users className="h-5 w-5 text-cyber-cyan" />
                <h2 className="font-display text-lg text-white">Daily Active Users</h2>
              </div>
              <div className="text-cyber-cyan">
                <Sparkline data={data.dau.map((d: DailyActiveUsers) => d.count)} width={500} height={80} />
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-500 font-mono">
                <span>{data.dau.length > 0 ? data.dau[0].date : ''}</span>
                <span>{data.dau.length > 0 ? data.dau[data.dau.length - 1].date : ''}</span>
              </div>
              {data.dau.length > 0 && (
                <div className="mt-3 text-sm text-gray-400">
                  Latest: <span className="text-white font-mono">{data.dau[data.dau.length - 1].count}</span> users
                </div>
              )}
            </div>

            {/* Search Analytics */}
            <div className="card-cyber p-6">
              <div className="flex items-center gap-2 mb-4">
                <Search className="h-5 w-5 text-cyber-pink" />
                <h2 className="font-display text-lg text-white">Search Analytics</h2>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="text-2xl font-mono font-bold text-white">
                    {data.search_analytics.total.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500">Total Searches</div>
                </div>
                <div>
                  <div className="text-2xl font-mono font-bold text-cyber-yellow">
                    {data.search_analytics.zero_result_pct}%
                  </div>
                  <div className="text-xs text-gray-500">Zero Results</div>
                </div>
              </div>
            </div>
          </div>

          {/* Top Search Queries + Trending Components Row */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            {/* Top Queries */}
            <div className="card-cyber p-6">
              <h2 className="font-display text-lg text-white mb-4">Top Search Queries</h2>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {data.search_analytics.top_queries.length === 0 ? (
                  <p className="text-gray-500 text-sm">No search data yet</p>
                ) : (
                  data.search_analytics.top_queries.map((q, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-1.5 px-2 border-b border-cyber-light/10"
                    >
                      <span className="font-mono text-sm text-gray-300 truncate flex-1">
                        {q.query}
                      </span>
                      <span className="font-mono text-xs text-cyber-cyan ml-2">
                        {q.count}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Trending Components */}
            <div className="card-cyber p-6">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="h-5 w-5 text-cyber-green" />
                <h2 className="font-display text-lg text-white">Trending Components</h2>
              </div>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {data.trending_components.length === 0 ? (
                  <p className="text-gray-500 text-sm">No view data yet</p>
                ) : (
                  data.trending_components.map((c, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-1.5 px-2 border-b border-cyber-light/10"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-mono text-sm text-white truncate">
                          {c.component__part_number}
                        </div>
                        <div className="text-xs text-gray-500 truncate">
                          {c.component__manufacturer}
                        </div>
                      </div>
                      <span className="font-mono text-xs text-cyber-green ml-2">
                        {c.total_views} views
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Activity Breakdown */}
          <div className="card-cyber p-6">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="h-5 w-5 text-cyber-yellow" />
              <h2 className="font-display text-lg text-white">Activity Breakdown</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {data.activity_breakdown.map((a, i) => (
                <div key={i} className="text-center">
                  <div className="text-xl font-mono font-bold text-white">
                    {a.count.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {ACTIVITY_LABELS[a.activity_type] || a.activity_type}
                  </div>
                </div>
              ))}
              {data.activity_breakdown.length === 0 && (
                <p className="text-gray-500 text-sm col-span-full">No activity data yet</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="card-cyber p-4">
      <div className={`flex items-center gap-2 mb-2 ${color}`}>
        {icon}
        <span className="text-xs text-gray-500 uppercase font-mono">{label}</span>
      </div>
      <div className="text-2xl font-mono font-bold text-white">
        {value.toLocaleString()}
      </div>
    </div>
  );
}
