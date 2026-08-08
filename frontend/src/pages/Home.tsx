import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation } from '@tanstack/react-query';
import { stats, newsletter, products } from '../api/endpoints';
import {
  Terminal,
  Cpu,
  FileText,
  HardDrive,
  Users,
  Zap,
  Mail,
  ArrowRight,
  ChevronRight,
} from 'lucide-react';
import { parseApiError } from '../utils/formErrors';
import LaunchCountdown from '../components/LaunchCountdown';

export default function Home() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const { data: siteStats } = useQuery({
    queryKey: ['stats'],
    queryFn: stats.get,
  });

  const { data: featuredProducts } = useQuery({
    queryKey: ['featured-products'],
    queryFn: products.featured,
    staleTime: 5 * 60 * 1000,
  });

  const subscribeMutation = useMutation({
    mutationFn: (email: string) => newsletter.subscribe(email, 'landing'),
    onSuccess: () => {
      setSubmitted(true);
      setEmail('');
      setError('');
    },
    onError: (err: any) => {
      setError(parseApiError(err, t('common.error')));
    },
  });

  const handleNotify = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    subscribeMutation.mutate(email);
  };

  return (
    <div className="noise">
      {/* OpenSauce Launch Section */}
      <section className="relative py-6 border-b border-cyber-pink/20 bg-cyber-darker/60 overflow-hidden">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-10">
            {/* Canted OpenSauce stamp with APPROVED overlay */}
            <div className="relative flex-shrink-0">
              <div className="-rotate-6 select-none">
                <div className="border-4 border-double border-cyber-pink/80 px-6 py-3 text-center bg-cyber-black/40 shadow-neon-pink">
                  <div className="font-display text-xl md:text-2xl font-black tracking-wider text-cyber-pink leading-tight">
                    OPEN<br />SAUCE
                  </div>
                  <div className="font-mono text-[11px] tracking-[0.3em] text-cyber-pink/70 mt-1">
                    {t('home.opensauce_dates')}
                  </div>
                </div>
              </div>
              <div className="absolute inset-0 flex items-center justify-center rotate-12 pointer-events-none opacity-50">
                <div className="border-4 border-cyber-green px-4 py-1 bg-cyber-black/30 shadow-neon-green">
                  <span className="font-display text-lg md:text-xl font-black tracking-[0.2em] text-cyber-green">
                    {t('home.opensauce_approved')}
                  </span>
                </div>
              </div>
            </div>

            {/* Countdown + statement */}
            <div className="flex-1 text-center max-w-md">
              <h2 className="font-display text-lg md:text-xl font-bold text-white mb-1">
                {t('home.opensauce_title')}<br />
                <span className="text-cyber-pink">{t('home.opensauce_title_highlight')}</span>
              </h2>
              <p className="text-gray-400 text-sm mb-3">
                {t('home.opensauce_statement')}
              </p>
              <LaunchCountdown />
            </div>

            {/* Official OpenSauce 2026 logo */}
            <div className="flex-shrink-0">
              <img
                src="/images/opensauce-2026-logo.webp"
                alt="OpenSauce 2026"
                className="w-28 md:w-40 drop-shadow-[0_0_20px_rgba(255,42,109,0.35)]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Hero Section */}
      <section className="relative overflow-hidden py-16 md:py-24 scanlines">
        {/* Background effects */}
        <div className="absolute inset-0 bg-gradient-to-b from-cyber-cyan/5 via-transparent to-cyber-pink/5" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-cyber-cyan/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyber-pink/10 rounded-full blur-3xl animate-pulse" />

        <div className="relative mx-auto max-w-7xl px-4 text-center">
          {/* Glitch title */}
          <h1 className="font-display text-5xl md:text-7xl lg:text-8xl font-bold text-white mb-4">
            <span
              className="glitch inline-block"
              data-text="JUNKBIN"
            >
              JUNK<span className="text-cyber-cyan">BIN</span>
            </span>
          </h1>

          {/* Tagline with terminal styling */}
          <div className="max-w-2xl mx-auto mb-8">
            <div className="crt bg-cyber-black/80 border border-cyber-cyan/50 p-4 font-mono text-left">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-cyber-cyan/20">
                <div className="w-3 h-3 rounded-full bg-cyber-pink" />
                <div className="w-3 h-3 rounded-full bg-cyber-yellow" />
                <div className="w-3 h-3 rounded-full bg-cyber-green" />
                <span className="text-cyber-cyan/50 text-xs ml-2">terminal v1.0</span>
              </div>
              <div className="text-cyber-cyan text-sm mb-2">
                <span className="text-cyber-green">$</span> {t('home.tagline_command')}
              </div>
              <div className="text-gray-400 text-sm leading-relaxed">
                <span className="text-cyber-pink">&gt;</span> {t('home.tagline_quote')}
              </div>
              <div className="text-white text-sm mt-2">
                <span className="text-cyber-green">$</span> echo "{t('home.tagline_response')}"
                <span className="blink ml-1 text-cyber-cyan">_</span>
              </div>
            </div>
          </div>

          <p className="max-w-2xl mx-auto text-gray-400 text-lg mb-6">
            {t('home.description')}
          </p>

          <div className="flex items-center justify-center gap-2 text-cyber-pink font-semibold text-xl mb-12">
            <Zap className="h-5 w-5" />
            <span>{t('home.right_to_repair')}</span>
            <Zap className="h-5 w-5" />
          </div>

          {/* Coming Soon CTA */}
          <div className="max-w-lg mx-auto">
            {!submitted ? (
              <form onSubmit={handleNotify} className="flex flex-col gap-3">
                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="flex-1 relative">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={t('home.email_placeholder')}
                      required
                      disabled={subscribeMutation.isPending}
                      className="terminal-input w-full px-4 py-3 text-cyber-cyan placeholder-cyber-cyan/40 disabled:opacity-50"
                    />
                    <Terminal className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-cyber-cyan/30" />
                  </div>
                  <button
                    type="submit"
                    className="btn-cyber whitespace-nowrap disabled:opacity-50"
                    disabled={subscribeMutation.isPending}
                  >
                    <Mail className="h-4 w-4 inline mr-2" />
                    {subscribeMutation.isPending ? t('home.subscribing') : t('home.notify_me')}
                  </button>
                </div>
                {error && (
                  <div className="text-cyber-pink font-mono text-sm">
                    <span className="text-cyber-pink">{t('home.error_prefix')}</span> {error}
                  </div>
                )}
              </form>
            ) : (
              <div className="border border-cyber-green/50 bg-cyber-green/10 p-4 font-mono text-cyber-green text-sm">
                <span className="text-cyber-green">✓</span> {t('home.subscription_confirmed')}
              </div>
            )}

            <div className="flex items-center justify-center gap-3 mt-5 animate-yellow-pulse">
              <span className="text-[#f9f002] text-2xl leading-none">▼</span>
              <p className="font-bold text-[#f9f002] tracking-widest uppercase text-lg">
                {t('home.beta_testers_cta')}
              </p>
              <span className="text-[#f9f002] text-2xl leading-none">▼</span>
            </div>
          </div>
        </div>
      </section>

      {/* Live Stats Section */}
      <section className="py-12 border-y border-cyber-cyan/20 bg-cyber-darker/80">
        <div className="mx-auto max-w-7xl px-4">
          <div className="text-center mb-8">
            <h2 className="font-mono text-sm text-cyber-cyan/70 tracking-widest">
              {t('home.db_status')} <span className="text-cyber-green">{t('home.db_online')}</span>
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
            <Link to="/products" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 neon-border hover:border-cyber-cyan/50 transition-colors group block">
              <Cpu className="h-6 w-6 text-cyber-cyan mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-cyan mb-1">
                {siteStats?.products ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-cyan font-mono text-xs tracking-wider transition-colors">{t('home.stats_products')}</div>
            </Link>

            <Link to="/components" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 hover:border-cyber-pink/50 transition-colors group block">
              <FileText className="h-6 w-6 text-cyber-pink mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-pink mb-1">
                {siteStats?.components ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-pink font-mono text-xs tracking-wider transition-colors">{t('home.stats_components')}</div>
            </Link>

            <Link to="/schematics" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 hover:border-cyber-green/50 transition-colors group block">
              <FileText className="h-6 w-6 text-cyber-green mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-green mb-1">
                {siteStats?.schematics ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-green font-mono text-xs tracking-wider transition-colors">{t('home.stats_schematics')}</div>
            </Link>

            <Link to="/products" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 hover:border-purple-400/50 transition-colors group block">
              <HardDrive className="h-6 w-6 text-purple-400 mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-purple-400 mb-1">
                {siteStats?.firmware ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-purple-400 font-mono text-xs tracking-wider transition-colors">{t('home.stats_firmware')}</div>
            </Link>

            <Link to="/leaderboard" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 hover:border-cyber-yellow/50 transition-colors group block">
              <Users className="h-6 w-6 text-cyber-yellow mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-yellow mb-1">
                {siteStats?.contributors ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-yellow font-mono text-xs tracking-wider transition-colors">{t('home.stats_contributors')}</div>
            </Link>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      {featuredProducts && featuredProducts.length > 0 && (
        <section className="py-12">
          <div className="mx-auto max-w-7xl px-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-xl font-bold text-white">
                {t('home.featured_products')} <span className="text-cyber-cyan">{t('home.featured_products_highlight')}</span>
              </h2>
              <Link
                to="/products"
                className="text-xs text-cyber-cyan hover:text-white transition-colors flex items-center gap-1 font-mono"
              >
                {t('home.view_all')} <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            <div className="flex gap-4 overflow-x-auto scrollbar-hide pb-2">
              {featuredProducts.map((product) => (
                <Link
                  key={product.id}
                  to={`/products/${product.id}`}
                  className="card-cyber p-4 min-w-[220px] max-w-[220px] flex-shrink-0 hover:border-cyber-cyan/50 transition-all group"
                >
                  <div className="aspect-video mb-3 bg-cyber-black flex items-center justify-center border border-cyber-light/20 overflow-hidden">
                    {product.primary_image ? (
                      <img
                        src={product.primary_image.thumbnail || product.primary_image.image}
                        alt={product.model_number}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Cpu className="h-8 w-8 text-gray-600" />
                    )}
                  </div>
                  <div className="text-xs font-mono text-cyber-cyan mb-1 truncate">
                    {product.manufacturer}
                  </div>
                  <div className="text-sm font-semibold text-white group-hover:text-cyber-cyan transition-colors truncate">
                    {product.model_number}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500 font-mono">
                    <span>{product.component_count} {t('home.parts')}</span>
                    <span>{product.schematic_count} {t('home.docs')}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* What We're Building Section */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4">
          <div className="text-center mb-12">
            <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-3">
              {t('home.what_were_building')} <span className="text-cyber-cyan chromatic-aberration">{t('home.building')}</span>
            </h2>
            <p className="text-gray-500 font-mono text-sm">
              {t('home.building_subtitle')}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="card-cyber p-6 group hover:border-cyber-cyan/50 transition-all relative overflow-hidden">
              <div className="absolute top-0 right-0 w-20 h-20 bg-cyber-cyan/5 blur-2xl group-hover:bg-cyber-cyan/10 transition-all" />
              <div className="relative">
                <div className="w-10 h-10 flex items-center justify-center bg-cyber-cyan/10 border border-cyber-cyan/30 mb-4">
                  <Cpu className="h-5 w-5 text-cyber-cyan" />
                </div>
                <h3 className="font-display text-lg font-semibold text-white mb-2">
                  {t('home.feature1_title')}
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  {t('home.feature1_desc')}
                </p>
                <div className="text-cyber-cyan/50 font-mono text-xs">
                  → parts.lookup()
                </div>
              </div>
            </div>

            {/* Feature 2 */}
            <div className="card-cyber p-6 group hover:border-cyber-pink/50 transition-all relative overflow-hidden">
              <div className="absolute top-0 right-0 w-20 h-20 bg-cyber-pink/5 blur-2xl group-hover:bg-cyber-pink/10 transition-all" />
              <div className="relative">
                <div className="w-10 h-10 flex items-center justify-center bg-cyber-pink/10 border border-cyber-pink/30 mb-4">
                  <FileText className="h-5 w-5 text-cyber-pink" />
                </div>
                <h3 className="font-display text-lg font-semibold text-white mb-2">
                  {t('home.feature2_title')}
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  {t('home.feature2_desc')}
                </p>
                <div className="text-cyber-pink/50 font-mono text-xs">
                  → docs.fetch()
                </div>
              </div>
            </div>

            {/* Feature 3 */}
            <div className="card-cyber p-6 group hover:border-cyber-green/50 transition-all relative overflow-hidden">
              <div className="absolute top-0 right-0 w-20 h-20 bg-cyber-green/5 blur-2xl group-hover:bg-cyber-green/10 transition-all" />
              <div className="relative">
                <div className="w-10 h-10 flex items-center justify-center bg-cyber-green/10 border border-cyber-green/30 mb-4">
                  <Users className="h-5 w-5 text-cyber-green" />
                </div>
                <h3 className="font-display text-lg font-semibold text-white mb-2">
                  {t('home.feature3_title')}
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  {t('home.feature3_desc')}
                </p>
                <div className="text-cyber-green/50 font-mono text-xs">
                  → community.join()
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Early Access Section */}
      <section className="py-16 bg-cyber-darker/50">
        <div className="mx-auto max-w-3xl px-4">
          <div className="card-cyber p-8 md:p-10 text-center relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0 opacity-5">
              <div className="absolute top-4 left-4 font-mono text-[8px] text-cyber-cyan leading-tight whitespace-pre">
{"╔══════════════════════════════════╗\n║  " + t('home.no_user_serviceable') + " ║\n║  " + t('home.no_user_serviceable') + " ║\n║  " + t('home.no_user_serviceable') + " ║\n╚══════════════════════════════════╝"}
              </div>
            </div>

            <div className="relative">
              <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-4">
                {t('home.early_access_title')} <span className="text-cyber-yellow">{t('home.early_access_highlight')}</span>{t('home.early_access_question')}
              </h2>
              <p className="text-gray-400 mb-6 max-w-md mx-auto">
                {t('home.early_access_desc')}
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link to="/register" className="btn-cyber">
                  {t('home.create_account')}
                  <ArrowRight className="h-4 w-4 inline ml-2" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Mascot Poster */}
      <section className="relative py-16 md:py-20 px-4">
        <div className="mx-auto max-w-3xl flex justify-center">
          <div className="poster-frame w-full">
            <div className="poster-tape poster-tape-tl" />
            <div className="poster-tape poster-tape-tr" />
            <img
              src="/images/junkbin-mascot-banner.webp"
              alt="Junkbin.io mascot — a punk raccoon with a red mohawk holding a glowing wrench, captioned Right to Repair Database"
              className="block w-full h-auto"
            />
          </div>
        </div>
        <p className="text-center mt-5 text-gray-500 font-mono text-xs tracking-wide">
          {t('home.mascot_caption')}
        </p>
      </section>

      {/* Right to Repair Message */}
      <section className="py-16">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <div className="inline-block mb-6">
            <Zap className="h-10 w-10 text-cyber-yellow mx-auto" />
          </div>
          <h2 className="font-display text-xl md:text-2xl font-bold text-white mb-4">
            {t('home.r2r_quote')}
          </h2>
          <p className="text-gray-400 mb-6">
            {t('home.r2r_desc')}
          </p>
          <a
            href="https://repair.org"
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyber-yellow font-mono text-sm hover:underline"
          >
            {t('home.learn_r2r')}
          </a>
        </div>
      </section>
    </div>
  );
}
