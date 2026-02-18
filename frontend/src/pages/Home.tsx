import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { stats, newsletter, products } from '../api/endpoints';
import {
  Terminal,
  Cpu,
  FileText,
  Users,
  Zap,
  Mail,
  Github,
  ArrowRight,
  AlertTriangle,
  ChevronRight,
} from 'lucide-react';
import { parseApiError } from '../utils/formErrors';

export default function Home() {
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
      setError(parseApiError(err, 'Failed to subscribe. Please try again.'));
    },
  });

  const handleNotify = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    subscribeMutation.mutate(email);
  };

  return (
    <div className="noise">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-16 md:py-24 scanlines">
        {/* Background effects */}
        <div className="absolute inset-0 bg-gradient-to-b from-cyber-cyan/5 via-transparent to-cyber-pink/5" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-cyber-cyan/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyber-pink/10 rounded-full blur-3xl animate-pulse" />

        <div className="relative mx-auto max-w-5xl px-4 text-center">
          {/* Warning badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 mb-8 border border-cyber-yellow/50 bg-cyber-yellow/5">
            <AlertTriangle className="h-4 w-4 text-cyber-yellow" />
            <span className="text-cyber-yellow font-mono text-sm tracking-wider">
              SITE UNDER CONSTRUCTION
            </span>
          </div>

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
                <span className="text-cyber-green">$</span> cat /etc/warning.txt
              </div>
              <div className="text-gray-400 text-sm leading-relaxed">
                <span className="text-cyber-pink">&gt;</span> "NO USER SERVICEABLE PARTS INSIDE"
              </div>
              <div className="text-white text-sm mt-2">
                <span className="text-cyber-green">$</span> echo "We took that personally."
                <span className="blink ml-1 text-cyber-cyan">_</span>
              </div>
            </div>
          </div>

          <p className="max-w-2xl mx-auto text-gray-400 text-lg mb-6">
            A community-driven database for electronic components, schematics, and repair documentation.
          </p>

          <div className="flex items-center justify-center gap-2 text-cyber-pink font-semibold text-xl mb-12">
            <Zap className="h-5 w-5" />
            <span>RIGHT TO REPAIR STARTS HERE</span>
            <Zap className="h-5 w-5" />
          </div>

          {/* Coming Soon CTA */}
          <div className="max-w-lg mx-auto">
            <h2 className="font-display text-xl text-white mb-4">
              LAUNCHING <span className="text-cyber-green">SOON</span>
            </h2>

            {!submitted ? (
              <form onSubmit={handleNotify} className="flex flex-col gap-3">
                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="flex-1 relative">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="enter_email@domain.com"
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
                    {subscribeMutation.isPending ? 'SUBSCRIBING...' : 'NOTIFY ME'}
                  </button>
                </div>
                {error && (
                  <div className="text-cyber-pink font-mono text-sm">
                    <span className="text-cyber-pink">ERROR:</span> {error}
                  </div>
                )}
              </form>
            ) : (
              <div className="border border-cyber-green/50 bg-cyber-green/10 p-4 font-mono text-cyber-green text-sm">
                <span className="text-cyber-green">✓</span> SUBSCRIPTION_CONFIRMED — You'll be notified at launch.
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Live Stats Section */}
      <section className="py-12 border-y border-cyber-cyan/20 bg-cyber-darker/80">
        <div className="mx-auto max-w-5xl px-4">
          <div className="text-center mb-8">
            <h2 className="font-mono text-sm text-cyber-cyan/70 tracking-widest">
              // DATABASE STATUS: <span className="text-cyber-green">ONLINE</span>
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <Link to="/products" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 neon-border hover:border-cyber-cyan/50 transition-colors group block">
              <Cpu className="h-6 w-6 text-cyber-cyan mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-cyan mb-1">
                {siteStats?.products ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-cyan font-mono text-xs tracking-wider transition-colors">PRODUCTS</div>
            </Link>

            <Link to="/components" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 hover:border-cyber-pink/50 transition-colors group block">
              <FileText className="h-6 w-6 text-cyber-pink mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-pink mb-1">
                {siteStats?.components ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-pink font-mono text-xs tracking-wider transition-colors">COMPONENTS</div>
            </Link>

            <Link to="/schematics" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 hover:border-cyber-green/50 transition-colors group block">
              <FileText className="h-6 w-6 text-cyber-green mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-green mb-1">
                {siteStats?.schematics ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-green font-mono text-xs tracking-wider transition-colors">SCHEMATICS</div>
            </Link>

            <Link to="/leaderboard" className="text-center p-4 border border-cyber-light/20 bg-cyber-dark/50 hover:border-cyber-yellow/50 transition-colors group block">
              <Users className="h-6 w-6 text-cyber-yellow mx-auto mb-3" />
              <div className="text-3xl md:text-4xl font-display font-bold text-cyber-yellow mb-1">
                {siteStats?.contributors ?? '—'}
              </div>
              <div className="text-gray-500 group-hover:text-cyber-yellow font-mono text-xs tracking-wider transition-colors">CONTRIBUTORS</div>
            </Link>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      {featuredProducts && featuredProducts.length > 0 && (
        <section className="py-12">
          <div className="mx-auto max-w-5xl px-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-xl font-bold text-white">
                FEATURED <span className="text-cyber-cyan">PRODUCTS</span>
              </h2>
              <Link
                to="/products"
                className="text-xs text-cyber-cyan hover:text-white transition-colors flex items-center gap-1 font-mono"
              >
                VIEW ALL <ChevronRight className="h-3.5 w-3.5" />
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
                    <span>{product.component_count} parts</span>
                    <span>{product.schematic_count} docs</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* What We're Building Section */}
      <section className="py-16">
        <div className="mx-auto max-w-5xl px-4">
          <div className="text-center mb-12">
            <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-3">
              WHAT WE'RE <span className="text-cyber-cyan chromatic-aberration">BUILDING</span>
            </h2>
            <p className="text-gray-500 font-mono text-sm">
              // A repair knowledge base for everyone
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
                  Component Database
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  Cross-reference ICs, transistors, and parts across thousands of consumer electronics.
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
                  Schematics & BOMs
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  Service manuals, block diagrams, and bills of materials from teardowns.
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
                  Community Driven
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  Built by repair enthusiasts, for repair enthusiasts. Open data for everyone.
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
{`╔══════════════════════════════════╗
║  NO USER SERVICEABLE PARTS INSIDE ║
║  NO USER SERVICEABLE PARTS INSIDE ║
║  NO USER SERVICEABLE PARTS INSIDE ║
╚══════════════════════════════════╝`}
              </div>
            </div>

            <div className="relative">
              <h2 className="font-display text-2xl md:text-3xl font-bold text-white mb-4">
                WANT <span className="text-cyber-yellow">EARLY ACCESS</span>?
              </h2>
              <p className="text-gray-400 mb-6 max-w-md mx-auto">
                We're looking for beta testers and early contributors to help build the database.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link to="/register" className="btn-cyber">
                  CREATE ACCOUNT
                  <ArrowRight className="h-4 w-4 inline ml-2" />
                </Link>
                <a
                  href="https://github.com/junkbin"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-cyber btn-cyber-pink"
                >
                  <Github className="h-4 w-4 inline mr-2" />
                  GITHUB
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Right to Repair Message */}
      <section className="py-16">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <div className="inline-block mb-6">
            <Zap className="h-10 w-10 text-cyber-yellow mx-auto" />
          </div>
          <h2 className="font-display text-xl md:text-2xl font-bold text-white mb-4">
            "NO USER SERVICEABLE PARTS INSIDE"
          </h2>
          <p className="text-gray-400 mb-6">
            Manufacturers don't want you to fix your devices. We're building a database to help you fix it anyway.
            Every documented component, every shared schematic, every teardown photo helps independent
            repair shops, hobbyists, and consumers fight for their right to repair.
          </p>
          <a
            href="https://repair.org"
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyber-yellow font-mono text-sm hover:underline"
          >
            LEARN MORE ABOUT RIGHT TO REPAIR →
          </a>
        </div>
      </section>
    </div>
  );
}
